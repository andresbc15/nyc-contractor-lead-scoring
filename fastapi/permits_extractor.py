import os
import requests 
from dotenv import load_dotenv
#Read my .env
load_dotenv()
token = os.getenv("DOB_APP_TOKEN")

response = requests.get(url="https://data.cityofnewyork.us/resource/rbx6-tga4.json", headers={"X-App-Token": token}, params={"$limit": 5}, timeout=30)
print("Status:", response.status_code)

rows = response.json()
print("Rows received:", len(rows))
print("First row keys:", list(rows[0].keys()))