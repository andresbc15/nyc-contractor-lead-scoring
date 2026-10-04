from pipeline import socrata
from pipeline.contracts.licenses import DobLicenseRow
from pydantic import ValidationError

DATASET_ID = "t8hj-ruu2"

def extract_licenses(max_rows=1000):

    rows = socrata.fetch(dataset_id=DATASET_ID, max_rows=max_rows)

    if not rows:
        raise ValueError(f"No rows returned from dataset: {DATASET_ID}")

    valid_rows = []
    
    for row in rows:
        try:
            valid_rows.append(DobLicenseRow.model_validate(row))
        except ValidationError as e:
            print(f"Row {row.get('id')} failed the pydantic test: {e}")

    if not valid_rows:
        raise ValueError(f"All {len(rows)} rows failed validation for {DATASET_ID}")

    return valid_rows