"""
Shared fetcher for NYC Open Data (Socrata), used by every extractor that pulls
from data.cityofnewyork.us: licenses (t8hj-ruu2) and permits (rbx6-tga4).

Upgrade (AI-assisted, written with Claude): `fetch` now takes an optional
`where` filter and treats `max_rows` as a real cap, separate from the page
size. Callers that pass neither get exactly the old behaviour.
"""

import requests
from pipeline.config import DOB_APP_TOKEN_ID, DOB_APP_TOKEN

# SODA v3 query endpoint. The dataset id is appended per call, e.g.
# https://data.cityofnewyork.us/api/v3/views/rbx6-tga4/query.json
BASE_URL = "https://data.cityofnewyork.us/api/v3/views"

# Rows requested per page. 50,000 is accepted by NYC Open Data and keeps the
# number of requests low (the full licenses table is 3 requests, not ~104).
DEFAULT_PAGE_SIZE = 50000


def clean_keys(original_dict: dict) -> dict:
    # v3 returns system columns with a leading colon (":id", ":updated_at").
    # Strip it so every key is a plain name the pydantic contracts can read.
    return {key.lstrip(":"): value for key, value in original_dict.items()}


def fetch(dataset_id, max_rows=None, where=None, page_size=DEFAULT_PAGE_SIZE, order=":id"):
    """
    Return rows of an NYC Open Data dataset, one page at a time.

    dataset_id  Socrata id of the dataset, e.g. "t8hj-ruu2" (licenses).
    max_rows    Most rows to return. None means no limit: keep paging until
                the dataset (or the filtered result) runs out.
    where       Optional SoQL condition, without the word WHERE, e.g.
                "issued_date >= '2025-01-01'" or ":updated_at > '2026-10-10'".
                None means no filter: every row in the dataset.
    page_size   Rows per request. Only affects speed, never which rows come back.
    order       Column to sort by. Paging is only stable with a fixed order, so
                pages never repeat or skip rows; ":id" is unique per row.
    """

    url = f"{BASE_URL}/{dataset_id}/query.json"
    all_rows = []
    page_number = 1

    # A small request should not download a full 50,000-row page just to keep
    # the first few rows. The page size stays fixed for the whole loop, which
    # pageNumber-based paging needs.
    if max_rows is not None:
        page_size = min(page_size, max_rows)

    # Build the SoQL query once. The WHERE clause is only added when a filter
    # was given, so a call without `where` sends the same query as before.
    query = "SELECT *"
    if where:
        query += f" WHERE {where}"
    query += f" ORDER BY {order}"

    while True:
        params = {
            "pageNumber": page_number,
            "pageSize": page_size,
            "query": query,
        }

        # Key ID + key secret, sent as basic auth. Both come from .env.
        response = requests.get(
            url,
            params=params,
            auth=(DOB_APP_TOKEN_ID, DOB_APP_TOKEN),
            timeout=180,
        )

        # Stop on any HTTP error (403 bad key, 429 rate limit, 5xx) instead of
        # saving a partial or empty page as if it were real data.
        response.raise_for_status()

        page = response.json()
        all_rows.extend(clean_keys(row) for row in page)

        # A page shorter than page_size means there is nothing after it.
        if len(page) < page_size:
            break

        # Enough rows collected for the caller's cap.
        if max_rows is not None and len(all_rows) >= max_rows:
            break

        page_number += 1

    # The last page can overshoot the cap, so trim to exactly max_rows.
    if max_rows is not None:
        all_rows = all_rows[:max_rows]

    return all_rows
