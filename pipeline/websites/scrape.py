from collections import Counter
from datetime import UTC, datetime

import requests

from pipeline import storage

# Some sites block the default python-requests user agent
HEADERS = {"User-Agent": "nyc-contractor-scraper/1.0"}


def fetch_html(domain):
    # Try with https:
    try:
        response = requests.get(
            f"https://{domain}",
            headers=HEADERS,
            timeout=(5, 10),  # (connect, read)
        )
    except requests.RequestException:
        # Try with http:
        try:
            response = requests.get(
                f"http://{domain}",
                headers=HEADERS,
                timeout=(5, 10),  # (connect, read)
            )
        # Timeouts, dead domains, etc.
        except requests.RequestException as e:
            return {
                "domain": domain,
                "final_url": None,
                "status": None,
                "html": None,
                "error": type(e).__name__,
                "fetched_at": datetime.now(UTC).isoformat(),
            }

    # Responded but with an error page
    if response.status_code >= 400:
        return {
            "domain": domain,
            "final_url": response.url,
            "status": response.status_code,
            "html": None,
            "error": f"http_{response.status_code}",
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    # Responses may not be in html
    content_type = response.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return {
            "domain": domain,
            "final_url": response.url,
            "status": response.status_code,
            "html": None,
            "error": "not_html",
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    # Domain may not be connected to a live website
    if len(response.text) < 500:
        return {
            "domain": domain,
            "final_url": response.url,
            "status": response.status_code,
            "html": response.text,
            "error": "parked",
            "fetched_at": datetime.now(UTC).isoformat(),
        }

    return {
        "domain": domain,
        "final_url": response.url,
        "status": response.status_code,
        "html": response.text,
        "error": None,
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def run(limit=100):

    # Check if there are any websites to scrape
    try:
        file_name, targets = storage.read_latest_file(
            "website_domains", stage="intermediate"
        )
    except FileNotFoundError:
        raise FileNotFoundError("No scrape targets found")

    # Check for websites that were scraped in the past
    try:
        _, scraped = storage.read_latest_file("website_status", stage="intermediate")
    except FileNotFoundError:
        scraped = []

    # Make set for those domains
    prev_scraped = {row["domain"] for row in scraped}

    # Go for domains with the most licenses first
    targets = sorted(targets, key=lambda row: row["n_licenses"], reverse=True)
    targets = [t for t in targets if t["domain"] not in prev_scraped][:limit]

    # No target or every domain already scraped
    if not targets:
        return {"source": file_name, "domains": 0, "errors": {}, "uploaded": None}

    results = []
    scraped_website_status = []

    for target in targets:
        result = fetch_html(target["domain"])
        results.append(result)
        # Make a list of websites that were scraped so we can reference later
        scraped_website_status.append(
            {key: result[key] for key in ("domain", "status", "error", "fetched_at")}
        )

    # Upload html and status for every domain to raw/websites
    blob_name = storage.write_data("websites", results)

    # Extend the list of websites that were scraped
    status_blob_name = storage.write_data(
        "website_status", scraped + scraped_website_status, stage="intermediate"
    )

    # Return a summary
    return {
        "source": file_name,
        "domains": len(results),
        "errors": dict(Counter(row["error"] for row in results)),
        "uploaded": [blob_name, status_blob_name],
    }


if __name__ == "__main__":
    print(run())
