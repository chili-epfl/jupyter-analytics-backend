from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app import db
from app.models.models import Event, CellExecution, ClickEvent, CellAlteration

event_bp = Blueprint('event', __name__)

# query all rows of the Event table
@event_bp.route('/all', methods=['GET'])
def getEvents() : 
    count = db.session.query(Event).count()
    return f"{count} entries in the table", 200

# Cell Execution Events

@event_bp.route('/execs', methods=['GET'])
def getExecs() : 
    count = db.session.query(CellExecution).count()
    return f"{count} entries in the table", 200

@event_bp.route('/execs/code', methods=['GET'])
def getCodeExecs() : 
    count = db.session.query(func.count()).filter(CellExecution.cell_type == 'CodeExecution').scalar()
    return f"{count} entries in the table", 200

@event_bp.route('/execs/markdown', methods=['GET'])
def getMarkdownExecs():
    count = db.session.query(func.count()).filter(CellExecution.cell_type == 'MarkdownExecution').scalar()
    return f"{count} entries in the table", 200

# Click Events

@event_bp.route('/clickevents', methods=['GET'])
def getClickEvents() : 
    count = db.session.query(ClickEvent).count()
    return f"{count} entries in the table", 200


# Cell Alteration Events

@event_bp.route('/alters', methods=['GET'])
def getAlterEvents() : 
    count = db.session.query(CellAlteration).count()
    return f"{count} entries in the table", 200