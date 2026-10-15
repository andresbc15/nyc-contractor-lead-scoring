from fastapi import APIRouter, HTTPException

from pipeline import storage
from pipeline.config import GCP_BUCKET_NAME
from pipeline.websites import scrape, signals

router = APIRouter(prefix="/websites")


@router.post("/scrape")
def scrape_websites(limit: int = 300):
    """
    - Scrapes the next batch of website domains (up to limit) that haven't been scraped
    yet and extracts the signals for that batch
    - Saves html to raw/websites/ and updates the running list of scraped website (intermediate/website_status)
    - Uploads running collection of signals to intermediate/website_signals/
    - Returns "skipped" if there are no scrape targets yet (run POST /extract/licenses first)
    """
    # Check bucket access before scraping, so missing access fails immediately.
    if not storage.can_write():
        raise HTTPException(
            status_code=500,
            detail=f"Current credentials cannot upload to bucket '{GCP_BUCKET_NAME}'",
        )

    try:
        summary, results = scrape.run(limit)
    except FileNotFoundError as e:
        print(f"Scrape skipped: {e}")
        return {
            "status": "skipped",
            "reason": "No scrape target yet. POST /extract/licenses first",
        }

    try:
        signals_summary = signals.run(results)
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
