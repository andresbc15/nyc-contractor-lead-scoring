#!/usr/bin/env bash

set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

# ==== VALIDATION ====
for _var in PROJECT_ID BUCKET REGION API_SERVICE WEB_SERVICE API_DIR WEB_DIR \
            API_PORT WEB_PORT RUNTIME_SA DOB_TOKEN_SECRET SCHEDULER_TZ; do
  if [ -z "${!_var:-}" ]; then
    echo "Error: $_var is empty -- set it in .env or config.sh." >&2
    exit 1
  fi
done
unset _var

log() { printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }

# Plain (non-secret) env vars for both Cloud Run services.
# No GCP_SERVICE_ACCOUNT_KEY: with it unset, pipeline/storage.py logs in as RUNTIME_SA.
APP_ENV="GCP_PROJECT_ID=${PROJECT_ID},GCP_BUCKET_NAME=${BUCKET}"
APP_ENV+=",DOB_APP_TOKEN_ID=${DOB_APP_TOKEN_ID:-}"

# ==== First Time Project Setup ====
init() {
    if [ -z "${DOB_APP_TOKEN:-}" ]; then
        echo "Error: DOB_APP_TOKEN is empty in .env" >&2
        exit 1
    fi

    gcloud config set project "$PROJECT_ID"
    gcloud config set run/region "$REGION"
    gcloud services enable \
        run.googleapis.com \
        cloudbuild.googleapis.com \
        artifactregistry.googleapis.com \
        cloudscheduler.googleapis.com \
        secretmanager.googleapis.com \
        storage.googleapis.com

    local project_number compute_sa
    project_number=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
    compute_sa="${project_number}-compute@developer.gserviceaccount.com"

    log "Letting Cloud Build run from source as ${compute_sa}"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:${compute_sa}" \
    --role=roles/cloudbuild.builds.builder \
    --condition=None >/dev/null

    log "Storing DOB_APP_TOKEN in Secret Manager as '${DOB_TOKEN_SECRET}'"
    if ! gcloud secrets describe "$DOB_TOKEN_SECRET" >/dev/null 2>&1; then
        gcloud secrets create "$DOB_TOKEN_SECRET" --replication-policy=automatic
    fi
    current=$(gcloud secrets versions access latest --secret="$DOB_TOKEN_SECRET" 2>/dev/null || true)
    if [ "$current" != "$DOB_APP_TOKEN" ]; then
        printf '%s' "$DOB_APP_TOKEN" | gcloud secrets versions add "$DOB_TOKEN_SECRET" --data-file=-
    else
        echo "DOB token unchanged, no new version added"
    fi

    log "Letting ${RUNTIME_SA} read the DOB token"
    gcloud secrets add-iam-policy-binding "$DOB_TOKEN_SECRET" \
        --member="serviceAccount:${RUNTIME_SA}" \
        --role=roles/secretmanager.secretAccessor >/dev/null
}

# ==== API SERVICE ====
deploy_api(){
    if [ ! -f "$API_DIR/Dockerfile" ]; then
        echo "Error: no Dockerfile in '$API_DIR'." >&2
        exit 1
    fi

    log "Deploying ${API_SERVICE} from ${API_DIR} (Cloud Build builds the image)"
    gcloud run deploy "$API_SERVICE" \
        --source "$API_DIR" \
        --region "$REGION" \
        --port="$API_PORT" \
        --allow-unauthenticated \
        --timeout="$API_TIMEOUT" \
        --max-instances=1 \
        --memory=2Gi \
        --service-account="$RUNTIME_SA" \
        --set-env-vars="$APP_ENV" \
        --set-secrets="DOB_APP_TOKEN=$DOB_TOKEN_SECRET:latest" \
        --quiet
}

api_url(){
    local url
    url=$(gcloud run services describe "$API_SERVICE" \
    --region "$REGION" --format="value(status.url)" 2>/dev/null || true)
    if [ -z "$url" ]; then
        echo "Error: could not find the URL for '$API_SERVICE' in $REGION. Deploy it first" >&2
        return 1
    fi
    echo "$url"
}

web_url(){
  local url
    url=$(gcloud run services describe "$WEB_SERVICE" \
    --region "$REGION" --format="value(status.url)" 2>/dev/null || true)
    if [ -z "$url" ]; then
        echo "Error: could not find the URL for '$WEB_SERVICE' in $REGION. Deploy it first" >&2
        return 1
    fi
    echo "$url"
}

# ==== WEB APP ====
deploy_web() {
  if [ ! -f "$WEB_DIR/Dockerfile" ]; then
    echo "Error: no Dockerfile in '$WEB_DIR'." >&2
    exit 1
  fi
  local url; url="$(api_url)"


  # the dashboard never calls Socrata from --set-env-vars
  log "Deploying ${WEB_SERVICE} from ${WEB_DIR}, pointing at ${url}"
  gcloud run deploy "$WEB_SERVICE" \
    --source "$WEB_DIR" \
    --region "$REGION" \
    --port="$WEB_PORT" \
    --allow-unauthenticated \
    --max-instances=1 \
    --service-account="$RUNTIME_SA" \
    --set-env-vars="${APP_ENV},API_SERVICE_URL=${url}" \
    --quiet
}

# ==== CLOUD SCHEDULER ====
deploy_scheduler() {
  local url; url="$(api_url)"
  local entry name schedule path

  for entry in "${JOBS[@]}"; do
    IFS='|' read -r name schedule path <<< "$entry"

    # `jobs update http` rejects --headers, so delete and recreate instead of create/update.
    gcloud scheduler jobs delete "$name" --location="$REGION" --quiet 2>/dev/null || true

    log "Creating '${name}' (${schedule} ${SCHEDULER_TZ}) -> POST ${url}${path}"
    gcloud scheduler jobs create http "$name" \
      --location="$REGION" \
      --schedule="$schedule" \
      --time-zone="$SCHEDULER_TZ" \
      --uri="${url}${path}" \
      --http-method=POST \
      --headers="Content-Type=application/json" \
      --message-body='{}' \
      --attempt-deadline="$ATTEMPT_DEADLINE" \
      --max-retry-attempts="$MAX_RETRIES"

    log "Triggering '${name}' once so you can confirm it works"
    gcloud scheduler jobs run "$name" --location="$REGION"
  done

  echo "Check the results with:"
  echo "  gcloud run services logs read ${API_SERVICE} --region=${REGION} --limit=50"
  echo "  gcloud storage ls -r gs://${BUCKET}/raw/"
}

show_urls() {
  local api web
  api="$(api_url)"
  web="$(web_url || true)"
  echo "API     : ${api}   (docs: ${api}/docs)"
  echo "Web app : ${web:-not deployed}"
}

# ==== ENTRY POINT ====
case "${1:-all}" in
  all)       init; deploy_api; deploy_scheduler; deploy_web; show_urls ;;
  init)      init ;;
  api)       deploy_api ;;
  web)       deploy_web ;;
  scheduler) deploy_scheduler ;;
  urls)      show_urls ;;
  *) echo "usage: $0 {all|init|api|web|scheduler|urls}" >&2; exit 1 ;;
esac

log "Done"
