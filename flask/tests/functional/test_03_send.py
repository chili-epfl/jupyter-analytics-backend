from conftest import notebook_id, user_id, cell_id, t_start, t_finish, status, cell_input, cell_output_model, cell_output_length, cell_content, language_mimetype, click_duration

URL_prefix = '/send'

def test_post_code_exec(test_client):
    """
    GIVEN a Flask application
    WHEN a POST request is made to '/send/exec/code'
    THEN check that the response is valid
    """

    payload = {
        "notebook_id": notebook_id,
        "user_id": user_id,
        "language_mimetype": language_mimetype,
        "cell_id": cell_id,
        "orig_cell_id": cell_id,
        "t_start": t_start,
        "t_finish": t_finish,
        "status": status,
        "cell_input": cell_input,
        "cell_output_model": cell_output_model,
        "cell_output_length": cell_output_length
    }

    response = test_client.post(URL_prefix+'/exec/code', json=payload)
    assert response.status_code == 200

    response_get = test_client.get(URL_prefix+'/exec/code')
    assert response_get.status_code == 405

def test_post_markdown_exec(test_client):
    """
    GIVEN a Flask application
    WHEN a POST request is made to '/send/exec/markdown'
    THEN check that the response is valid
    """
    payload = {
        "notebook_id": notebook_id,
        "user_id": user_id,
        "cell_id": cell_id,
        "orig_cell_id": cell_id,
        "time": t_start,
        "cell_content": cell_content
    }

    response = test_client.post(URL_prefix+'/exec/markdown', json=payload)
    assert response.status_code == 200

    response_get = test_client.get(URL_prefix+'/exec/markdown')
    assert response_get.status_code == 405

def test_post_cell_click_event(test_client):
    """
    GIVEN a Flask application
    WHEN a POST request is made to '/send/clickevent/cell'
    THEN check that the response is valid
    """
    payload = {
        "notebook_id": notebook_id,
        "user_id": user_id,
        "cell_id": cell_id,
        "orig_cell_id": cell_id,
        "time": t_start,
        "click_duration": click_duration,
        "click_type": 'ON'
    }

    response = test_client.post(URL_prefix+'/clickevent/cell', json=payload)
    assert response.status_code == 200

    response_get = test_client.get(URL_prefix+'/clickevent/cell')
    assert response_get.status_code == 405

def test_post_notebook_click_event(test_client):
    """
    GIVEN a Flask application
    WHEN a POST request is made to '/send/clickevent/notebook'
    THEN check that the response is valid
    """
    payload = {
        "notebook_id": notebook_id,
        "user_id": user_id,
        "time": t_start,
        "click_duration": click_duration,
        "click_type": 'ON'
    }

    response = test_client.post(URL_prefix+'/clickevent/notebook', json=payload)
    assert response.status_code == 200

    response_get = test_client.get(URL_prefix+'/clickevent/notebook')
    assert response_get.status_code == 405

def test_post_alter_event(test_client):
    """
    GIVEN a Flask application
    WHEN a POST request is made to '/send/alter'
    THEN check that the response is valid
    """
    payload = {
        "notebook_id": notebook_id,
        "user_id": user_id,
        "cell_id": cell_id,
        "alteration_type": 'REMOVE',
        "time": t_start
    }

    response = test_client.post(URL_prefix+'/alter', json=payload)
    assert response.status_code == 200

    response_get = test_client.get(URL_prefix+'/alter')
    assert response_get.status_code == 405


