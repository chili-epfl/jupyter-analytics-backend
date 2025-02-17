from gevent import monkey
monkey.patch_all()

from flask import Flask
from app import create_app, db

if __name__ == "__main__":
    application = create_app()
    with application.app_context():
        db.create_all()