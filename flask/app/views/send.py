from flask import Blueprint, request, jsonify
import datetime
from app import db, socketio
from app.models.models import (
    CellExecution,
    CellClickEvent,
    ConnectionType,
    NotebookClickEvent,
    CellAlteration,
    Notebook,
    PendingUpdateInteraction,
    PendingUpdateAction,
)
from app.utils.constants import MAX_PAYLOAD_SIZE
from app.utils.cache import check_refresh_cache
from app.utils.utils import hash_user_id_with_salt

send_bp = Blueprint("send", __name__)


# check the token, the notebook id and the payload size
def payload_check_middleware():

    if request.method == "OPTIONS":
        return (
            jsonify("OK"),
            200,
        )  # respond to OPTIONS preflight request with a 200 status

    # check if the payload size exceeds the limit
    payload_size = len(request.data)
    if payload_size > MAX_PAYLOAD_SIZE:
        return jsonify("Payload size exceeds the limit"), 413

    data = request.get_json()
    notebook_id = data.get("notebook_id")

    # check if the notebook_id exists in the database
    notebook = Notebook.query.filter_by(notebook_id=notebook_id).first()
    if not notebook:
        return jsonify("Notebook not found"), 404

    return


# apply the check before every /send request
send_bp.before_request(payload_check_middleware)


# notify all the connected users with a notebook_id that some new data was posted
def websocket_post_to_client(response):

    if request.method == "OPTIONS":
        return response  # let OPTIONS preflight requests through

    notebook_id = request.get_json().get("notebook_id")
    # go through only if the POST request added something to the database
    if (200 <= response.status_code < 300) and notebook_id:

        # to limit frequency of refresh requests
        should_send_refresh_request = check_refresh_cache(notebook_id)

        if should_send_refresh_request:
            # broadcast refresh dashboard message to all teachers in the notebook room
            room_name = ConnectionType.TEACHER.name.lower() + "_" + notebook_id
            socketio.emit("refreshDashboard", to=room_name)

    return response


send_bp.after_request(websocket_post_to_client)


@send_bp.route("/exec/code", methods=["POST"])
def postCodeExec():
    data = request.get_json()
    hashed_user_id = hash_user_id_with_salt(data["user_id"])

    try:

        new_code_exec = CellExecution(
            notebook_id=data["notebook_id"],
            user_id=hashed_user_id,
            cell_id=data["cell_id"],
            orig_cell_id=data["orig_cell_id"],
            t_start=datetime.datetime.strptime(
                data["t_start"], "%Y-%m-%dT%H:%M:%S.%f%z"
            ),
            cell_input=data["cell_input"],
            cell_type="CodeExecution",
            language_mimetype=data["language_mimetype"],
            t_finish=datetime.datetime.strptime(
                data["t_finish"], "%Y-%m-%dT%H:%M:%S.%f%z"
            ),
            status=data["status"],
            cell_output_model=data["cell_output_model"],
            cell_output_length=data["cell_output_length"],
        )
        db.session.add(new_code_exec)
        db.session.commit()
        return jsonify("Code OK")

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@send_bp.route("/exec/markdown", methods=["POST"])
def postMarkdownExec():
    data = request.get_json()
    hashed_user_id = hash_user_id_with_salt(data["user_id"])

    try:
        new_md_exec = CellExecution(
            notebook_id=data["notebook_id"],
            user_id=hashed_user_id,
            cell_id=data["cell_id"],
            orig_cell_id=data["orig_cell_id"],
            t_start=datetime.datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S.%f%z"),
            cell_input=data["cell_content"],
            cell_type="MarkdownExecution",
        )
        db.session.add(new_md_exec)
        db.session.commit()
        return jsonify("Markdown OK")

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@send_bp.route("/clickevent/cell", methods=["POST"])
def postCellClickEvent():
    data = request.get_json()
    hashed_user_id = hash_user_id_with_salt(data["user_id"])

    try:
        new_click_event = CellClickEvent(
            notebook_id=data["notebook_id"],
            user_id=hashed_user_id,
            cell_id=data["cell_id"],
            orig_cell_id=data["orig_cell_id"],
            time=datetime.datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S.%f%z"),
            click_duration=data["click_duration"],
            click_type=data["click_type"],
        )

        db.session.add(new_click_event)
        db.session.commit()
        return jsonify("CellClick OK")

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@send_bp.route("/clickevent/notebook", methods=["POST"])
def postNotebookClickEvent():
    data = request.get_json()
    hashed_user_id = hash_user_id_with_salt(data["user_id"])

    try:
        new_click_event = NotebookClickEvent(
            notebook_id=data["notebook_id"],
            user_id=hashed_user_id,
            time=datetime.datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S.%f%z"),
            click_duration=data["click_duration"],
            click_type=data["click_type"],
        )

        db.session.add(new_click_event)
        db.session.commit()
        return jsonify("NotebookClick OK")

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@send_bp.route("/alter", methods=["POST"])
def postAlterEvent():
    data = request.get_json()
    hashed_user_id = hash_user_id_with_salt(data["user_id"])

    try:
        new_alter_event = CellAlteration(
            notebook_id=data["notebook_id"],
            user_id=hashed_user_id,
            cell_id=data["cell_id"],
            alteration_type=data["alteration_type"],
            time=datetime.datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S.%f%z"),
        )

        db.session.add(new_alter_event)
        db.session.commit()
        return jsonify("Alteration OK")

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@send_bp.route("/pending_update_interaction", methods=["POST"])
def postPendingUpdateInteraction():
    """Record a user's interaction with a pending cell update.
    
    This endpoint logs telemetry data for how users respond to pending updates
    (e.g., UPDATE_NOW, UPDATE_LATER, OVERRIDE). Tracks user actions along with
    the sender information (teacher or teammate) for analytics purposes.
    """
    data = request.get_json()

    hashed_user_id = hash_user_id_with_salt(data["user_id"])

    # Hash the sender if provided
    sender_hashed = None
    sender_type = data.get("sender_type")  # Get sender_type from frontend
    if data.get("sender"):
        sender_hashed = hash_user_id_with_salt(data["sender"])

    cell_id = data.get("cell_id")
    update_id = data.get("update_id")
    action = data.get("action")

    try:
        action_enum = PendingUpdateAction[action]

        new_interaction = PendingUpdateInteraction(
            notebook_id=data["notebook_id"],
            user_id=hashed_user_id,
            cell_id=cell_id,  # optional
            update_id=update_id,
            action=action_enum,
            sender=sender_hashed,  # hashed sender user_id
            sender_type=sender_type,  # 'teacher' or 'teammate'
            timestamp=datetime.datetime.strptime(
                data["time"], "%Y-%m-%dT%H:%M:%S.%f%z"
            ),
        )
        db.session.add(new_interaction)
        db.session.commit()
        return jsonify("PendingUpdateInteraction OK")

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500
