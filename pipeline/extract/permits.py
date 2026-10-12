from pydantic import ValidationError

from pipeline import socrata
from pipeline.contracts.permits import PermitRecord

DATASET_ID = "rbx6-tga4"
PAGE_SIZE = 50000
BACKFILL_START = "2025-01-01"


def extract(since=None):

    if since is None:
        where = f"issued_date >= '{BACKFILL_START}'"
    else:
        where = f":updated_at > '{since}'"

    rows = socrata.fetch(dataset_id=DATASET_ID, max_rows=PAGE_SIZE, where=where)
    if not rows:
        raise ValueError("No permits returned from NYC")

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