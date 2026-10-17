import requests
from fastapi import APIRouter, HTTPException

from pipeline import storage
from pipeline.config import GCP_BUCKET_NAME
from pipeline.extract import permits
from pipeline.transform import build

router = APIRouter(prefix="/extract")


@router.post("/permits")
def extract_permits(since: str | None = None, backfill: bool = False):
    """
    Extracts and uploads construction permits in NYC to GCP using a single endpoint.
    Automatically backfills on a project with no files.
    After new permits are uploaded, rebuilds the dashboard tables in processed/

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
    extract_summary = {"rows": len(rows), "backfill": backfill, "uploaded": blob_name}

    # Need to save on the memory on the backfill
    del records, rows

    # Build tables for the dashboard
    try:
        tables = build.run()
    except FileNotFoundError as e:
        # No licenses yet on a fresh project
        print(f"Skipping transform: {e}")
        return {
            "status": "success",
            "extract_summary": extract_summary,
            "transform": {"status": "skipped", "reason": str(e)},
        }
    except Exception as e:
        print(f"Transform step failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "partial",
                "step": "transform",
                "file_path": blob_name,
                "error": f"{type(e).__name__}: {e}",
            },
        )

    return {
        "status": "success",
        "extract_summary": extract_summary,
        "transform": {"status": "success", "uploaded": tables},
    }
