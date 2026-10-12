import requests
from fastapi import APIRouter, HTTPException

from pipeline import storage
from pipeline.config import GCP_BUCKET_NAME
from pipeline.extract import licenses
from pipeline.websites import domains

router = APIRouter(prefix="/extract")

@router.post("/licenses")
def extract_licenses(max_rows: int = 1000):
    '''
    Extracts and uploads licenses and their target websites domains using a single endpoint
    '''
    # Check bucket access before the ~90s extract, so missing access fails immediately.
    if not storage.can_write():
        raise HTTPException(status_code=500, detail=f"Current credentials cannot upload to bucket '{GCP_BUCKET_NAME}'")

    try:
        records = licenses.extract(max_rows)
    except (requests.HTTPError, ValueError) as e:
        print(f"License extraction step failed: {e}")
        raise HTTPException(status_code=500, detail={"status" : "failed", "step": "extract", "error": f"{type(e).__name__}: {e}"})

    rows = [record.model_dump(mode="json") for record in records]
    blob_name = storage.write_data("licenses", rows)

    extract_summary =  {"dataset": licenses.DATASET_ID, "rows": len(rows), "uploaded": blob_name}

    try:
        license_domains = domains.run()
    except (Exception) as e:
        print(f"Domain step failed: {e}")
        raise HTTPException(status_code=500, detail={"status" : "partial", "step": "domains", "file_path": blob_name,"error": f"{type(e).__name__}: {e}"})

    return {"status" : "success", "extract_summary": extract_summary, "domains": license_domains}