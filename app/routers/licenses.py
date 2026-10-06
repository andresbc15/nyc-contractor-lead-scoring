import requests
from fastapi import APIRouter, HTTPException
from pipeline.extract import licenses
# TO DO: Import the storage from storage.py

router = APIRouter(prefix="/extract")

@router.post("/licenses")
def extract_licenses(max_rows=1000):
    try:
        records = licenses.extract(max_rows)
        # TO DO: Use storage function to upload to bucket
    except requests.HTTPError as e:
        status = e.response.status_code
        print(f"Socrata returned {status}: {e}")
