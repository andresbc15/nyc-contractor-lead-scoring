from pydantic import ValidationError
from datetime import date, timedelta

from pipeline import socrata
from pipeline.contracts.permits import PermitRecord

DATASET_ID = "rbx6-tga4"
PAGE_SIZE = 50000
BACKFILL_START = "2025-01-01"


def extract(since=None, backfill=False):

    if backfill:
        where = f"issued_date >= '{BACKFILL_START}'"
    else:
        if since is None:
            since = (date.today() - timedelta(days=1)).isoformat()
        where = f":updated_at > '{since}'"

    rows = socrata.fetch(dataset_id=DATASET_ID, max_rows=PAGE_SIZE, where=where)
    if not rows:
        if backfill:
            raise ValueError("Backfill returned no permits from NYC")
        print(f"No permits changed since {since}")
        return []


    correct_rows = []
    errors = 0
    for row in rows:
        try:
            correct_rows.append(PermitRecord.model_validate(row))
        except ValidationError as e:
            errors += 1
            print(f"Permit {row.get('job_filing_number')} failed the contract: {e}")

    if not correct_rows:
        raise ValueError(f"All {len(rows)} permits failed the contract")

    print(f"Extracted {len(correct_rows)} permits with {errors} errors ({errors / len(rows):.2%})")
    return correct_rows