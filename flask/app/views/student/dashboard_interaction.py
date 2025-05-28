from flask import Blueprint, jsonify, request
import datetime
from app import db
from app.models.models import DashboardEvent
from app.utils.utils import hash_user_id_with_salt

dashboard_interaction_bp = Blueprint('student_dashboard_interaction', __name__)

@dashboard_interaction_bp.route('/add', methods=['POST'])
def add_dashboard_interaction():

    user_id = request.args.get('user_id')
    if not user_id:
        return None, jsonify({"error": "User ID is required"}), 400
    user_id = hash_user_id_with_salt(user_id), 

    data = request.get_json()
    try:
        new_dashboard_event = DashboardEvent(
            dashboard_user_id=user_id,
            click_type=data['click_type'],
            signal_origin=data['signal_origin'],
            notebook_id=data.get('notebook_id', None),
            timestamp=datetime.datetime.strptime(data['time'],'%Y-%m-%dT%H:%M:%S.%f%z'),
            dashboard_type='STUDENT'
        )
        db.session.add(new_dashboard_event)
        db.session.commit()
        return jsonify('Dashboard Interaction OK')
    
    except Exception as e:
        db.session.rollback()
        return f'An error occurred: {str(e)}', 500
