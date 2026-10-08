import requests
from pipeline.config import DOB_APP_TOKEN_ID, DOB_APP_TOKEN

BASE_URL = "https://data.cityofnewyork.us/api/v3/views"

def clean_keys(original_dict: dict) -> dict:
    return {key.lstrip(":"): value for key, value in original_dict.items()}

def fetch(dataset_id, max_rows, order=":id"):

    # Initialize
    url = f"{BASE_URL}/{dataset_id}/query.json"
    all_rows = []
    page_number = 1

    # Keep looping until we hit a page that isnt full
    while True:
        # Build params in loop so page_number updates
        params = {
                "pageNumber": page_number,
                "pageSize": max_rows,
                "query": f"SELECT * ORDER BY {order}"
            }
        
        # Make the request
        response = requests.get(
            url,
            params=params,
            auth=(DOB_APP_TOKEN_ID, DOB_APP_TOKEN),
            timeout=180
        )

        # Raise errors
        response.raise_for_status()

        # Turn bytes into json format, clean, and extend
        response_json = response.json()
        cleaned_response = [clean_keys(row) for row in response_json]
        all_rows.extend(cleaned_response)

        # Check when all data is retrieved
        if len(response_json) < max_rows:
            break
        page_number += 1

    return all_rows
