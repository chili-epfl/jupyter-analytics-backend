from flask import Blueprint, jsonify
import os

main_bp = Blueprint('main', __name__)

# '/' GET route for the AWS health check, which occurs every few seconds, so it must stay light
@main_bp.route('/', methods=['GET'])
def health_check():
    return 'OK', 200

@main_bp.route('/hostname')
def get_hostname():
    return jsonify({'hostname': os.uname().nodename})

