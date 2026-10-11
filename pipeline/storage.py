import io
import json
from datetime import datetime, timezone

from google.cloud import storage
from google.oauth2 import service_account

from pipeline.config import GCP_BUCKET_NAME, GCP_PROJECT_ID, GCP_SERVICE_ACCOUNT_KEY

SOURCES = {"permits", "licenses", "websites"}

def get_bucket():
    if not GCP_SERVICE_ACCOUNT_KEY:
        client = storage.Client(project=GCP_PROJECT_ID)
    else:
        credentials = service_account.Credentials.from_service_account_file(GCP_SERVICE_ACCOUNT_KEY)
        client = storage.Client(project=GCP_PROJECT_ID,
                                credentials=credentials)
    bucket = client.bucket(GCP_BUCKET_NAME)
    return bucket

def upload_json_to_gcp(data, blob_name):
    bucket = get_bucket()
    bucket.blob(blob_name).upload_from_string(json.dumps(data), content_type="application/json")
    return blob_name

def can_write():
    '''
    Checks if user has permission to write to bucket
    '''
    bucket = get_bucket()
    if "storage.objects.create" not in bucket.test_iam_permissions(["storage.objects.create"]):
        return False
    return True

def raw_data_path(source, runtime=None):
    '''
    Returns the formatted file path's naming convention for raw data
    '''
    if source not in SOURCES:
        raise ValueError(f"{source} isn't a valid source. Choose from {SOURCES}")
    if runtime is None:
        runtime = datetime.now(timezone.utc)
    year = runtime.strftime("%Y")
    month = runtime.strftime("%m")
    day = runtime.strftime("%d")
    hour = runtime.strftime("%H")
    minute = runtime.strftime("%M")
    seconds = runtime.strftime("%S")
    file_path = f"raw/{source}/{year}_{month}_{day}_{hour}_{minute}_{seconds}Z.json"
    return file_path

def write_raw(source, data):
    '''
    Writes raw data to a GCP file
    '''
    file_path = raw_data_path(source)
    upload_json_to_gcp(data, file_path)
    return file_path