from flask import Blueprint, request, jsonify
from app import db, redis_client
from app.models.models import UserGroups, Users, UserGroupAssociation, TeammateLocation
from datetime import datetime, timedelta, timezone
from app.utils.utils import hash_user_id_with_salt
from app.views.dashboard import getGroupsUserIdsSubquery
import json
from sqlalchemy import func


groups_bp = Blueprint("groups", __name__)


@groups_bp.route("/add", methods=["POST"])
def add_group():
    """Create a new user group for a notebook.
    
    Creates a group with the specified name and associates the provided users with it.
    """
    data = request.get_json()
    try:
        group = UserGroups(
            group_name=data.get("group_name", None),
            notebook_id=data.get("notebook_id", None),
        )

        users = []
        non_hashed_user_ids = data.get("user_ids", [])
        user_ids = [hash_user_id_with_salt(elem) for elem in non_hashed_user_ids]
        for user_id in user_ids:
            # check if the user already exists
            user = Users.query.filter_by(user_id=user_id).first()
            if user is None:
                # if the user does not exist, create it
                user = Users(user_id=user_id)
                db.session.add(user)
            users.append(user)

        group.group_users.extend(users)

        db.session.add(group)
        db.session.commit()
        return jsonify(f"Group {data.get('group_name', None)} added")

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@groups_bp.route("/delete", methods=["DELETE"])
def delete_group():
    """Delete a user group by group name and notebook ID."""
    data = request.get_json()
    try:
        group_pk = f"{data.get('group_name', '')}-{data.get('notebook_id', '')}"
        group = UserGroups.query.filter_by(group_pk=group_pk).first()
        if group:
            db.session.delete(group)
            db.session.commit()
            return jsonify(f"Group {data.get('group_name', None)} deleted"), 200
        else:
            return jsonify("Group not found"), 404

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@groups_bp.route("/update", methods=["PUT"])
def update_group():
    """Update the users in an existing group.
    
    Accepts a complete list of user IDs that should be in the group.
    Adds new users and removes users no longer in the list.
    """
    data = request.get_json()
    try:
        group_pk = f"{data.get('group_name', '')}-{data.get('notebook_id', '')}"
        group = UserGroups.query.filter_by(group_pk=group_pk).first()
        if group:
            # assume user_ids is the complete set of users that should now be in the group
            current_user_ids = set(user.user_id for user in group.group_users)
            new_user_ids = set(
                [hash_user_id_with_salt(elem) for elem in data.get("user_ids", [])]
            )
            users_to_add = new_user_ids - current_user_ids
            users_to_remove = current_user_ids - new_user_ids

            # add new users to the group
            for user_id in users_to_add:
                user = Users.query.filter_by(user_id=user_id).first()
                if user is None:
                    user = Users(user_id=user_id)
                    db.session.add(user)
                group.group_users.append(user)

            # remove users no longer in the group
            for user_id in users_to_remove:
                user = Users.query.filter_by(user_id=user_id).first()
                if user:
                    group.group_users.remove(user)

            db.session.commit()
            return jsonify(f"Group {group.group_name} updated"), 200
        else:
            return jsonify("Group not found"), 404

    except Exception as e:
        db.session.rollback()
        return f"An error occurred: {str(e)}", 500


@groups_bp.route("/getusers", methods=["GET"])
def get_users():
    """Get the user IDs for the selected groups in a notebook."""
    notebook_id = request.args.get("notebookId", None)
    # group_name = request.args.get('groupName', None)

    # if group_name :
    #     group_userids_subquery = getGroupUserIdsSubquery(notebook_id, group_name)

    selected_groups = request.args.get("selectedGroups", None)

    if selected_groups:

        selected_groups = json.loads(selected_groups)
        group_userids_subquery = getGroupsUserIdsSubquery(notebook_id, selected_groups)

        results = db.session.query(group_userids_subquery).all()

        user_ids = [r[0] for r in results]
    else:
        user_ids = []

    return jsonify(user_ids), 200


@groups_bp.route("testgroup", methods=["GET"])
def test_group():
    """Test endpoint for validating group selection parsing."""
    selected_groups = request.args.get("selectedGroups", None)

    if selected_groups:
        selected_groups = json.loads(selected_groups)

        return jsonify(selected_groups)
    else:
        return jsonify("No groups")


@groups_bp.route("/users/<user_id>/teammates", methods=["GET"])
def get_teammates(user_id):
    """Get the teammates of a user in the same groups for a given notebook."""
    notebook_id = request.args.get("notebookId", None)
    if not notebook_id:
        return jsonify({"error": "Missing notebookId"}), 400

    # incoming user_id is unhashed
    hashed_user_id = hash_user_id_with_salt(user_id)

    # find groups in this notebook that the user belongs to
    group_pk_rows = (
        db.session.query(UserGroupAssociation.c.group_pk)
        .join(UserGroups, UserGroupAssociation.c.group_pk == UserGroups.group_pk)
        .filter(
            UserGroupAssociation.c.user_id == hashed_user_id,
            UserGroups.notebook_id == notebook_id,
        )
        .distinct()
        .all()
    )
    group_pks = [r[0] for r in group_pk_rows]

    if not group_pks:
        return jsonify([]), 200

    # find all users in those groups excluding the given user
    teammate_rows = (
        db.session.query(Users.user_id)
        .join(UserGroupAssociation, UserGroupAssociation.c.user_id == Users.user_id)
        .filter(
            UserGroupAssociation.c.group_pk.in_(group_pks),
            Users.user_id != hashed_user_id,
        )
        .distinct()
        .all()
    )
    teammates = [r[0] for r in teammate_rows]

    return jsonify(teammates), 200


@groups_bp.route("/users/<user_id>/teammates/connected", methods=["GET"])
def get_connected_teammates(user_id):
    """Get connected teammates for a user (teammates who are currently connected via websocket)."""
    notebook_id = request.args.get("notebookId", None)
    if not notebook_id:
        return jsonify("Missing notebookId"), 400

    # Hash the incoming user_id
    hashed_user_id = hash_user_id_with_salt(user_id)

    # Find groups in this notebook that the user belongs to
    group_pk_rows = (
        db.session.query(UserGroupAssociation.c.group_pk)
        .join(UserGroups, UserGroupAssociation.c.group_pk == UserGroups.group_pk)
        .filter(
            UserGroupAssociation.c.user_id == hashed_user_id,
            UserGroups.notebook_id == notebook_id,
        )
        .distinct()
        .all()
    )
    group_pks = [r[0] for r in group_pk_rows]

    if not group_pks:
        return jsonify([]), 200

    # Find all users in those groups excluding the given user (these are HASHED)
    teammate_rows = (
        db.session.query(UserGroupAssociation.c.user_id)
        .filter(
            UserGroupAssociation.c.group_pk.in_(group_pks),
            UserGroupAssociation.c.user_id != hashed_user_id,
        )
        .distinct()
        .all()
    )
    all_teammates_hashed = {r[0] for r in teammate_rows}

    # Return early if no teammates
    if not all_teammates_hashed:
        return jsonify([]), 200

    # Get currently connected students from Redis cache
    # NOTE: These are ALREADY HASHED (see sockets.py handle_connect)
    connected_student_ids_raw = redis_client.smembers(
        f"connected_students:{notebook_id}"
    )

    # Decode bytes to strings - NO hashing needed since they're already hashed
    connected_set_hashed = {uid.decode("utf-8") for uid in connected_student_ids_raw}

    # Filter teammates to only those who are currently connected
    connected_teammates = list(all_teammates_hashed & connected_set_hashed)

    return jsonify(connected_teammates), 200


@groups_bp.route("/users/<user_id>/groups/names", methods=["GET"])
def get_user_group_names(user_id):
    """Get group names for a specific user."""
    notebook_id = request.args.get("notebookId", None)

    # Hash the incoming user_id
    hashed_user_id = hash_user_id_with_salt(user_id)

    # Build query for groups the user belongs to
    query = (
        db.session.query(
            UserGroups.group_name, UserGroups.group_pk, UserGroups.notebook_id
        )
        .join(
            UserGroupAssociation, UserGroupAssociation.c.group_pk == UserGroups.group_pk
        )
        .filter(UserGroupAssociation.c.user_id == hashed_user_id)
    )

    # Optionally filter by notebook_id if provided
    if notebook_id:
        query = query.filter(UserGroups.notebook_id == notebook_id)

    group_rows = query.distinct().all()

    groups = [
        {"group_name": r[0], "group_pk": r[1], "notebook_id": r[2]} for r in group_rows
    ]

    return jsonify(groups), 200


@groups_bp.route("/notebook/<notebook_id>/getgroups", methods=["GET"])
def get_groups_for_notebook(notebook_id):
    """Get all groups for a specific notebook."""

    # Query groups for this notebook with user count
    groups = (
        db.session.query(
            UserGroups.group_name,
            UserGroups.group_pk,
            func.count(UserGroupAssociation.c.user_id).label("user_count"),
        )
        .outerjoin(
            UserGroupAssociation, UserGroupAssociation.c.group_pk == UserGroups.group_pk
        )
        .filter(UserGroups.notebook_id == notebook_id)
        .group_by(UserGroups.group_name, UserGroups.group_pk)
        .all()
    )

    result = [
        {"group_name": g[0], "group_pk": g[1], "user_count": g[2]} for g in groups
    ]

    return jsonify(result), 200


@groups_bp.route("/location/update", methods=["POST"])
def update_user_location():
    """Update the current cell location for a user."""
    data = request.get_json()
    user_id = data.get("userId")
    notebook_id = data.get("notebookId")
    cell_id = data.get("cellId")
    cell_index = data.get("cellIndex")

    if not user_id or not notebook_id or not cell_id:
        return jsonify({"error": "Missing required fields"}), 400

    hashed_user_id = hash_user_id_with_salt(user_id)

    try:
        # Upsert the location
        existing = TeammateLocation.query.filter_by(
            user_id=hashed_user_id, notebook_id=notebook_id
        ).first()

        if existing:
            existing.cell_id = cell_id
            existing.cell_index = cell_index
            existing.updated_at = datetime.now(timezone.utc)
        else:
            new_location = TeammateLocation(
                user_id=hashed_user_id,
                notebook_id=notebook_id,
                cell_id=cell_id,
                cell_index=cell_index,
                updated_at=datetime.now(timezone.utc),
            )
            db.session.add(new_location)

        db.session.commit()

        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@groups_bp.route("/location/teammates", methods=["GET"])
def get_teammates_locations():
    """Get current locations of all connected teammates."""
    user_id = request.args.get("userId")
    notebook_id = request.args.get("notebookId")

    if not user_id or not notebook_id:
        return jsonify({"error": "Missing required fields"}), 400

    hashed_user_id = hash_user_id_with_salt(user_id)

    # Find groups the user belongs to
    group_pk_rows = (
        db.session.query(UserGroupAssociation.c.group_pk)
        .join(UserGroups, UserGroupAssociation.c.group_pk == UserGroups.group_pk)
        .filter(
            UserGroupAssociation.c.user_id == hashed_user_id,
            UserGroups.notebook_id == notebook_id,
        )
        .distinct()
        .all()
    )
    group_pks = [r[0] for r in group_pk_rows]

    if not group_pks:
        return jsonify([]), 200

    # Find all teammates (users in same groups)
    teammate_rows = (
        db.session.query(UserGroupAssociation.c.user_id)
        .filter(
            UserGroupAssociation.c.group_pk.in_(group_pks),
            UserGroupAssociation.c.user_id != hashed_user_id,
        )
        .distinct()
        .all()
    )
    teammate_ids = [r[0] for r in teammate_rows]

    # Return early if no teammates
    if not teammate_ids:
        return jsonify([]), 200

    # Get connected teammates from Redis
    connected_student_ids_raw = redis_client.smembers(
        f"connected_students:{notebook_id}"
    )
    connected_set = {uid.decode("utf-8") for uid in connected_student_ids_raw}

    # Filter to only connected teammates
    connected_teammates = [tid for tid in teammate_ids if tid in connected_set]

    # Return early if no connected teammates
    if not connected_teammates:
        return jsonify([]), 200

    # Get their locations (only recent - within last 5 minutes)
    cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
    locations = TeammateLocation.query.filter(
        TeammateLocation.user_id.in_(connected_teammates),
        TeammateLocation.notebook_id == notebook_id,
        TeammateLocation.updated_at >= cutoff_time,
    ).all()

    result = [
        {
            "userId": loc.user_id,
            "cellId": loc.cell_id,
            "cellIndex": loc.cell_index,
            "updatedAt": loc.updated_at.isoformat(),
        }
        for loc in locations
    ]

    return jsonify(result), 200


@groups_bp.route("/users/<user_id>/role", methods=["GET"])
def get_user_role(user_id):
    """Get the role of a user based on their connection type."""
    notebook_id = request.args.get("notebookId", None)
    if not notebook_id:
        return jsonify({"error": "Missing notebookId"}), 400

    hashed_user_id = hash_user_id_with_salt(user_id)

    # Check if user is connected as a teacher
    teacher_key = f"connected_teachers:{notebook_id}"
    is_teacher = redis_client.sismember(teacher_key, hashed_user_id)

    if is_teacher:
        return jsonify({"role": "teacher"}), 200
    else:
        return jsonify({"role": "student"}), 200


@groups_bp.route("/location/clear", methods=["DELETE"])
def clear_user_location():
    """Clear location when user disconnects."""
    user_id = request.args.get("userId")
    notebook_id = request.args.get("notebookId")

    if not user_id or not notebook_id:
        return jsonify({"error": "Missing required fields"}), 400

    hashed_user_id = hash_user_id_with_salt(user_id)

    try:
        TeammateLocation.query.filter_by(
            user_id=hashed_user_id, notebook_id=notebook_id
        ).delete()
        db.session.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
