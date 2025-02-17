from flask import Flask
from flask_cors import CORS
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from datetime import timedelta
from flask_socketio import SocketIO
import redis

db = SQLAlchemy()

migrate = Migrate()

jwt = JWTManager()

socketio = SocketIO()

redis_client = redis.from_url(os.environ.get('REDIS_MESSAGE_QUEUE_URL'))

def create_app():

    app = Flask(__name__)
    
    cors = CORS(app, origins='*')
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg://{username}:{password}@{host}:{port}/{database}'.format(
        username=os.environ['RDS_USERNAME'],
        password=os.environ['RDS_PASSWORD'],
        host=os.environ['RDS_HOSTNAME'],
        port=os.environ['RDS_PORT'],
        database=os.environ['RDS_DB_NAME'],
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=30) # default: 15 mins
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30) # default: 30 days
    app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
    
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app,  cors_allowed_origins='*', message_queue=os.environ.get('REDIS_MESSAGE_QUEUE_URL'))

    # importing and registering routes with their url prefix
    from .views.main import main_bp
    from .views.event import event_bp
    from .views.send import send_bp
    from .views.dashboard import dashboard_bp
    from .views.notebook import notebook_bp
    from .views.delete import delete_bp
    from .views.jwt import jwt_bp
    from .views.groups import groups_bp
    from .views.dashboard_interaction import dashboard_interaction_bp
    
    app.register_blueprint(main_bp, url_prefix='/')
    app.register_blueprint(event_bp, url_prefix='/event')
    app.register_blueprint(send_bp, url_prefix='/send')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(notebook_bp, url_prefix='/notebook')
    app.register_blueprint(delete_bp, url_prefix='/delete')
    app.register_blueprint(jwt_bp, url_prefix='/jwt')
    app.register_blueprint(groups_bp, url_prefix='/groups')
    app.register_blueprint(dashboard_interaction_bp, url_prefix='/dashboard_interaction')
    
    jwt.init_app(app)

    return app