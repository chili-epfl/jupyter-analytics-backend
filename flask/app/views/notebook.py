from flask import Blueprint, request, jsonify, Response
import json
import datetime
from app import db
from app.models.models import Notebook
from io import BytesIO
import zipfile
import nbformat
from app.utils.storage import upload_file_to_volume, download_file_from_volume
from app.utils.constants import Selectors 
import uuid
import os
from flask_jwt_extended import jwt_required, current_user

notebook_bp = Blueprint('notebook', __name__)

@notebook_bp.route('/upload', methods=['POST'])
@jwt_required()
def postS3Notebook():
    if not current_user.is_superuser:
        return { 'error': 'The dashboard user does not have rights to upload notebooks' }, 401
    
    notebook_content_str = request.form['notebook_content']
    name = request.form['name']

    try:
        # upgrade the notebook if necessary (older versions might for example not have cell ids)
        nb = nbformat.reads(notebook_content_str, as_version=nbformat.NO_CONVERT)
        upgraded_nb = nbformat.v4.upgrade(nb)

        cell_mapping = []
        for c in upgraded_nb.cells : 
            cell_id = c.id
            if not cell_id : 
                return { 'error': 'The notebook is missing cell ids' }, 400
            else : 
                cell_mapping.append([cell_id, cell_id])

        upgraded_nb.metadata[Selectors["cellMapping"]] = cell_mapping
        if Selectors['notebookId'] in upgraded_nb.metadata :
            notebook_id = upgraded_nb.metadata[Selectors['notebookId']]
        else :  
            notebook_id = str(uuid.uuid4())
            upgraded_nb.metadata[Selectors["notebookId"]] = notebook_id

    except Exception as e:
        return { 'error': f"An error occurred while tagging the notebook : {str(e)}" }, 500

    try:
        # compress the notebook and name it with the 'name' value
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(name, json.dumps(upgraded_nb))  
        # move the buffer cursor to the beginning
        zip_buffer.seek(0)

        # in S3 the zip file will be named '.../{notebook_id}.zip'
        s3_object_key = os.environ.get('S3_PATH_NOTEBOOKS') + name.replace('.ipynb','') + '_' + notebook_id + '.zip'

        new_notebook = Notebook(
            name=name,
            notebook_id=notebook_id,
            s3_bucket_name=os.environ.get('S3_BUCKET_NAME'),
            s3_object_key=s3_object_key,
            time=datetime.datetime.now()
        )
        db.session.add(new_notebook)
        db.session.commit()

        # upload notebook file only if database insertion was successful
        upload_file_to_volume(os.environ.get('S3_BUCKET_NAME'), s3_object_key, zip_buffer)

        return jsonify(upgraded_nb)

    except Exception as e:
        db.session.rollback()
        return { 'error': f"An error occurred uploading the notebook to the server: {str(e)}"}, 500

@notebook_bp.route('/download/<notebook_id>', methods=['GET'])
def downloadS3NotebookById(notebook_id):

    notebook = Notebook.query.filter_by(notebook_id=notebook_id).first()

    if not notebook:
        return 'Notebook not found', 404   

    try:
        zip_file_content = download_file_from_volume(notebook.s3_bucket_name, notebook.s3_object_key)

        if zip_file_content is None:
            return 'Notebook file not found', 404

        # set the appropriate headers for the response
        headers = {
            'Content-Disposition': f"attachment; filename={notebook.name.replace('.ipynb','')}_{notebook_id}.zip",
            'Content-Type': 'application/zip'
        }

        # return the compressed zip file as a response with headers
        return Response(zip_file_content, headers=headers)

    except Exception as e:
        return f"An error occurred while retrieving the notebook: {str(e)}", 500
