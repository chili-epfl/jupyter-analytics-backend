from conftest import notebook_id, auth_headers
import json

URL_prefix = '/notebook'

notebook_content = {
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 2,
   "id": "49805f03-bfd4-4b9c-ae96-77a822af6dd7",
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.10.11"
  },
  "unianalytics_notebook_id": notebook_id
 },
 "nbformat": 4,
 "nbformat_minor": 5
}

def test_upload_notebook(test_client):
    """
    GIVEN a Flask application
    WHEN a POST request is made to '/notebook/upload'
    THEN check that the response is valid
    """

    data = {
        'notebook_content': json.dumps(notebook_content),
        'name': notebook_id
    }

    # follow_redirects set to True to follow the redirect caused by authentication
    response = test_client.post(URL_prefix+'/upload', data=data, headers=auth_headers)
    print('\nRESPONSE NOTEBOOK : ',response.text,'\n')
    assert response.status_code == 200

    response_get = test_client.get(URL_prefix+'/upload')
    assert response_get.status_code == 405

