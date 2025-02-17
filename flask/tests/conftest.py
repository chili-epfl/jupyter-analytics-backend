import pytest
from app.models.models import Event, CellExecution, ClickEvent, CellClickEvent, \
                                      NotebookClickEvent, CellAlteration, ClickType, AlterationType, Notebook
from app import create_app, db

# define all mock variables for reusability
notebook_id = 'notebook_x'
notebook_name = 'notebook.ipynb'
user_id = 'user_y'
cell_id = 'cell_z'
t_start = '2023-05-29T13:55:52.811566Z'
t_finish = '2023-05-29T13:55:55.055059Z'
status = 'ok'
cell_input = 'print("Hello, world!")'
cell_output_model = [
            {
                "name": "stdout",
                "text": "Hello, world!\n",
                "output_type": "stream"
            }
        ]
cell_output_length = 14
cell_content = 'This is a markdown cell'
language_mimetype = 'text/x-python'
alteration_type = AlterationType.ADD
click_type = ClickType.ON
click_duration = 2.034
s3_bucket_name = 's3_bucket'
s3_object_key = 'unianalytics/object.zip'

login_headers = {
    'Unianalytics-User-Id': user_id
}
auth_headers = {
    'Authorization': 'x'
}

# create a test app and create all tables
@pytest.fixture(scope='session')
def app():
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app

@pytest.fixture(scope='session')
def test_client(app):
    with app.test_client() as client:
        yield client

@pytest.fixture(scope='module')
def new_event():
    event = Event(notebook_id=notebook_id,
                  user_id=user_id, 
                  event_type='Event')
    return event

@pytest.fixture(scope='module')
def new_code_execution():
    code_execution = CellExecution(
        notebook_id=notebook_id,
        user_id=user_id,
        cell_id=cell_id,
        orig_cell_id=cell_id,
        cell_type='CodeExecution',
        language_mimetype=language_mimetype,
        t_start=t_start,
        t_finish=t_finish,
        status=status,
        cell_input=cell_input,
        cell_output_model=cell_output_model,
        cell_output_length=cell_output_length
    )
    return code_execution

@pytest.fixture(scope='module')
def new_markdown_execution():
    markdown_execution = CellExecution(
        notebook_id=notebook_id,
        user_id=user_id,
        cell_id=cell_id,
        orig_cell_id=cell_id,
        cell_type='MarkdownExecution',
        t_start=t_start,
        cell_input=cell_content
    )
    return markdown_execution

@pytest.fixture(scope='module')
def new_click_event():
    click_event = ClickEvent(
        notebook_id=notebook_id,
        user_id=user_id,
        time=t_start,
        click_type=click_type,
        click_duration=click_duration
    )
    return click_event

@pytest.fixture(scope='module')
def new_cell_click_event():
    cell_click_event = CellClickEvent(
        notebook_id=notebook_id,
        user_id=user_id,
        time=t_start,
        click_type=click_type,
        click_duration=click_duration,
        cell_id=cell_id,
        orig_cell_id=cell_id
    )
    return cell_click_event

@pytest.fixture(scope='module')
def new_notebook_click_event():
    notebook_click_event = NotebookClickEvent(
        notebook_id=notebook_id,
        user_id=user_id,
        time=t_start,
        click_type=click_type,
        click_duration=click_duration
    )
    return notebook_click_event

@pytest.fixture(scope='module')
def new_cell_alteration():
    cell_alteration = CellAlteration(
        notebook_id=notebook_id,
        user_id=user_id,
        cell_id=cell_id,
        alteration_type=alteration_type,
        time=t_start
    )
    return cell_alteration

@pytest.fixture(scope='module')
def new_notebook():
    notebook = Notebook(
        notebook_id=notebook_id,
        name=notebook_name,
        time=t_start,
        s3_bucket_name=s3_bucket_name,
        s3_object_key=s3_object_key
    )
    return notebook
