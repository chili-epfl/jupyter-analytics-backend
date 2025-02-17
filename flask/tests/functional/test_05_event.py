URL_prefix = '/event'

def test_get_all_events(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the URL_prefix+'/all' page is requested (GET)
    THEN check that the response is valid
    """
    response_get = test_client.get(URL_prefix+'/all')
    assert response_get.status_code == 200

    response_post = test_client.post(URL_prefix+'/all')
    assert response_post.status_code == 405


def test_get_list_execs(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the URL_prefix+'/execs' page is requested (GET)
    THEN check that the response is valid
    """
    response_get = test_client.get(URL_prefix+'/execs')
    assert response_get.status_code == 200

    response_post = test_client.post(URL_prefix+'/execs')
    assert response_post.status_code == 405

def test_get_list_code_execs(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the URL_prefix+'/execs/code' page is requested (GET)
    THEN check that the response is valid
    """
    response_get = test_client.get(URL_prefix+'/execs/code')
    assert response_get.status_code == 200

    response_post = test_client.post(URL_prefix+'/execs/code')
    assert response_post.status_code == 405

def test_get_list_markdown_execs(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the URL_prefix+'/execs/markdown' page is requested (GET)
    THEN check that the response is valid
    """
    response_get = test_client.get(URL_prefix+'/execs/markdown')
    assert response_get.status_code == 200

    response_post = test_client.post(URL_prefix+'/execs/markdown')
    assert response_post.status_code == 405

def test_get_list_click_events(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the URL_prefix+'/clickevents' page is requested (GET)
    THEN check that the response is valid
    """
    response_get = test_client.get(URL_prefix+'/clickevents')
    assert response_get.status_code == 200

    response_post = test_client.post(URL_prefix+'/clickevents')
    assert response_post.status_code == 405

def test_get_list_alter_events(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the URL_prefix+'/alters' page is requested (GET)
    THEN check that the response is valid
    """
    response_get = test_client.get(URL_prefix+'/alters')
    assert response_get.status_code == 200

    response_post = test_client.post(URL_prefix+'/alters')
    assert response_post.status_code == 405