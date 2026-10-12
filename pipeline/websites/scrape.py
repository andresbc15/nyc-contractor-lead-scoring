from datetime import UTC, datetime

import requests

# Some sites block the default python-requests user agent
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; nyc-contractor-research)"}


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
