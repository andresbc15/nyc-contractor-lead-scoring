# =====CONFIG/LOAD====

ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: '$ENV_FILE' not found. Run: 
    cp .env_template .env" >&2
    exit 1
fi
set -a; source "$ENV_FILE"; set +a

PROJECT_ID="${GCP_PROJECT_ID:-}"

BUCKET="${GCP_BUCKET_NAME:-}"

# ==== CLOUD RUN ====

REGION="us-west1"

API_SERVICE="nyc-api-server"

WEB_SERVICE="nyc-leads-dashboard"

API_DIR="."

WEB_DIR="./dashboard"

API_PORT=8000

WEB_PORT=8501

API_TIMEOUT=1800

# Both services run as this account, so the code gets its GCS access with no key file
RUNTIME_SA_NAME="pipeline-uploader"
RUNTIME_SA="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# ==== SECRET MANAGER ==== (names only: values from .env)

DOB_TOKEN_SECRET="socrata-app-token" # holds DOB_APP_TOKEN from .env

# ==== Cloud Scheduler ====

SCHEDULER_TZ="America/Los_Angeles"

ATTEMPT_DEADLINE="1800s"

MAX_RETRIES=1

JOBS=(
    "collect-permits|0 6 * * *|/extract/permits"
    "collect-licenses|30 6 * * 1|/extract/licenses"
    "collect-websites|0 7 * * *|/websites/scrape"
) # Data extraction jobs (Max 3 Jobs to stay in the free tier)




