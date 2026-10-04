import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DOB_APP_TOKEN_ID = os.getenv('DOB_APP_TOKEN_ID')
DOB_APP_TOKEN = os.getenv('DOB_APP_TOKEN')
