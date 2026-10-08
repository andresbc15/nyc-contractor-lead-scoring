from pipeline import socrata
from pipeline.contracts.licenses import DobLicenseRow
from pydantic import ValidationError

DATASET_ID = "t8hj-ruu2"

def extract(max_rows):

    rows = socrata.fetch(dataset_id=DATASET_ID, max_rows=max_rows)

    if not rows:
        raise ValueError(f"No rows returned from dataset: {DATASET_ID}")

    valid_rows = []

    errors = 0
    for row in rows:
        try:
            valid_rows.append(DobLicenseRow.model_validate(row))
        except ValidationError as e:
            errors += 1
            print(f"Row {row.get('id')} failed the pydantic test: {e}")

    if not valid_rows:
        raise ValueError(f"All {len(rows)} rows failed validation for {DATASET_ID}")
    print(f"Extracted {len(valid_rows)} rows with {errors} errors ({errors / len(rows):.2%})")
    return valid_rows