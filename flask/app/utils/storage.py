import os
import boto3

# define the S3 client
s3_client = boto3.client('s3')

def upload_file_to_volume(bucket_name, object_key, file_content) :
    # this environment variable is only defined locally
    if os.environ.get('LOCAL_DEV') == 'true':
        # save to local S3 volume
        local_path = f'/app/S3/{bucket_name}/{object_key}'
        local_dir = os.path.dirname(local_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)
        with open(local_path, 'wb') as local_file:
            local_file.write(file_content.getvalue())   
    else:
        # upload to S3
        s3_client.upload_fileobj(file_content, bucket_name, object_key)

def download_file_from_volume(bucket_name, object_key):
    # this environment variable is only defined locally
    if os.environ.get('LOCAL_DEV') == 'true':
        local_path = f'/app/S3/{bucket_name}/{object_key}'
        try:
            with open(local_path, 'rb') as local_file:
                return local_file.read()
        except FileNotFoundError:
            return None
    else:
        
        try:
            s3_object = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            return s3_object['Body'].read()
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            else:
                raise e

