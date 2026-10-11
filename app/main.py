import requests
from fastapi import FastAPI, HTTPException

from app.routers import licenses
from pipeline import storage
from pipeline.config import  DOB_APP_TOKEN

app = FastAPI()
app.include_router(licenses.router)

url = "https://data.cityofnewyork.us/resource/rbx6-tga4.json"
header = {"X-App-Token": DOB_APP_TOKEN}
params={"$limit": 1}

@app.get("/get_dob_data")
def get_dob_data():
    response = requests.get(url, params = params, headers = header, timeout=15)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="API Call failed")
    data = response.json()
    blob_name = storage.write_raw("permits", data)
    return {"uploaded": blob_name, "rows": len(data)}