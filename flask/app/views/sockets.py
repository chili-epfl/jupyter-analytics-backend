from flask_socketio import send, join_room, leave_room, ConnectionRefusedError, emit
from app import socketio, redis_client
from app.models.models import ConnectionType, Notebook
from flask import request, session
from app.utils.utils import hash_user_id_with_salt

@socketio.on('connect')
def handle_connect():
    try:
        con_type = ConnectionType(request.args.get('conType')) 
    except ValueError as e:
        raise ConnectionRefusedError('Invalid connection type')
    
    user_id = request.args.get('userId')
    if user_id : user_id = hash_user_id_with_salt(user_id)
    
    notebook_id = request.args.get('nbId')

    if (not user_id) or (not notebook_id):
        # no required identifiers
        raise ConnectionRefusedError('Missing required identifiers')

    # check that the notebook is registered
    notebook = Notebook.query.filter_by(notebook_id=notebook_id).first()
    if not notebook:
        # notebook not registered
        raise ConnectionRefusedError('Notebook not registered')

    # add to the appropriate list of connected users in the redis cache
    redis_client.sadd(f'connected_{con_type.name.lower()}s:{notebook_id}', user_id)
    # add to the all-students or all-teachers room
    room_name = con_type.name.lower() + "_" + notebook_id
    join_room(room_name)
    # add to a room specific to that user_id
    personal_user_room_name = con_type.name.lower() + '_' + user_id + '_' + notebook_id
    join_room(personal_user_room_name)

    session['con_type'] = con_type.name
    session['user_id'] = user_id
    session['notebook_id'] = notebook_id
    
@socketio.on('disconnect')
def handle_disconnect():
    try:
        con_type = ConnectionType(request.args.get('conType')) 
    except ValueError as e:
        raise ConnectionRefusedError('Invalid connection type')
    
    user_id = request.args.get('userId')
    if user_id : user_id = hash_user_id_with_salt(user_id)

    notebook_id = request.args.get('nbId')

    if user_id:
        # remove from the list of connected users
        redis_client.srem(f'connected_{con_type.name.lower()}s:{notebook_id}', user_id)
    # remove from the rooms
    room_name = con_type.name.lower() + "_" + notebook_id
    leave_room(room_name)

    personal_user_room_name = con_type.name.lower() + '_' + user_id + '_' + notebook_id
    leave_room(personal_user_room_name)

    if session.get('con_type', None): del session['con_type'] 
    if session.get('user_id', None): del session['user_id'] 
    if session.get('notebook_id', None): del session['notebook_id'] 

@socketio.on('sendmessage')
def handle_sendmessage(message):
    print('\nReceived message:', message, '\nSession : ',session, '\n')
    send('response')    

@socketio.on('send_message')
def handle_send_message(data):
    target_user_id = data['userId']
    message = data['message']
    # send message to the target user
    if session.get('con_type', None) == ConnectionType.STUDENT.name: 
        target_con_type = ConnectionType.TEACHER.name
    elif session.get('con_type', None) == ConnectionType.TEACHER.name: 
        target_con_type = ConnectionType.STUDENT.name
    else:
        target_con_type = None
    
    if target_user_id and message and target_con_type and session.get('notebook_id', None) and session.get('user_id', None):
        target_user_room_name = target_con_type.lower() + "_" + target_user_id + "_" + session['notebook_id']
        emit('chat', f"From {session['user_id']}: {message}", to=target_user_room_name)
