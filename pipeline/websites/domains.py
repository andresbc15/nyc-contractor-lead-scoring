import json

from google.cloud import storage

from pipeline.config import GCP_BUCKET_NAME, GCP_PROJECT_ID

# app/routers/licenses.py uploads to raw/dob_licenses/<YYYY-MM-DD>/dob_licenses.json
LICENSES_PREFIX = "raw/dob_licenses/"
LICENSES_FILE = "dob_licenses.json"
TARGET_COLUMNS = ["license_type", "license_number", "license_status", "business_name", "business_email"]


# TO DO: move to pipeline/storage.py once it exists
def get_bucket():
    # No key file: uses Application Default Credentials (gcloud login locally)
    client = storage.Client(project=GCP_PROJECT_ID)
    return client.bucket(GCP_BUCKET_NAME)


def latest_licenses_file_name(bucket):
    file_names = [blob.name for blob in bucket.list_blobs(prefix=LICENSES_PREFIX) if blob.name.endswith(f"/{LICENSES_FILE}")]
    if not file_names:
        raise FileNotFoundError(f"No licenses files under gs://{GCP_BUCKET_NAME}/{LICENSES_PREFIX}")
    return max(file_names)


def load_latest_licenses():
    bucket = get_bucket()
    file_name = latest_licenses_file_name(bucket)
    data = bucket.blob(file_name).download_as_bytes()
    return file_name, json.loads(data)


def extract_licenses(data):
    extracted_data = list()
    for row in data:
        extracted_data.append({key: row[key] for key in TARGET_COLUMNS})
    return extracted_data
