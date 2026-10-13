import requests
from fastapi import APIRouter, HTTPException

from pipeline import storage
from pipeline.config import GCP_BUCKET_NAME
from pipeline.extract import permits

router = APIRouter(prefix="/extract")


@router.post("/permits")
def extract_permits(since: str | None = None, backfill: bool = False):
    if not storage.can_write():
        raise HTTPException(status_code=500, detail=f"Current credentials cannot upload to bucket '{GCP_BUCKET_NAME}'")

    try:
        records = permits.extract(since=since, backfill=backfill)
    except requests.HTTPError as e:
        status = e.response.status_code
        print(f"NYC Open Data returned {status}: {e}")
        raise HTTPException(status_code=500, detail=f"NYC Open Data returned {status}")
    if not records:
        return {"rows": 0, "uploaded": None}
    rows = [record.model_dump(mode="json") for record in records]
    blob_name = storage.write_data("permits", rows)

    return {"rows": len(rows), "uploaded": blob_name}