from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
from app import db, redis_client
from app.models.models import (
    Notebook,
    Event,
    CellExecution,
    CellClickEvent,
    NotebookClickEvent,
    CellAlteration,
    UserGroupAssociation,
    UserGroups,
    PendingUpdateInteraction,
    PendingUpdateAction,
)
from app.utils.utils import get_fetch_real_time, get_time_boundaries
from sqlalchemy import func, and_, select, or_
from sqlalchemy.orm import with_polymorphic
from flask_jwt_extended import jwt_required, current_user
import csv
from io import StringIO
import datetime

dashboard_bp = Blueprint("dashboard", __name__)

### Protecting the blueprint with authentication ###


# to require authentication on all the routes of this blueprint
# notebook-specific: resolve requests with no_user_permission if users are not allowed to view this notebook data
@dashboard_bp.before_request
@jwt_required()
def auth_check():
    # let preflight requests through
    if request.method == "OPTIONS":
        return jsonify("OK"), 200

    # catch the notebook_id provided in all of this blueprint's routes
    notebook_id = request.view_args.get("notebook_id")

    # abort the request if the provided notebook_id is not among the loggedin user authorized notebooks
    if all(
        entry.notebook_id != notebook_id for entry in current_user.authorized_notebooks
    ):
        return jsonify({"status": "no_user_permission"}), 403


### Common utils for the queries


def getConnectedStudentUserIds(notebook_id):
    connected_student_ids = redis_client.smembers(
        f"connected_students:{notebook_id}"
    )  # Stored in the cache as bytes
    return [user_id.decode("utf-8") for user_id in connected_student_ids]


def getGroupsUserIdsSubquery(notebook_id, groups):
    group_pks = [f"{group_name}-{notebook_id}" for group_name in groups]

    return (
        db.session.query(UserGroupAssociation.c.user_id)
        .filter(UserGroupAssociation.c.group_pk.in_(group_pks))
        .subquery()
    )


### Routes ###


@dashboard_bp.route("/<notebook_id>/check", methods=["GET"])
def checkNotebook(notebook_id):
    notebook = Notebook.query.filter_by(notebook_id=notebook_id).first()
    if not notebook:
        # notebook not found
        return jsonify({"status": "not_found"}), 404

    return jsonify({"status": "success"}), 200


### Notebook dashboard ###


@dashboard_bp.route("/<notebook_id>/user_code_execution", methods=["GET"])
def listNotebookCellExecution(notebook_id):

    t_start, t_end = get_time_boundaries(request.args)
    # if t_end is defined, real time is ignored and set to False since what happens in real-time is not included anymore
    fetch_real_time = get_fetch_real_time(request.args, t_end)
    if fetch_real_time:
        connected_students = getConnectedStudentUserIds(notebook_id)
    else:
        connected_students = None
    selected_groups = request.args.get("selectedGroups", None)
    if selected_groups:
        selected_groups = json.loads(selected_groups)

    # get cell click information
    cell_click_subq = db.session.query(
        CellClickEvent.cell_id,
        func.count(CellClickEvent.user_id).label("cell_click_count"),
    ).filter(
        CellClickEvent.notebook_id == notebook_id,
        and_(
            CellClickEvent.time > t_start if t_start is not None else True,
            CellClickEvent.time <= t_end if t_end is not None else True,
        ),
    )

    if fetch_real_time:
        cell_click_subq = cell_click_subq.filter(
            CellClickEvent.user_id.in_(connected_students)
        )

    if selected_groups:
        cell_click_subq = cell_click_subq.filter(
            CellClickEvent.user_id.in_(
                select(getGroupsUserIdsSubquery(notebook_id, selected_groups))
            )
        )

    cell_click_subq = cell_click_subq.group_by(CellClickEvent.cell_id).subquery()

    # get code execution information
    code_exec_subq = db.session.query(
        CellExecution.cell_id,
        func.count(CellExecution.user_id).label("code_exec_count"),
        func.count(CellExecution.user_id)
        .filter(CellExecution.status == "ok")
        .label("code_exec_ok_count"),
    ).filter(
        CellExecution.cell_type == "CodeExecution",
        CellExecution.notebook_id == notebook_id,
        and_(
            CellExecution.t_finish > t_start if t_start is not None else True,
            CellExecution.t_finish <= t_end if t_end is not None else True,
        ),
    )

    if fetch_real_time:
        code_exec_subq = code_exec_subq.filter(
            CellClickEvent.user_id.in_(connected_students)
        )

    if selected_groups:
        code_exec_subq = code_exec_subq.filter(
            CellClickEvent.user_id.in_(
                select(getGroupsUserIdsSubquery(notebook_id, selected_groups))
            )
        )

    code_exec_subq = code_exec_subq.group_by(CellExecution.cell_id).subquery()

    # get data from subqueries
    data = (
        db.session.query(
            cell_click_subq.c.cell_id,
            (cell_click_subq.c.cell_click_count).label("cell_click_pct"),
            (code_exec_subq.c.code_exec_count).label("code_exec_pct"),
            (code_exec_subq.c.code_exec_ok_count).label("code_exec_ok_pct"),
        )
        .join(code_exec_subq, cell_click_subq.c.cell_id == code_exec_subq.c.cell_id)
        .all()
    )

    return jsonify(
        [
            {
                "cell": cell,
                "cell_click_pct": cell_click_pct,
                "code_exec_pct": code_exec_pct,
                "code_exec_ok_pct": code_exec_ok_pct,
            }
            for cell, cell_click_pct, code_exec_pct, code_exec_ok_pct in data
        ]
    )


@dashboard_bp.route("/<notebook_id>/user_cell_time", methods=["GET"])
def listNotebookCellAccessTime(notebook_id):

    t_start, t_end = get_time_boundaries(request.args)
    # if t_end is defined, real time is ignored and set to False since what happens in real-time is not included anymore
    fetch_real_time = get_fetch_real_time(request.args, t_end)
    selected_groups = request.args.get("selectedGroups", None)
    if selected_groups:
        selected_groups = json.loads(selected_groups)

    cell_click_events = db.session.query(
        CellClickEvent.cell_id,
        func.array_agg(CellClickEvent.click_duration).label("durations"),
    ).filter(
        CellClickEvent.notebook_id == notebook_id,
        and_(
            CellClickEvent.time > t_start if t_start is not None else True,
            CellClickEvent.time <= t_end if t_end is not None else True,
        ),
        CellClickEvent.click_type == "OFF",
        CellClickEvent.click_duration.isnot(None),
    )  # use isnot to check for non-null values

    if fetch_real_time:
        cell_click_events = cell_click_events.filter(
            CellClickEvent.user_id.in_(getConnectedStudentUserIds(notebook_id))
        )

    if selected_groups:
        cell_click_events = cell_click_events.filter(
            CellClickEvent.user_id.in_(
                select(getGroupsUserIdsSubquery(notebook_id, selected_groups))
            )
        )

    cell_click_events = cell_click_events.group_by(CellClickEvent.cell_id).all()

    return jsonify(
        [
            {"cell": cell, "durations": durations}
            for cell, durations in cell_click_events
        ]
    )


@dashboard_bp.route("/<notebook_id>/user_cell_duration_time", methods=["GET"])
def listNotebookCellDurationTime(notebook_id):

    t_start, t_end = get_time_boundaries(request.args)
    # if t_end is defined, real time is ignored and set to False since what happens in real-time is not included anymore
    fetch_real_time = get_fetch_real_time(request.args, t_end)
    selected_groups = request.args.get("selectedGroups", None)
    if selected_groups:
        selected_groups = json.loads(selected_groups)

    # subquery to average cell focus duration per user
    per_user_avg_subquery = (
        db.session.query(
            CellClickEvent.cell_id,
            CellClickEvent.user_id,
            func.avg(CellClickEvent.click_duration).label("user_avg_duration"),
        )
        .filter(
            CellClickEvent.notebook_id == notebook_id,
            and_(
                CellClickEvent.time > t_start if t_start is not None else True,
                CellClickEvent.time <= t_end if t_end is not None else True,
            ),
            CellClickEvent.click_type == "OFF",
            CellClickEvent.click_duration.isnot(None),
            CellClickEvent.click_duration
            <= 5000,  # durations longer than this can be considered outliers
        )
        .group_by(CellClickEvent.cell_id, CellClickEvent.user_id)
        .subquery()
    )

    # main query to average the user averages per cell
    cell_click_events_query = db.session.query(
        per_user_avg_subquery.c.cell_id.label("cell"),
        func.avg(per_user_avg_subquery.c.user_avg_duration).label("average_duration"),
        func.count(per_user_avg_subquery.c.user_id).label("user_count"),
    ).group_by(per_user_avg_subquery.c.cell_id)

    # query to compute the total count of distinct users
    filtered_user_ids_query = db.session.query(
        func.distinct(per_user_avg_subquery.c.user_id)
    )

    if fetch_real_time:
        connected_user_ids = getConnectedStudentUserIds(notebook_id)
        cell_click_events_query = cell_click_events_query.filter(
            per_user_avg_subquery.c.user_id.in_(connected_user_ids)
        )
        filtered_user_ids_query = filtered_user_ids_query.filter(
            per_user_avg_subquery.c.user_id.in_(connected_user_ids)
        )

    if selected_groups:
        group_user_ids_subquery = select(
            getGroupsUserIdsSubquery(notebook_id, selected_groups)
        )
        cell_click_events_query = cell_click_events_query.filter(
            per_user_avg_subquery.c.user_id.in_(group_user_ids_subquery)
        )
        filtered_user_ids_query = filtered_user_ids_query.filter(
            per_user_avg_subquery.c.user_id.in_(group_user_ids_subquery)
        )

    cell_click_events = cell_click_events_query.all()

    # calculate total user count
    total_user_count = filtered_user_ids_query.count()

    return jsonify(
        {
            "durations": [
                {
                    "average_duration": avg_duration,
                    "cell": cell,
                    "user_count": user_count,
                }
                for cell, avg_duration, user_count in cell_click_events
            ],
            "total_user_count": total_user_count,
        }
    )


### Cell dashboard ###


@dashboard_bp.route("/<notebook_id>/cell/<cell_id>", methods=["GET"])
def listAttemptsPerCell(notebook_id, cell_id):
    t_start, t_end = get_time_boundaries(request.args)
    # if t_end is defined, real time is ignored and set to False since what happens in real-time is not included anymore
    fetch_real_time = get_fetch_real_time(request.args, t_end)
    selected_groups = request.args.get("selectedGroups", None)
    if selected_groups:
        selected_groups = json.loads(selected_groups)

    sort_by = request.args.get("sortBy", "timeDesc")
    match sort_by:
        case "inputAsc":
            sort_condition = func.length(CellExecution.cell_input).asc()
        case "inputDesc":
            sort_condition = func.length(CellExecution.cell_input).desc()
        case "outputAsc":
            sort_condition = CellExecution.cell_output_length.asc()
        case "outputDesc":
            sort_condition = CellExecution.cell_output_length.desc()
        case "timeAsc":
            sort_condition = CellExecution.id.asc()
        case _:  # default, including timeDesc
            sort_condition = CellExecution.id.desc()

    limit = request.args.get("limit", 20, type=int)
    offset = request.args.get("offset", 0, type=int)

    # only t_start exists for markdown executions so filter on that column
    subq = db.session.query(
        CellExecution.user_id, func.max(CellExecution.id).label("last_id")
    ).filter(
        CellExecution.notebook_id == notebook_id,
        CellExecution.cell_id == cell_id,
        and_(
            CellExecution.t_start > t_start if t_start is not None else True,
            CellExecution.t_start <= t_end if t_end is not None else True,
        ),
    )

    if fetch_real_time:
        subq = subq.filter(
            CellExecution.user_id.in_(getConnectedStudentUserIds(notebook_id))
        )

    if selected_groups:
        subq = subq.filter(
            CellExecution.user_id.in_(
                select(getGroupsUserIdsSubquery(notebook_id, selected_groups))
            )
        )

    subq = subq.group_by(CellExecution.user_id).subquery()

    result = (
        db.session.query(
            CellExecution.id.label("exec_id"),
            CellExecution.user_id,
            CellExecution.cell_type,
            CellExecution.cell_input,
            CellExecution.t_start,
            CellExecution.t_finish,
            CellExecution.language_mimetype,
            CellExecution.status,
            CellExecution.cell_output_model,
            CellExecution.cell_output_length,
        )
        .join(
            subq,
            and_(
                CellExecution.user_id == subq.c.user_id,
                CellExecution.id == subq.c.last_id,
            ),
        )
        .order_by(sort_condition)
        .limit(limit)
        .offset(offset)
    )

    # check if markdown or code execution to include the extra entries related to a code execution
    result_list = [
        (
            {
                "exec_id": exec_id,
                "user_id": user_id,
                "cell_type": cell_type,
                "cell_input": cell_input,
                "t_finish": t_finish.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "language_mimetype": language_mimetype,
                "status": status,
                "cell_output_model": cell_output_model,
                "cell_output_length": cell_output_length,
            }
            if cell_type == "CodeExecution"
            else {
                "exec_id": exec_id,
                "user_id": user_id,
                "cell_type": cell_type,
                "cell_input": cell_input,
                "t_finish": t_start.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
        )
        for exec_id, user_id, cell_type, cell_input, t_start, t_finish, language_mimetype, status, cell_output_model, cell_output_length in result
    ]

    return jsonify(result_list)


### ToC dashboard ###


@dashboard_bp.route("/<notebook_id>/toc", methods=["GET"])
def getNotebookToc(notebook_id):

    t_start, t_end = get_time_boundaries(request.args)
    # if t_end is defined, real time is ignored and set to False since what happens in real-time is not included anymore
    fetch_real_time = get_fetch_real_time(request.args, t_end)
    selected_groups = request.args.get("selectedGroups", None)
    if selected_groups:
        selected_groups = json.loads(selected_groups)

    # retrieve the ids of the last event for each user_id
    subquery = db.session.query(
        CellClickEvent.user_id, func.max(CellClickEvent.id).label("last_event_id")
    ).filter(
        CellClickEvent.notebook_id == notebook_id,
        CellClickEvent.click_type == "ON",
        and_(
            CellClickEvent.time > t_start if t_start is not None else True,
            CellClickEvent.time <= t_end if t_end is not None else True,
        ),
    )

    if fetch_real_time:
        subquery = subquery.filter(
            CellClickEvent.user_id.in_(getConnectedStudentUserIds(notebook_id))
        )

    if selected_groups:
        subquery = subquery.filter(
            CellClickEvent.user_id.in_(
                select(getGroupsUserIdsSubquery(notebook_id, selected_groups))
            )
        )

    subquery = subquery.group_by(CellClickEvent.user_id).subquery()

    # first join with the previous subquery to only keep the rows with an id = last_event_id, then group by orig_cell_id
    query = (
        db.session.query(
            CellClickEvent.orig_cell_id,
            func.count(func.distinct(CellClickEvent.user_id)).label("user_count"),
        )
        .join(
            subquery,
            and_(
                CellClickEvent.user_id == subquery.c.user_id,
                CellClickEvent.id == subquery.c.last_event_id,
            ),
        )
        .group_by(CellClickEvent.orig_cell_id)
    )

    location_count = {}
    for orig_cell_id, user_count in query:
        location_count[orig_cell_id] = user_count

    return jsonify({"status": "success", "data": {"location_count": location_count}})


### Chat ###


@dashboard_bp.route("/<notebook_id>/connectedstudents", methods=["GET"])
def listConnectedStudents(notebook_id):
    return jsonify(getConnectedStudentUserIds(notebook_id)), 200


### Download notebook data ###
@dashboard_bp.route("/<notebook_id>/download_csv", methods=["GET"])
def downloadNotebookDataCSV(notebook_id):

    try:

        # parse query parameters
        t1_str = request.args.get("t1")
        t2_str = request.args.get("t2")

        # convert string to datetime object
        t1 = datetime.datetime.strptime(t1_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        t2 = datetime.datetime.strptime(t2_str, "%Y-%m-%dT%H:%M:%S.%f%z")

        polymorphic_join = with_polymorphic(
            Event, [CellExecution, CellClickEvent, NotebookClickEvent, CellAlteration]
        )

        rows = (
            db.session.query(polymorphic_join)
            .filter(Event.notebook_id == notebook_id)
            .filter(
                or_(
                    and_(
                        CellExecution.t_start.between(t1, t2),
                        CellExecution.cell_type == "MarkdownExecution",
                    ),
                    and_(
                        CellExecution.t_finish.between(t1, t2),
                        CellExecution.cell_type == "CodeExecution",
                    ),
                    CellClickEvent.time.between(t1, t2),
                    NotebookClickEvent.time.between(t1, t2),
                    CellAlteration.time.between(t1, t2),
                )
            )
            .yield_per(2000)
        )

        def generate():
            data = StringIO()
            w = csv.writer(data)

            columns = [
                "id",
                "__tablename__",
                "notebook_id",
                "user_id",
                "status",
                "cell_input",  # 'cell_output_model',
                "cell_type",
                "cell_id",
                "orig_cell_id",
                "click_type",
                "click_duration",
                "alteration_type",
                "time (UTC !)",
            ]

            # write header
            w.writerow(columns)
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

            # write each log item
            for row in rows:

                # time is encoded in t_start or t_finish in CellExecution rows, not in time
                time_value = (
                    getattr(row, "time", None)
                    or getattr(row, "t_finish", None)
                    or getattr(row, "t_start", None)
                )

                w.writerow(
                    (
                        list(getattr(row, column, None) for column in columns[:-1])
                        + [time_value.isoformat() if time_value else None]
                    )
                )
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)

        # stream the response as the data is generated
        response = Response(stream_with_context(generate()), mimetype="text/csv")
        # add the filename
        response.headers.set(
            "Content-Disposition", "attachment", filename=f"log_{notebook_id}.csv"
        )
        response.headers.set("Access-Control-Expose-Headers", "Content-Disposition")

        return response

    except Exception as e:
        return f"An error occurred while downloading the data: {str(e)}", 500


@dashboard_bp.route("/<notebook_id>/getgroups", methods=["GET"])
def getGroups(notebook_id):
    group_names = (
        db.session.query(UserGroups.group_name)
        .filter_by(notebook_id=notebook_id)
        .distinct()
        .all()
    )
    group_names = [name[0] for name in group_names]
    return jsonify(group_names)


@dashboard_bp.route("/<notebook_id>/pending_updates_stats", methods=["GET"])
@jwt_required()
def getPendingUpdatesStats(notebook_id):
    # Query to get the latest update per cell_id
    # First, find the latest timestamp for each cell_id
    latest_updates_subquery = (
        db.session.query(
            PendingUpdateInteraction.cell_id,
            func.max(PendingUpdateInteraction.timestamp).label("max_timestamp"),
        )
        .filter(
            PendingUpdateInteraction.notebook_id == notebook_id,
            PendingUpdateInteraction.update_id.isnot(None),
            PendingUpdateInteraction.action.in_(
                [PendingUpdateAction.UPDATE_NOW, PendingUpdateAction.UPDATE_LATER]
            ),
            PendingUpdateInteraction.sender_type == "teacher",  # Only teacher updates
        )
        .group_by(PendingUpdateInteraction.cell_id)
        .subquery()
    )

    # Then get the update_id for those latest timestamps
    latest_update_ids_subquery = (
        db.session.query(
            PendingUpdateInteraction.cell_id, PendingUpdateInteraction.update_id
        )
        .join(
            latest_updates_subquery,
            db.and_(
                PendingUpdateInteraction.cell_id == latest_updates_subquery.c.cell_id,
                PendingUpdateInteraction.timestamp
                == latest_updates_subquery.c.max_timestamp,
            ),
        )
        .filter(
            PendingUpdateInteraction.notebook_id == notebook_id,
            PendingUpdateInteraction.action.in_(
                [PendingUpdateAction.UPDATE_NOW, PendingUpdateAction.UPDATE_LATER]
            ),
            PendingUpdateInteraction.sender_type == "teacher",  # Only teacher updates
        )
        .distinct()
        .subquery()
    )

    # Now query to count actions per cell_id using only the latest update_id
    results = (
        db.session.query(
            PendingUpdateInteraction.cell_id,
            PendingUpdateInteraction.update_id,
            PendingUpdateInteraction.action,
            func.count(PendingUpdateInteraction.user_id),
            func.min(PendingUpdateInteraction.timestamp),
        )
        .join(
            latest_update_ids_subquery,
            db.and_(
                PendingUpdateInteraction.cell_id
                == latest_update_ids_subquery.c.cell_id,
                PendingUpdateInteraction.update_id
                == latest_update_ids_subquery.c.update_id,
            ),
        )
        .filter(
            PendingUpdateInteraction.notebook_id == notebook_id,
            PendingUpdateInteraction.action.in_(
                [PendingUpdateAction.UPDATE_NOW, PendingUpdateAction.UPDATE_LATER]
            ),
            PendingUpdateInteraction.sender_type == "teacher",  # Only teacher updates
        )
        .group_by(
            PendingUpdateInteraction.cell_id,
            PendingUpdateInteraction.update_id,
            PendingUpdateInteraction.action,
        )
        .all()
    )

    stats = {}
    for cell_id, update_id, action, count, timestamp in results:
        # Group by cell_id instead of update_id
        if cell_id not in stats:
            stats[cell_id] = {
                "update_id": update_id,  # Store the latest update_id for this cell
                "cell_id": cell_id,
                "timestamp": timestamp.isoformat(),
                "update_now": 0,
                "update_later": 0,
            }

        if action == PendingUpdateAction.UPDATE_NOW:
            stats[cell_id]["update_now"] = count
        elif action == PendingUpdateAction.UPDATE_LATER:
            stats[cell_id]["update_later"] = count

    # Fetch detailed actions for students who selected "Update Later"
    for cell_id in stats.keys():
        # Get the update_id for this cell
        update_id = stats[cell_id]["update_id"]

        # First, get all users who clicked "Update Later" for this update
        users_who_delayed = (
            db.session.query(PendingUpdateInteraction.user_id)
            .filter(
                PendingUpdateInteraction.notebook_id == notebook_id,
                PendingUpdateInteraction.update_id == update_id,
                PendingUpdateInteraction.action == PendingUpdateAction.UPDATE_LATER,
                PendingUpdateInteraction.sender_type
                == "teacher",  # Only teacher updates
            )
            .distinct()
            .all()
        )

        delayed_user_ids = {user_id for (user_id,) in users_who_delayed}

        # Get all subsequent actions from those users (APPLY_SINGLE, REMOVE_SINGLE, UPDATE_ALL, DELETE_ALL)
        subsequent_actions = (
            db.session.query(
                PendingUpdateInteraction.user_id,
                PendingUpdateInteraction.action,
                PendingUpdateInteraction.timestamp,
            )
            .filter(
                PendingUpdateInteraction.notebook_id == notebook_id,
                PendingUpdateInteraction.update_id == update_id,
                PendingUpdateInteraction.action.in_(
                    [
                        PendingUpdateAction.APPLY_SINGLE,
                        PendingUpdateAction.REMOVE_SINGLE,
                        PendingUpdateAction.UPDATE_ALL,
                        PendingUpdateAction.DELETE_ALL,
                    ]
                ),
                PendingUpdateInteraction.user_id.in_(delayed_user_ids),
                PendingUpdateInteraction.sender_type
                == "teacher",  # Only teacher updates
            )
            .all()
        )

        stats[cell_id]["detailed_actions"] = [
            {
                "user_id": user_id,
                "action": action.value,
                "timestamp": timestamp.isoformat(),
            }
            for user_id, action, timestamp in subsequent_actions
        ]

    # Sort by timestamp descending
    sorted_stats = sorted(stats.values(), key=lambda x: x["timestamp"], reverse=True)

    return jsonify(sorted_stats)
