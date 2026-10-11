import requests
from pydantic import ValidationError

from pipeline.config import DOB_APP_TOKEN
from pipeline.contracts.permits import PermitRecord

URL = "https://data.cityofnewyork.us/resource/rbx6-tga4.json"
PAGE_SIZE = 50000
BACKFILL_START = "2025-01-01"


def fetch(where, max_rows=None):
    headers = {"X-App-Token": DOB_APP_TOKEN}
    all_rows = []
    offset = 0

    while True:
        limit = PAGE_SIZE
        if max_rows is not None:
            limit = min(PAGE_SIZE, max_rows - len(all_rows))

        params = {
            "$where": where,
            "$order": ":id",
            "$limit": limit,
            "$offset": offset,
        }
        response = requests.get(URL, headers=headers, params=params, timeout=180)
        response.raise_for_status()

        page = response.json()
        all_rows.extend(page)

        if len(page) < limit:
            break
        if max_rows is not None and len(all_rows) >= max_rows:
            break
        offset += limit

    return all_rows


def extract(since=None, max_rows=None):

    if since is None:
        where = f"issued_date >= '{BACKFILL_START}'"
    else:
        where = f":updated_at > '{since}'"

    rows = fetch(where, max_rows)
    if not rows:
        raise ValueError("No permits returned from NYC")

    valid_rows = []
    errors = 0
    for row in rows:
        try:
            valid_rows.append(PermitRecord.model_validate(row))
        except ValidationError as e:
            errors += 1
            print(f"Permit {row.get('job_filing_number')} failed the contract: {e}")

    if not valid_rows:
        raise ValueError(f"All {len(rows)} permits failed the contract")

    print(f"Extracted {len(valid_rows)} permits with {errors} errors ({errors / len(rows):.2%})")
    return valid_rows