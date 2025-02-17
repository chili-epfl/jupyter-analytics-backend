from gevent import monkey
monkey.patch_all()

from flask import Flask
from app import create_app, socketio

application = create_app()

if __name__ == "__main__":
    socketio.run(application, debug=True, host='0.0.0.0')