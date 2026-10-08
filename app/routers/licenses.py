import json
from datetime import date

import requests
from fastapi import APIRouter, HTTPException
from google.cloud import storage

from pipeline.config import GCP_BUCKET_NAME, GCP_PROJECT_ID
from pipeline.extract import licenses

router = APIRouter(prefix="/extract")


# TEMPORARY: move to pipeline/storage.py once it exists
def get_bucket():
    client = storage.Client(project=GCP_PROJECT_ID)
    return client.bucket(GCP_BUCKET_NAME)


# TEMPORARY: move to pipeline/storage.py once it exists
def upload_json_to_gcp(bucket, data, blob_name):
    bucket.blob(blob_name).upload_from_string(json.dumps(data), content_type="application/json")
    return blob_name


@router.post("/licenses")
def extract_licenses(max_rows: int = 1000):
    # Check bucket access before the ~90s extract, so missing access fails immediately.
    # Creating the client alone doesn't check permissions, so ask GCS directly.
    bucket = get_bucket()
    if "storage.objects.create" not in bucket.test_iam_permissions(["storage.objects.create"]):
        raise HTTPException(status_code=500, detail=f"Current credentials cannot upload to bucket '{GCP_BUCKET_NAME}'")

    try:
        records = licenses.extract(max_rows)
    except requests.HTTPError as e:
        status = e.response.status_code
        print(f"Socrata returned {status}: {e}")
        raise HTTPException(status_code=500, detail=f"Socrata returned {status}")

    # TEMPORARY: serializing to JSON belongs in pipeline/storage.py's write function, not the router
    rows = [record.model_dump(mode="json") for record in records]
    blob_name = f"raw/dob_licenses/dt={date.today().isoformat()}/dob_licenses.json"
    upload_json_to_gcp(bucket, rows, blob_name)

    return {"dataset": licenses.DATASET_ID, "rows": len(rows), "uploaded": blob_name}
