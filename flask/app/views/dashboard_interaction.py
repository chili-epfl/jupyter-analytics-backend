from flask import Blueprint, jsonify, request, Response, stream_with_context
import datetime
from app import db
from app.models.models import DashboardEvent
import csv
from io import StringIO
from flask_jwt_extended import jwt_required, current_user

dashboard_interaction_bp = Blueprint('dashboard_interaction', __name__)

@dashboard_interaction_bp.route('/add', methods=['POST'])
@jwt_required()
def add_dashboard_interaction():

    data = request.get_json()
    dashboard_user_id = current_user.username_hash

    try:
        new_dashboard_event = DashboardEvent(
            dashboard_user_id=dashboard_user_id,
            click_type=data['click_type'],
            signal_origin=data['signal_origin'],
            notebook_id=data.get('notebook_id', None),
            timestamp=datetime.datetime.strptime(data['time'],'%Y-%m-%dT%H:%M:%S.%f%z')
        )
        db.session.add(new_dashboard_event)
        db.session.commit()
        return jsonify('Dashboard Interaction OK')
    
    except Exception as e:
        db.session.rollback()
        return f'An error occurred: {str(e)}', 500

@dashboard_interaction_bp.route('/download_csv', methods=['GET'])
def download_TA_interactiondata_CSV():

    try:

        # parse query parameters
        t1_str = request.args.get('t1')
        t2_str = request.args.get('t2')

        # convert string to datetime object
        t1 = datetime.datetime.strptime(t1_str,'%Y-%m-%dT%H:%M:%S.%f%z')
        t2 = datetime.datetime.strptime(t2_str,'%Y-%m-%dT%H:%M:%S.%f%z')

        rows = db.session.query(DashboardEvent).filter(DashboardEvent.timestamp.between(t1, t2)).yield_per(2000)

        def generate():
            data = StringIO()
            w = csv.writer(data)

            columns = [
                'id', 'dashboard_user_id', 'click_type', 'signal_origin', 'notebook_id', 'time (UTC !)'
            ]

            # write header
            w.writerow(columns)
            yield data.getvalue()
            data.seek(0)
            data.truncate(0)

            # write each log item
            for row in rows:

                time_value = getattr(row, 'timestamp', None)

                w.writerow((
                    list(getattr(row, column, None) for column in columns[:-1]) + [time_value.isoformat() if time_value else None]
                ))
                yield data.getvalue()
                data.seek(0)
                data.truncate(0)
        
        # stream the response as the data is generated
        response = Response(stream_with_context(generate()), mimetype='text/csv')
        # add the filename
        response.headers.set("Content-Disposition", "attachment", filename=f"log_TA_interaction.csv")
        response.headers.set('Access-Control-Expose-Headers', 'Content-Disposition')
        
        return response

    except Exception as e:
        return f"An error occurred while downloading the data: {str(e)}", 500