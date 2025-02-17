from flask import Blueprint, request, jsonify, render_template
from app import db
from app.models.auth import AuthUsers, AuthNotebooks
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity, current_user
from app.utils.utils import hash_user_id_with_salt

jwt_bp = Blueprint('jwt', __name__)

# route to check access token validity which means the user is logged in
@jwt_bp.route('/check', methods=['GET'])
@jwt_required()
def check_access():
    return jsonify({ 'auth_notebooks': [n.notebook_id for n in current_user.authorized_notebooks] }), 200

# route to get a refresh and an access token
@jwt_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # validate input data
        if not username:
            return jsonify({'error': 'Username is missing'}), 400
        if not password:
            return jsonify({'error': 'Password is missing'}), 400

        username_hash = hash_user_id_with_salt(username)
        user = AuthUsers.query.filter_by(username_hash=username_hash).first()
        if user:
            password_match = user.check_password(password)
            if password_match:
                access_token = create_access_token(identity=user.id)
                refresh_token = create_refresh_token(identity=user.id)
                return jsonify({ 'access_token': access_token, 'refresh_token': refresh_token, 'auth_notebooks': [n.notebook_id for n in user.authorized_notebooks] }), 200
        
        return jsonify({'error': 'Invalid username or password'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@jwt_bp.route('/signup', methods=['GET'])
def render_signup_page():
    return render_template('signup.html')

@jwt_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        # validate input data
        if not username:
            return jsonify({'error': 'Username is missing'}), 400
        if not password:
            return jsonify({'error': 'Password is missing'}), 400

        username_hash = hash_user_id_with_salt(username)

        # check if the username already exists in AuthUsers
        existing_user = AuthUsers.query.filter_by(username_hash=username_hash).first()
        if existing_user:
            return jsonify({'error': 'User already exists'}), 400

        # create a new user and add it to the AuthUsers table
        new_user = AuthUsers(username_hash=username_hash, password=password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': f'User {username} created successfully'}), 201
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# route to request a new access token with a refresh token
@jwt_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({ 'access_token': access_token })

@jwt_bp.route('/enable_notebooks_for_user/<username>', methods=['POST'])
@jwt_required()
def enable_notebooks_for_user(username):
    try:
        if not current_user.is_superuser:
            return jsonify({'error': 'Only superusers can enable notebooks'}), 403

        username_hash = hash_user_id_with_salt(username)
        notebook_ids = request.get_json().get('notebook_ids', [])

        # check if the user exists in AuthUsers
        user = AuthUsers.query.filter_by(username_hash=username_hash).first()
        if not user:
            return jsonify({'error': f'User {username} not registered'}), 404

        # authorize notebooks for the given user
        for notebook_id in notebook_ids:
            # check if the notebook exists in AuthNotebooks, create it if not
            notebook = AuthNotebooks.query.filter_by(notebook_id=notebook_id).first()
            if not notebook:
                notebook = AuthNotebooks(notebook_id=notebook_id)
                db.session.add(notebook)

            # check if the notebook is already authorized for the user, authorize if not
            if notebook not in user.authorized_notebooks:
                user.authorized_notebooks.append(notebook)

        db.session.commit()
        return jsonify({'message': f"{len(notebook_ids)} notebook(s) authorized for user {username}"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    
@jwt_bp.route('/disable_notebooks_for_user/<username>', methods=['DELETE'])
@jwt_required()
def disable_notebooks_for_user(username):
    try:
        if not current_user.is_superuser:
            return jsonify({'error': 'Only superusers can disable notebooks'}), 403
        
        username_hash = hash_user_id_with_salt(username)
        notebook_ids = request.get_json().get('notebook_ids', [])

        # check if the user exists in AuthUsers
        user = AuthUsers.query.filter_by(username_hash=username_hash).first()
        if not user:
            return jsonify({'error': f'User {username} not registered'}), 404

        # deauthorize notebooks for the given user
        for notebook_id in notebook_ids:
            notebook = AuthNotebooks.query.filter_by(notebook_id=notebook_id).first()
            if notebook and notebook in user.authorized_notebooks:
                user.authorized_notebooks.remove(notebook)

        db.session.commit()
        return jsonify({'message': f"{len(notebook_ids)} notebook(s) deauthorized for user {username}"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500


@jwt_bp.route('/enable_users_for_notebook/<notebook_id>', methods=['POST'])
@jwt_required()
def enable_users_for_notebook(notebook_id):
    try:
        if not current_user.is_superuser:
            return jsonify({'error': 'Only superusers can enable users'}), 403
        
        usernames = request.get_json().get('usernames', [])

        # check if the notebook_id exists in AuthNotebooks, add if not
        notebook = AuthNotebooks.query.filter_by(notebook_id=notebook_id).first()
        if not notebook:
            notebook = AuthNotebooks(notebook_id=notebook_id)
            db.session.add(notebook)

        # whitelist users for the given notebook
        for username in usernames:
            username_hash = hash_user_id_with_salt(username)
            # check if the user exists in AuthUsers
            user = AuthUsers.query.filter_by(username_hash=username_hash).first()

            if not user:
                return jsonify({'error': f'User {username} not registered'}), 404
            
            # check if the user is already authorized for the notebook, authorize if not
            if user and user not in notebook.authorized_users:
                notebook.authorized_users.append(user)
        
        db.session.commit()
        return jsonify({'message': f"{notebook_id} notebook authorized for {len(usernames)} user(s)"}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@jwt_bp.route('/disable_users_for_notebook/<notebook_id>', methods=['DELETE'])
@jwt_required()
def disable_users_for_notebook(notebook_id):
    try:
        if not current_user.is_superuser:
            return jsonify({'error': 'Only superusers can disable users'}), 403

        usernames = request.get_json().get('usernames', [])

        # check if the notebook exists in AuthNotebooks
        notebook = AuthNotebooks.query.filter_by(notebook_id=notebook_id).first()
        if not notebook:
            return jsonify({'error': f'Notebook {notebook_id} not found'}), 404

        # deauthorize users for the given notebook
        for username in usernames:
            username_hash = hash_user_id_with_salt(username)
            user = AuthUsers.query.filter_by(username_hash=username_hash).first()
            if user and user in notebook.authorized_users:
                notebook.authorized_users.remove(user)

        db.session.commit()
        return jsonify({'message': f"{notebook_id} notebook deauthorized for {len(usernames)} user(s)"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@jwt_bp.route('/enable_superuser', methods=['POST'])
@jwt_required()
def enable_superuser():
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Only admins can enable superusers'}), 403

        usernames = request.json.get('usernames', [])

        # iterate through the list of usernames and enable superuser status for each user
        for username in usernames:
            user = AuthUsers.query.filter_by(username_hash=hash_user_id_with_salt(username)).first()
            if not user:
                return jsonify({'error': f'User {username} not registered'}), 404
            user.is_superuser = True
            db.session.commit()

        return jsonify({'message': f"Superuser status enabled for {len(usernames)} user(s)"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    
@jwt_bp.route('/disable_superuser', methods=['DELETE'])
@jwt_required()
def disable_superuser():
    try:
        if not current_user.is_admin:
            return jsonify({'error': 'Only admins can disable superusers'}), 403

        usernames = request.json.get('usernames', [])

        # iterate through the list of usernames and disable superuser status for each user
        for username in usernames:
            user = AuthUsers.query.filter_by(username_hash=hash_user_id_with_salt(username)).first()
            if not user:
                return jsonify({'error': f'User {username} not registered'}), 404
            user.is_superuser = False
            db.session.commit()

        return jsonify({'message': f"Superuser status disabled for {len(usernames)} user(s)"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

