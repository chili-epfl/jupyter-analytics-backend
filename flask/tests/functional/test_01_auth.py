from conftest import notebook_id, user_id, login_headers, auth_headers

### NOT VALID ANYMORE AFTER CHANGING TO /jwt

# URL_prefix = '/auth'

# def test_whitelist_user(test_client):
#     """
#     GIVEN a Flask application
#     WHEN a POST request is made to '/auth/whitelistnotebooksforuser/<user_id>'
#     THEN check that the response is valid
#     """
#     payload = {
#         "notebook_ids": [notebook_id]
#     }

#     response = test_client.post(URL_prefix+'/whitelistnotebooksforuser/'+user_id, json=payload)
#     assert response.status_code == 200

#     response_get = test_client.get(URL_prefix+'/whitelistnotebooksforuser/'+user_id)
#     assert response_get.status_code == 405

# def test_login(test_client):
#     """
#     GIVEN a Flask application
#     WHEN a POST request is made to '/auth/login'
#     THEN check that the response is valid
#     """

#     response_token = test_client.post(URL_prefix+'/login', headers=login_headers)
#     assert response_token.status_code == 200

#     auth_headers['Authorization'] = f'Bearer {response_token.json["access_token"]}'

#     # empty headers
#     response_no_headers = test_client.post(URL_prefix+'/login', headers={})
#     assert response_no_headers.status_code == 401

#     response_get = test_client.get(URL_prefix+'/login', headers=login_headers)
#     assert response_get.status_code == 405
