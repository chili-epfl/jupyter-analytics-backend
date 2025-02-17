from app import db, jwt
from flask import Flask, jsonify
import enum
from werkzeug.security import generate_password_hash, check_password_hash

class UserIdType(enum.Enum):
    SCIPER = "sciper"
    UUID = "uuid"

# defining a many-to-many relationship between whitelisted users and notebooks
WhiteListAssociation = db.Table(
    'WhiteListAssociation',
    db.Column('user_id', db.String(100), db.ForeignKey('UserWhiteList.user_id')),
    db.Column('notebook_id', db.String(60), db.ForeignKey('NotebookWhiteList.notebook_id')),
    db.UniqueConstraint('user_id', 'notebook_id')
)

# class used to authenticate users
class UserWhiteList(db.Model):

    __tablename__ = 'UserWhiteList'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, unique=True)
    user_id_type = db.Column(db.Enum(UserIdType), nullable=False, default=UserIdType.UUID)
    authorized_notebooks = db.relationship('NotebookWhiteList', secondary=WhiteListAssociation, back_populates='authorized_users')

class NotebookWhiteList(db.Model):

    __tablename__ = 'NotebookWhiteList'

    id = db.Column(db.Integer, primary_key=True)
    notebook_id = db.Column(db.String(60), nullable=False, unique=True)
    authorized_users = db.relationship('UserWhiteList', secondary=WhiteListAssociation, back_populates='authorized_notebooks')

# defining a many-to-many relationship between auth users and notebooks
AuthAssociation = db.Table(
    'AuthAssociation',
    db.Column('username_hash', db.String(200), db.ForeignKey('AuthUsers.username_hash')),
    db.Column('notebook_id', db.String(100), db.ForeignKey('AuthNotebooks.notebook_id')),
    db.UniqueConstraint('username_hash', 'notebook_id')
)

# class used to register users
class AuthUsers(db.Model):

    __tablename__ = 'AuthUsers'

    id = db.Column(db.Integer, primary_key=True)
    username_hash = db.Column(db.String(200), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    authorized_notebooks = db.relationship('AuthNotebooks', secondary=AuthAssociation, back_populates='authorized_users')
    is_superuser = db.Column(db.Boolean, default=False, nullable=False) 
    is_admin = db.Column(db.Boolean, default=False, nullable=False) # is_admin > is_superuser

    # is_admin and is_superuser left False upon initialization
    def __init__(self, username_hash, password):
        self.username_hash = username_hash
        if password: self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AuthNotebooks(db.Model):

    __tablename__ = 'AuthNotebooks'

    id = db.Column(db.Integer, primary_key=True)
    notebook_id = db.Column(db.String(100), nullable=False, unique=True)
    authorized_users = db.relationship('AuthUsers', secondary=AuthAssociation, back_populates='authorized_notebooks')

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    # check if the identity exists in AuthUsers
    return AuthUsers.query.filter_by(id=identity).one_or_none()

# change the default response message when an expired token is used
@jwt.expired_token_loader
def my_expired_token_callback(jwt_header, jwt_payload):
    return jsonify({ 'status': 'expired_token' }), 401

