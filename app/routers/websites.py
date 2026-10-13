from fastapi import APIRouter, HTTPException

from pipeline import storage
from pipeline.config import GCP_BUCKET_NAME
from pipeline.websites import scrape, signals

router = APIRouter(prefix="/websites")


@router.post("/scrape")
def scrape_websites(limit: int = 100):
    """
    Scrapes the next batch of website domains that haven't been scraped yet
    """
    # Check bucket access before scraping, so missing access fails immediately.
    if not storage.can_write():
        raise HTTPException(
            status_code=500,
            detail=f"Current credentials cannot upload to bucket '{GCP_BUCKET_NAME}'",
        )

    try:
        summary = scrape.run(limit)
    except FileNotFoundError as e:
        print(f"Scrape step failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "step": "scrape",
                "error": f"{type(e).__name__}: {e}",
            },
        )

    try:
        signals_summary = signals.run()
    except FileNotFoundError as e:
        print(f"Signals step failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "failed",
                "step": "signals",
                "error": f"{type(e).__name__}: {e}",
            },
        )

    return {
        "status": "success",
        "scrape_summary": summary,
        "signals_summary": signals_summary,
    }
