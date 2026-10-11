import requests
from fastapi import APIRouter, HTTPException

from pipeline import storage
from pipeline.config import GCP_BUCKET_NAME, GCP_PROJECT_ID
from pipeline.extract import licenses

router = APIRouter(prefix="/extract")

@router.post("/licenses")
def extract_licenses(max_rows: int = 1000):
    # Check bucket access before the ~90s extract, so missing access fails immediately.
    # Creating the client alone doesn't check permissions, so ask GCS directly.
    if not storage.can_write():
        raise HTTPException(status_code=500, detail=f"Current credentials cannot upload to bucket '{GCP_BUCKET_NAME}'")

    try:
        records = licenses.extract(max_rows)
    except requests.HTTPError as e:
        status = e.response.status_code
        print(f"Socrata returned {status}: {e}")
        raise HTTPException(status_code=500, detail=f"Socrata returned {status}")

    rows = [record.model_dump(mode="json") for record in records]
    blob_name = storage.write_raw("licenses", rows)

    return {"dataset": licenses.DATASET_ID, "rows": len(rows), "uploaded": blob_name}
