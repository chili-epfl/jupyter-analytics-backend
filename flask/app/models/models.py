from app import db
import enum

# User interaction events


class Event(db.Model):

    __tablename__ = "Event"

    id = db.Column(db.Integer, primary_key=True)
    notebook_id = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.String(100), nullable=False)
    event_type = db.Column(db.String(32), nullable=False)
    __mapper_args__ = {"polymorphic_identity": "Event", "polymorphic_on": event_type}

    def __str__(self):
        return f"Event (id: {self.id}), type : {self.event_type}"


class CellExecution(Event):

    __tablename__ = "CellExecution"

    id = db.Column(
        db.Integer, db.ForeignKey("Event.id", ondelete="CASCADE"), primary_key=True
    )
    cell_id = db.Column(db.String(100), nullable=False)
    orig_cell_id = db.Column(
        db.String(100), nullable=False
    )  # can be null or undefined when not available in the metadata
    t_start = db.Column(db.DateTime, nullable=False)
    cell_input = db.Column(db.Text, nullable=False)
    cell_type = db.Column(db.String(32), nullable=False)

    # attributes specific to code cell executions (nullable) :
    language_mimetype = db.Column(db.String(50))
    t_finish = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # 'ok', 'error' or 'abort'
    cell_output_model = db.Column(db.PickleType)
    cell_output_length = db.Column(db.Integer)

    __mapper_args__ = {"polymorphic_identity": "CellExecution"}

    def __str__(self):
        return f"{self.cell_type} Event (id: {self.id}), {self.cell_type} cell : {self.cell_id}, notebook :  {self.notebook_id}"


class ClickType(enum.Enum):
    ON = "on-click"
    OFF = "off-click"


class ClickEvent(Event):

    __tablename__ = "ClickEvent"

    id = db.Column(
        db.Integer, db.ForeignKey("Event.id", ondelete="CASCADE"), primary_key=True
    )
    time = db.Column(db.DateTime, nullable=False)
    click_duration = db.Column(db.Float, nullable=True)
    click_type = db.Column(db.Enum(ClickType), nullable=False)

    __mapper_args__ = {"polymorphic_identity": "ClickEvent"}

    def __str__(self):
        return f"Click Event (id: {self.id}), type : {self.click_type}, notebook :  {self.notebook_id}"


class CellClickEvent(ClickEvent):

    __tablename__ = "CellClickEvent"

    id = db.Column(
        db.Integer, db.ForeignKey("ClickEvent.id", ondelete="CASCADE"), primary_key=True
    )
    cell_id = db.Column(db.String(100), nullable=False)
    orig_cell_id = db.Column(
        db.String(100), nullable=False
    )  # can be null or undefined when not available in the metadata

    __mapper_args__ = {"polymorphic_identity": "CellClickEvent"}

    def __str__(self):
        return f"Cell Click Event (id: {self.id}), cell_id : {self.cell_id}, type : {self.click_type}, notebook : {self.notebook_id}"


class NotebookClickEvent(ClickEvent):

    __tablename__ = "NotebookClickEvent"

    id = db.Column(
        db.Integer, db.ForeignKey("ClickEvent.id", ondelete="CASCADE"), primary_key=True
    )

    __mapper_args__ = {"polymorphic_identity": "NotebookClickEvent"}

    def __str__(self):
        return f"Notebook Click Event (id: {self.id}), type : {self.click_type}, notebook : {self.notebook_id}"


class AlterationType(enum.Enum):
    ADD = "added"
    REMOVE = "removed"


class CellAlteration(Event):

    __tablename__ = "CellAlteration"

    id = db.Column(
        db.Integer, db.ForeignKey("Event.id", ondelete="CASCADE"), primary_key=True
    )
    cell_id = db.Column(db.String(100), nullable=False)
    alteration_type = db.Column(db.Enum(AlterationType), nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    __mapper_args__ = {"polymorphic_identity": "CellAlteration"}

    def __str__(self):
        return f"Cell Alteration Event (id: {self.id}), [{self.alteration_type}], cell : {self.cell_id}, notebook :  {self.notebook_id}"


# Notebook registration


class Notebook(db.Model):

    __tablename__ = "Notebook"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(400), nullable=False)
    notebook_id = db.Column(db.String(100), nullable=False, unique=True, index=True)
    s3_bucket_name = db.Column(db.String(300), nullable=False)
    s3_object_key = db.Column(db.String(500), nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    def __str__(self):
        return f"Notebook {self.name}, id : {self.notebook_id}"


class ConnectionType(enum.Enum):
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"


# Cache


class RefreshDashboardCache(db.Model):
    __tablename__ = "RefreshDashboardCache"

    notebook_id = db.Column(db.String(60), primary_key=True)
    last_refresh_time = db.Column(db.DateTime, nullable=False)

    def __str__(self):
        return f"{self.notebook_id}, on {self.last_refresh_time}"


# Dashboard interaction collection
class DashboardEvent(db.Model):

    __tablename__ = "DashboardEvent"

    id = db.Column(db.Integer, primary_key=True)
    dashboard_user_id = db.Column(db.String(100), nullable=False)
    click_type = db.Column(
        db.Enum(ClickType), nullable=False
    )  # ON or OFF (if it does not make sense, select ON)
    signal_origin = db.Column(db.String(90), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False)
    notebook_id = db.Column(
        db.String(60), nullable=True
    )  # null if not associated with a notebook_id

    def __str__(self):
        return f"User ({self.dashboard_user_id}): '{self.signal_origin}', {self.click_type}, nb_id: {self.notebook_id}"


UserGroupAssociation = db.Table(
    "UserGroupAssociation",
    db.Column("group_pk", db.String(100), db.ForeignKey("UserGroups.group_pk")),
    db.Column("user_id", db.String(100), db.ForeignKey("Users.user_id")),
)


class UserGroups(db.Model):

    __tablename__ = "UserGroups"

    group_pk = db.Column(
        db.String(401), primary_key=True
    )  # combining group_name and notebook_id
    group_name = db.Column(db.String(300), nullable=False)
    notebook_id = db.Column(db.String(100), nullable=False)
    group_users = db.relationship("Users", secondary=UserGroupAssociation)

    def __init__(self, group_name, notebook_id):
        self.group_pk = f"{group_name}-{notebook_id}"
        self.group_name = group_name
        self.notebook_id = notebook_id

    def __str__(self):
        return f"UserGroup entry (group_name, notebook_id): ({self.group_name}, {self.notebook_id})"


class TeammateLocation(db.Model):
    """Stores the current cell location of users for teammate tracking."""

    __tablename__ = "TeammateLocation"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)  # hashed user id
    notebook_id = db.Column(db.String(100), nullable=False, index=True)
    cell_id = db.Column(db.String(100), nullable=False)
    cell_index = db.Column(db.Integer, nullable=True)  # cell position
    updated_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "notebook_id", name="unique_user_notebook_location"
        ),
    )

    def __str__(self):
        return f"TeammateLocation({self.user_id}, {self.notebook_id}, {self.cell_id})"


class Users(db.Model):

    __tablename__ = "Users"

    user_id = db.Column(db.String(100), primary_key=True)

    def __init__(self, user_id):
        self.user_id = user_id

    def __str__(self):
        return f"User {self.user_id}"


class PendingUpdateAction(enum.Enum):
    UPDATE_NOW = "update_now"
    UPDATE_LATER = "update_later"
    UPDATE_ALL = "update_all"
    DELETE_ALL = "delete_all"
    APPLY_SINGLE = "apply_single"
    REMOVE_SINGLE = "remove_single"
    OVERRIDE = "override" 


class PendingUpdateInteraction(db.Model):
    """Logs student interactions with pending updates."""

    __tablename__ = "PendingUpdateInteraction"

    id = db.Column(db.Integer, primary_key=True)
    notebook_id = db.Column(db.String(100), nullable=False, index=True)
    user_id = db.Column(db.String(100), nullable=False, index=True)  
    cell_id = db.Column(
        db.String(100), nullable=True
    )  # null for notebook-level actions
    update_id = db.Column(db.String(100), nullable=True)  # New column
    action = db.Column(db.Enum(PendingUpdateAction), nullable=False)
    sender = db.Column(db.String(100), nullable=True)  # hashed user id of sender
    sender_type = db.Column(db.String(20), nullable=True)  # 'teacher' or 'teammate'
    timestamp = db.Column(db.DateTime, nullable=False)

    def __str__(self):
        return f"PendingUpdateInteraction({self.user_id}, {self.action}, {self.notebook_id})"
