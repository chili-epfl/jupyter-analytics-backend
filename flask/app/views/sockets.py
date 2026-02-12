from flask_socketio import send, join_room, leave_room, ConnectionRefusedError, emit
from app import socketio, redis_client
from app.models.models import ConnectionType, Notebook, TeammateLocation, db
from flask import request, session
from app.utils.utils import hash_user_id_with_salt
from datetime import datetime, timezone


@socketio.on("connect")
def handle_connect():
    """Handle WebSocket connection for students and teachers."""
    try:
        con_type = ConnectionType(request.args.get("conType"))
    except ValueError as e:
        raise ConnectionRefusedError("Invalid connection type")

    user_id = request.args.get("userId")
    if user_id:
        user_id = hash_user_id_with_salt(user_id)

    notebook_id = request.args.get("nbId")

    if (not user_id) or (not notebook_id):
        # no required identifiers
        raise ConnectionRefusedError("Missing required identifiers")

    # check that the notebook is registered
    notebook = Notebook.query.filter_by(notebook_id=notebook_id).first()
    if not notebook:
        # notebook not registered
        raise ConnectionRefusedError("Notebook not registered")

    # add to the appropriate list of connected users in the redis cache
    redis_client.sadd(f"connected_{con_type.name.lower()}s:{notebook_id}", user_id)
    # add to the all-students or all-teachers room
    room_name = con_type.name.lower() + "_" + notebook_id
    join_room(room_name)
    # add to a room specific to that user_id
    personal_user_room_name = con_type.name.lower() + "_" + user_id + "_" + notebook_id
    join_room(personal_user_room_name)

    session["con_type"] = con_type.name
    session["user_id"] = user_id
    session["notebook_id"] = notebook_id

    # Notify teammates of new connection
    if con_type == ConnectionType.STUDENT:
        emit(
            "teammate_connected",
            {"userId": user_id},
            room=room_name,
            include_self=False,
        )


@socketio.on("disconnect")
def handle_disconnect():
    """Handle WebSocket disconnection and cleanup resources."""
    try:
        con_type = ConnectionType(request.args.get("conType"))
    except ValueError as e:
        raise ConnectionRefusedError("Invalid connection type")

    user_id = request.args.get("userId")
    if user_id:
        user_id = hash_user_id_with_salt(user_id)

    notebook_id = request.args.get("nbId")

    if user_id:
        # remove from the list of connected users
        redis_client.srem(f"connected_{con_type.name.lower()}s:{notebook_id}", user_id)

    # Notify teammates of disconnection before leaving the room
    room_name = con_type.name.lower() + "_" + notebook_id
    if con_type == ConnectionType.STUDENT:
        # Clear location from database
        if user_id and notebook_id:
            try:
                TeammateLocation.query.filter_by(
                    user_id=user_id, notebook_id=notebook_id
                ).delete()
                db.session.commit()
            except Exception as e:
                db.session.rollback()

        # Get teammates in the same groups to notify them
        from app.models.models import UserGroups, UserGroupAssociation

        group_pk_rows = (
            db.session.query(UserGroupAssociation.c.group_pk)
            .join(UserGroups, UserGroupAssociation.c.group_pk == UserGroups.group_pk)
            .filter(
                UserGroupAssociation.c.user_id == user_id,
                UserGroups.notebook_id == notebook_id,
            )
            .distinct()
            .all()
        )
        group_pks = [r[0] for r in group_pk_rows]

        if group_pks:
            teammate_rows = (
                db.session.query(UserGroupAssociation.c.user_id)
                .filter(
                    UserGroupAssociation.c.group_pk.in_(group_pks),
                    UserGroupAssociation.c.user_id != user_id,
                )
                .distinct()
                .all()
            )
            teammate_ids = [r[0] for r in teammate_rows]

            # Notify each teammate
            for teammate_id in teammate_ids:
                emit(
                    "teammate_disconnected",
                    {"userId": user_id},
                    to=f"student_{teammate_id}_{notebook_id}",
                )
                emit(
                    "teammate_location_cleared",
                    {"userId": user_id},
                    to=f"student_{teammate_id}_{notebook_id}",
                )

    # remove from the rooms
    room_name = con_type.name.lower() + "_" + notebook_id
    leave_room(room_name)

    personal_user_room_name = con_type.name.lower() + "_" + user_id + "_" + notebook_id
    leave_room(personal_user_room_name)

    if session.get("con_type", None):
        del session["con_type"]
    if session.get("user_id", None):
        del session["user_id"]
    if session.get("notebook_id", None):
        del session["notebook_id"]


@socketio.on("sendmessage")
def handle_sendmessage(message):
    """Handle simple message echo (legacy endpoint)."""
    send("response")


@socketio.on("send_message")
def handle_send_message(data):
    """Handle direct message between users (teacher-student communication)."""
    target_user_id = data["userId"]
    message = data["message"]
    # send message to the target user
    if session.get("con_type", None) == ConnectionType.STUDENT.name:
        target_con_type = ConnectionType.TEACHER.name
        sender_type = "student"  # Student is sending to teacher
    elif session.get("con_type", None) == ConnectionType.TEACHER.name:
        target_con_type = ConnectionType.STUDENT.name
        sender_type = "teacher"  # Teacher is sending to student

        # If teacher is sending an update, check for override scenarios
        try:
            import json
            from app.models.models import PendingUpdateInteraction, PendingUpdateAction

            # Try to parse the message to extract cell_id and update_id
            if message and "{" in message:
                json_start = message.index("{")
                json_str = message[json_start:]
                parsed = json.loads(json_str)

                cell_id = None
                new_update_id = parsed.get("update_id")

                # Extract cell_id
                if "content" in parsed:
                    cell_id = parsed["content"].get("id") or parsed["content"].get(
                        "cell_id"
                    )

                if cell_id and new_update_id and session.get("notebook_id"):
                    notebook_id = session["notebook_id"]
                    sender_user_id = session["user_id"]

                    # Find students who have UPDATE_LATER for this cell (any update_id)
                    pending_updates = PendingUpdateInteraction.query.filter(
                        PendingUpdateInteraction.notebook_id == notebook_id,
                        PendingUpdateInteraction.cell_id == cell_id,
                        PendingUpdateInteraction.action
                        == PendingUpdateAction.UPDATE_LATER,
                        PendingUpdateInteraction.update_id
                        != new_update_id,  # Different update_id
                    ).all()

                    if pending_updates:
                        # Group by user_id and old update_id
                        users_to_override = {}
                        for pu in pending_updates:
                            if pu.user_id not in users_to_override:
                                users_to_override[pu.user_id] = []
                            users_to_override[pu.user_id].append(pu.update_id)

                        # Log OVERRIDE actions for each student
                        for user_id, old_update_ids in users_to_override.items():
                            for old_update_id in old_update_ids:
                                override_interaction = PendingUpdateInteraction(
                                    notebook_id=notebook_id,
                                    user_id=user_id,
                                    cell_id=cell_id,
                                    update_id=old_update_id,  # Reference the old update that's being overridden
                                    action=PendingUpdateAction.OVERRIDE,
                                    sender=sender_user_id,
                                    sender_type=sender_type,
                                    timestamp=datetime.now(timezone.utc),
                                )
                                db.session.add(override_interaction)

                        db.session.commit()

        except Exception as e:
            pass
    else:
        target_con_type = None
        sender_type = "unknown"

    if (
        target_user_id
        and message
        and target_con_type
        and session.get("notebook_id", None)
        and session.get("user_id", None)
    ):
        target_user_room_name = (
            target_con_type.lower()
            + "_"
            + target_user_id
            + "_"
            + session["notebook_id"]
        )
        # Send the actual sender's user_id and sender_type
        sender_user_id = session["user_id"]
        emit(
            "chat",
            {"message": message, "sender": sender_user_id, "sender_type": sender_type},
            to=target_user_room_name,
        )


@socketio.on("update_location")
def handle_update_location(data):
    """Handle location update from a student and broadcast to teammates."""
    user_id = session.get("user_id")
    notebook_id = session.get("notebook_id")
    con_type_str = session.get("con_type")

    if not user_id or not notebook_id or con_type_str != "STUDENT":
        return

    cell_id = data.get("cellId")
    cell_index = data.get("cellIndex")

    if not cell_id:
        return

    try:
        # Update or create location in database
        location = TeammateLocation.query.filter_by(
            user_id=user_id, notebook_id=notebook_id
        ).first()

        if location:
            location.cell_id = cell_id
            location.cell_index = cell_index
            location.updated_at = datetime.now(timezone.utc)
        else:
            location = TeammateLocation(
                user_id=user_id,
                notebook_id=notebook_id,
                cell_id=cell_id,
                cell_index=cell_index,
                updated_at=datetime.now(timezone.utc),
            )
            db.session.add(location)

        db.session.commit()

        # Get teammates in the same groups
        from app.models.models import UserGroups, UserGroupAssociation

        # Find groups the user belongs to
        group_pk_rows = (
            db.session.query(UserGroupAssociation.c.group_pk)
            .join(UserGroups, UserGroupAssociation.c.group_pk == UserGroups.group_pk)
            .filter(
                UserGroupAssociation.c.user_id == user_id,
                UserGroups.notebook_id == notebook_id,
            )
            .distinct()
            .all()
        )
        group_pks = [r[0] for r in group_pk_rows]

        if not group_pks:
            return

        # Find all teammates in the same groups
        teammate_rows = (
            db.session.query(UserGroupAssociation.c.user_id)
            .filter(
                UserGroupAssociation.c.group_pk.in_(group_pks),
                UserGroupAssociation.c.user_id != user_id,
            )
            .distinct()
            .all()
        )
        teammate_ids = [r[0] for r in teammate_rows]

        # Broadcast to each teammate's personal room
        for teammate_id in teammate_ids:
            teammate_room = f"student_{teammate_id}_{notebook_id}"
            emit(
                "teammate_location_update",
                {"userId": user_id, "cellId": cell_id, "cellIndex": cell_index},
                to=teammate_room,
            )
    except Exception as e:
        db.session.rollback()


@socketio.on("group_message")
def handle_group_message(data):
    """Handle messages sent between teammates in a group."""
    target_user_id = data.get("userId")
    message = data.get("message")

    if not target_user_id or not message:
        return

    notebook_id = session.get("notebook_id", None)
    sender_user_id = session.get("user_id", None)

    if not notebook_id or not sender_user_id:
        return

    # Check for OVERRIDE scenarios (similar to teacher updates)
    try:
        import json
        from app.models.models import PendingUpdateInteraction, PendingUpdateAction

        # Try to parse the message to extract cell_id and update_id
        if message and "{" in message:
            json_start = message.index("{")
            json_str = message[json_start:]
            parsed = json.loads(json_str)

            cell_id = None
            new_update_id = parsed.get("update_id")

            # Extract cell_id
            if "content" in parsed:
                cell_id = parsed["content"].get("id") or parsed["content"].get(
                    "cell_id"
                )

            if cell_id and new_update_id:
                # Find teammates who have UPDATE_LATER for this cell
                pending_updates = PendingUpdateInteraction.query.filter(
                    PendingUpdateInteraction.notebook_id == notebook_id,
                    PendingUpdateInteraction.cell_id == cell_id,
                    PendingUpdateInteraction.action == PendingUpdateAction.UPDATE_LATER,
                    PendingUpdateInteraction.update_id != new_update_id,
                ).all()

                if pending_updates:
                    # Group by user_id and old update_id
                    users_to_override = {}
                    for pu in pending_updates:
                        if pu.user_id not in users_to_override:
                            users_to_override[pu.user_id] = []
                        users_to_override[pu.user_id].append(pu.update_id)

                    # Log OVERRIDE actions for each teammate
                    for user_id, old_update_ids in users_to_override.items():
                        for old_update_id in old_update_ids:
                            override_interaction = PendingUpdateInteraction(
                                notebook_id=notebook_id,
                                user_id=user_id,
                                cell_id=cell_id,
                                update_id=old_update_id,
                                action=PendingUpdateAction.OVERRIDE,
                                sender=sender_user_id,
                                sender_type="teammate",
                                timestamp=datetime.now(timezone.utc),
                            )
                            db.session.add(override_interaction)

                    db.session.commit()

    except Exception as e:
        pass

    # Send to the target student's personal room
    target_user_room_name = f"student_{target_user_id}_{notebook_id}"
    emit("group_chat", f"From {sender_user_id}: {message}", to=target_user_room_name)
