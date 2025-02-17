from flask import Blueprint, request, jsonify
from app import db
from app.models.models import Notebook, Event
import os

delete_bp = Blueprint('delete', __name__)

# routes in this blueprint can be temporarily uncommented and the value of the DELETE_TOKEN changed to perform some delete requests
# the blueprint denies all request that don't have the X-Token header equals to DELETE_TOKEN

DELETE_TOKEN = 'CHANGE_VALUE_HERE_BEFORE_DEPLOYING'

# check the token
def payload_check_middleware():

    # if request.method == 'OPTIONS':
    #     return jsonify('OK'), 200  # respond to OPTIONS preflight request with a 200 status

    received_token = request.headers.get('X-Token', None)

    if received_token:
        try :

            if received_token != DELETE_TOKEN :
                return jsonify('Invalid authorization'), 401

        except Exception as e :
            return jsonify('Unauthorized'), 401
        
    else:
        return jsonify('Unauthorized'), 401

    return

# apply the check before every /send request
delete_bp.before_request(payload_check_middleware)

# @delete_bp.route('/events/<notebook_id>', methods=['DELETE'])
# def delete_events(notebook_id):

#     try:
#         # perform the delete operation
#         deleted_count = Event.query.filter_by(notebook_id=notebook_id).delete()
#         db.session.commit()

#         if deleted_count == 0 : 
#             return f"No entries found for notebook_id: {notebook_id}", 404
#         else : 
#             return f"Successfully deleted {deleted_count} entries with notebook_id: {notebook_id}", 200
#     except Exception as e:
#         db.session.rollback()
#         return f"An error occurred: {str(e)}", 500
    
# @delete_bp.route('/notebook/<notebook_id>', methods=['DELETE'])
# def delete_notebook(notebook_id):

#     try:
#         # perform the delete operation
#         deleted_count = Notebook.query.filter_by(notebook_id=notebook_id).delete()
#         db.session.commit()

#         if deleted_count == 0 : 
#             return f"No entries found for notebook_id: {notebook_id}", 404
#         else : 
#             return f"Successfully deleted entries with notebook_id: {notebook_id}", 200
#     except Exception as e:
#         db.session.rollback()
#         return f"An error occurred: {str(e)}", 500
    
# @delete_bp.route('/all_events_and_notebooks', methods=['DELETE'])
# def clear_all_events_and_notebooks():
    
#     try:
#         # clear the Event table (with cascading deletes)
#         Event.query.delete()
#         # clear the Notebook table
#         Notebook.query.delete()
#         db.session.commit()
        
#         return 'Cleared notebooks and events successfully', 200
#     except Exception as e:
#         db.session.rollback()
#         return f"An error occurred: {str(e)}", 500

# @delete_bp.route('/reset_database', methods=['DELETE'])
# def reset_database():

#     try:
#         # drop all tables
#         db.drop_all()
#         # create the tables again
#         db.create_all()
#         return 'Database reset successfully', 200
#     except Exception as e:
#         db.session.rollback()
#         return f"An error occurred clearing the database: {str(e)}", 500