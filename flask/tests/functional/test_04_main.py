def test_get(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response_get = test_client.get('/')
    assert response_get.status_code == 200

    response_post = test_client.post('/')
    assert response_post.status_code == 405
