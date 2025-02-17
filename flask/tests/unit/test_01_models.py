from conftest import (
    notebook_id, notebook_name, user_id, cell_id, t_start, t_finish, status, 
    cell_input, cell_output_model, cell_output_length, cell_content, language_mimetype, 
    alteration_type, click_type, s3_bucket_name, s3_object_key, click_duration
)

def test_new_event(new_event):
    """
    GIVEN an Event model
    WHEN a new Event is created
    THEN check all fields are defined correctly
    """
    assert new_event.notebook_id == notebook_id
    assert new_event.user_id == user_id
    assert new_event.event_type == 'Event'

def test_new_code_execution(new_code_execution):
    """
    GIVEN a CodeExecution
    WHEN a new CodeExecution is created
    THEN check all fields are defined correctly
    """
    assert new_code_execution.notebook_id == notebook_id
    assert new_code_execution.user_id == user_id
    assert new_code_execution.event_type == 'CellExecution'
    assert new_code_execution.cell_id == cell_id
    assert new_code_execution.orig_cell_id == cell_id
    assert new_code_execution.cell_type == 'CodeExecution'
    assert new_code_execution.language_mimetype == language_mimetype
    assert new_code_execution.t_start == t_start
    assert new_code_execution.t_finish == t_finish
    assert new_code_execution.status == status
    assert new_code_execution.cell_input == cell_input
    assert new_code_execution.cell_output_model == cell_output_model
    assert new_code_execution.cell_output_length == cell_output_length

def test_new_markdown_execution(new_markdown_execution):
    """
    GIVEN a MarkdownExecution 
    WHEN a new MarkdownExecution is created
    THEN check all fields are defined correctly
    """
    assert new_markdown_execution.notebook_id == notebook_id
    assert new_markdown_execution.user_id == user_id
    assert new_markdown_execution.event_type == 'CellExecution'
    assert new_markdown_execution.cell_id == cell_id
    assert new_markdown_execution.orig_cell_id == cell_id
    assert new_markdown_execution.cell_type == 'MarkdownExecution'
    assert new_markdown_execution.t_start == t_start
    assert new_markdown_execution.cell_input == cell_content

def test_new_click_event(new_click_event):
    """
    GIVEN a ClickEvent model
    WHEN a new ClickEvent is created
    THEN check all fields are defined correctly
    """
    assert new_click_event.notebook_id == notebook_id
    assert new_click_event.user_id == user_id
    assert new_click_event.event_type == 'ClickEvent'
    assert new_click_event.time == t_start
    assert new_click_event.click_type == click_type
    assert new_click_event.click_duration == click_duration

def test_new_cell_click_event(new_cell_click_event):
    """
    GIVEN a CellClickEvent model
    WHEN a new CellClickEvent is created
    THEN check all fields are defined correctly
    """
    assert new_cell_click_event.notebook_id == notebook_id
    assert new_cell_click_event.user_id == user_id
    assert new_cell_click_event.event_type == 'CellClickEvent'
    assert new_cell_click_event.time == t_start
    assert new_cell_click_event.click_type == click_type
    assert new_cell_click_event.click_duration == click_duration
    assert new_cell_click_event.cell_id == cell_id
    assert new_cell_click_event.orig_cell_id == cell_id

def test_new_notebook_click_event(new_notebook_click_event):
    """
    GIVEN a NotebookClickEvent model
    WHEN a new NotebookClickEvent is created
    THEN check all fields are defined correctly
    """
    assert new_notebook_click_event.notebook_id == notebook_id
    assert new_notebook_click_event.user_id == user_id
    assert new_notebook_click_event.event_type == 'NotebookClickEvent'
    assert new_notebook_click_event.time == t_start
    assert new_notebook_click_event.click_type == click_type
    assert new_notebook_click_event.click_duration == click_duration

def test_new_cell_alteration(new_cell_alteration):
    """
    GIVEN a CellAlteration model
    WHEN a new CellAlteration is created
    THEN check all fields are defined correctly
    """
    assert new_cell_alteration.notebook_id == notebook_id
    assert new_cell_alteration.user_id == user_id
    assert new_cell_alteration.event_type == 'CellAlteration'
    assert new_cell_alteration.cell_id == cell_id
    assert new_cell_alteration.alteration_type == alteration_type
    assert new_cell_alteration.time == t_start

def test_new_notebook(new_notebook):
    """
    GIVEN a Notebook model
    WHEN a new Notebook is created
    THEN check all fields are defined correctly
    """
    assert new_notebook.notebook_id == notebook_id
    assert new_notebook.name == notebook_name
    assert new_notebook.time == t_start
    assert new_notebook.s3_bucket_name == s3_bucket_name
    assert new_notebook.s3_object_key == s3_object_key

