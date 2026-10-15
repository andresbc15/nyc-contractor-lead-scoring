import requests
from fastapi import APIRouter, HTTPException

from pipeline import storage
from pipeline.config import GCP_BUCKET_NAME
from pipeline.extract import permits

router = APIRouter(prefix="/extract")


@router.post("/permits")
def extract_permits(since: str | None = None, backfill: bool = False):
    """
    Extracts and uploads construction permits in NYC to GCP using a single endpoint.
    Automatically backfills on a project with no files.

    - since: only pull permits updated after this date
    - backfill: pull every permit issued since 2025-01-01
    """
    if not storage.can_write():
        raise HTTPException(
            status_code=500,
            detail=f"Current credentials cannot upload to bucket '{GCP_BUCKET_NAME}'",
        )

    # If the project has no files, do a backfill
    if since is None and not backfill:
        try:
            storage.latest_file_name("permits")
        except FileNotFoundError:
            backfill = True

    try:
        records = permits.extract(since=since, backfill=backfill)
    except requests.HTTPError as e:
        status = e.response.status_code
        print(f"NYC Open Data returned {status}: {e}")
        raise HTTPException(status_code=500, detail=f"NYC Open Data returned {status}")
    if not records:
        return {"rows": 0, "backfill": backfill, "uploaded": None}
    rows = [record.model_dump(mode="json") for record in records]
    blob_name = storage.write_data("permits", rows)

    return {"rows": len(rows), "backfill": backfill, "uploaded": blob_name}
