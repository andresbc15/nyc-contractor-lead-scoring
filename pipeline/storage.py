import io
import json
from datetime import datetime, timezone

from google.cloud import storage
from google.oauth2 import service_account

from pipeline.config import GCP_BUCKET_NAME, GCP_PROJECT_ID, GCP_SERVICE_ACCOUNT_KEY

SOURCES = {"permits", "licenses", "websites"}
STAGES = {"raw", "intermediate", "processed"}

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

def get_data_path(source, stage="raw", runtime=None):
    '''
    Returns the formatted file path's naming convention for a specified data type
    '''
    if stage == "raw" and source not in SOURCES:
        raise ValueError(f"{source} isn't a valid source. Choose from {SOURCES}")
    if stage not in STAGES:
        raise ValueError(f"{stage} isn't a valid data stage. Choose from {STAGES}")
    if runtime is None:
        runtime = datetime.now(timezone.utc)

    year = runtime.strftime("%Y")
    month = runtime.strftime("%m")
    day = runtime.strftime("%d")
    hour = runtime.strftime("%H")
    minute = runtime.strftime("%M")
    seconds = runtime.strftime("%S")

    file_path = f"{stage}/{source}/{year}_{month}_{day}_{hour}_{minute}_{seconds}Z.json"
    return file_path

def write_data(source, data, stage="raw"):
    '''
    Writes data to a GCP file
    '''
    file_path = get_data_path(source, stage)
    upload_json_to_gcp(data, file_path)
    return file_path

def read_data(file_path):
    '''
    Reads data from a GCP file
    '''
    bucket = get_bucket()
    data = bucket.blob(file_path).download_as_bytes()
    return json.loads(data)

def latest_file_name(source, stage="raw"):
    '''
    returns the file path of the newest file inside {stage}/{source}/
    '''
    bucket = get_bucket()

    file_names = [
        blob.name
        for blob in bucket.list_blobs(prefix=f"{stage}/{source}/")
        if blob.name.endswith("Z.json")
    ]
    if not file_names:
        raise FileNotFoundError(
            f"No files found in {GCP_BUCKET_NAME}/{stage}/{source}"
        )
    return max(file_names)

def read_latest_file(source, stage="raw"):
    '''
    Reads the data and file path of the newest data in a specified source and stage folder
    '''
    file_name = latest_file_name(source, stage)
    data = read_data(file_name)
    # Return tuple for logging purposes
    return file_name, data
