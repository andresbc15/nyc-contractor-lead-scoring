import requests
import os
import json
from fastapi import FastAPI
from fastapi import HTTPException
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import storage

app = FastAPI()
load_dotenv()

dob_app_token = os.getenv("DOB_APP_TOKEN")
project_id = os.getenv("GCP_PROJECT_ID")
bucket_name = os.getenv("GCP_BUCKET_NAME")
service_account_key = os.getenv("GCP_SERVICE_ACCOUNT_KEY")

credentials = service_account.Credentials.from_service_account_file(service_account_key)
client = storage.Client(project=project_id,
                        credentials=credentials)
bucket = client.bucket(bucket_name)

url = "https://data.cityofnewyork.us/resource/rbx6-tga4.json"
header = {"X-App-Token": dob_app_token}
params={"$limit": 1}

def upload_json_to_gcp(data, blob_name):
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps(data), content_type="application/json")

@app.get("/get_dob_data")
def get_dob_data():
    response = requests.get(url, params = params, headers = header, timeout=15)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="API Call failed")
    data = response.json()
    blob_name = "raw/dob_permits/dob_permits_v1.json"
    upload_json_to_gcp(data, blob_name)
    return {"uploaded": blob_name, "rows": len(data)}