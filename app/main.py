import requests
from fastapi import FastAPI, HTTPException

from app.routers import licenses, permits
from pipeline import storage
from pipeline.config import  DOB_APP_TOKEN

app = FastAPI()
app.include_router(licenses.router)
app.include_router(permits.router)