from flask import Blueprint, request, jsonify
from app import db
from app.models.models import UserGroups, Users
from app.utils.utils import hash_user_id_with_salt
# from app.views.dashboard import getGroupsUserIdsSubquery
# import json

groups_bp = Blueprint('groups', __name__)

@groups_bp.route('/add', methods=['POST'])
def add_group():

    data = request.get_json()
    try:
        group = UserGroups(group_name=data.get("group_name", None), notebook_id=data.get("notebook_id", None))

        users = []
        non_hashed_user_ids = data.get('user_ids', [])
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
        return f'An error occurred: {str(e)}', 500
    
@groups_bp.route('/update', methods=['PUT'])
def update_group():
    data = request.get_json()
    try:
        group_pk = f"{data.get('group_name', '')}-{data.get('notebook_id', '')}"
        group = UserGroups.query.filter_by(group_pk=group_pk).first()
        if group:
            # assume user_ids is the complete set of users that should now be in the group
            current_user_ids = set(user.user_id for user in group.group_users)
            new_user_ids = set([hash_user_id_with_salt(elem) for elem in data.get('user_ids', [])])
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
        return f'An error occurred: {str(e)}', 500

# import json
# from app.views.dashboard import getGroupsUserIdsSubquery
# @groups_bp.route('/getusers', methods=['GET'])
# def get_users():
#     notebook_id = request.args.get('notebookId', None)
#     # group_name = request.args.get('groupName', None)

#     # if group_name : 
#     #     group_userids_subquery = getGroupUserIdsSubquery(notebook_id, group_name)
    
#     selected_groups = request.args.get('selectedGroups', None)

#     if selected_groups:

#         selected_groups = json.loads(selected_groups)
#         group_userids_subquery = getGroupsUserIdsSubquery(notebook_id, selected_groups)

#         results = db.session.query(group_userids_subquery).all()

#         user_ids = [r[0] for r in results]
#     else : 
#         user_ids = []

#     return jsonify(user_ids), 200

# @groups_bp.route('testgroup', methods=['GET'])
# def test_group():

#     selected_groups = request.args.get('selectedGroups', None)

#     if selected_groups:
#         selected_groups = json.loads(selected_groups)

#         return jsonify(selected_groups)
#     else:
#         return jsonify('No groups')