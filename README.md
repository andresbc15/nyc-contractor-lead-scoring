# nyc-contractor-lead-scoring
Which New York City trade contractors look like high-value leads for a B2B payments platform, and how do their job frequency and cost vary by trade and company size?

Dashboard: https://nyc-leads-dashboard-435qo2trra-uw.a.run.app
API docs: https://nyc-api-server-435qo2trra-uw.a.run.app/docs

## Team Members

| Name | GitHubID | Role / Focus |
| --- | --- | --- |
| Nathan Gong | nathan-gong9 | Fastapi implementation, README, contract review, GCS folder structure |
| Yash Tiwari | yshtiwa | Permits extractor + contract, backfill, /extract/permits endpoint |
| Andres Javier Miguel Cojuangco | andresbc15 | License, email, and contract extraction + HTML storage |
| Joseph Lacap | Joseph5105 | GCP project, bucket and service accounts + scheduled collection of all sources|
| Disha Khati | dkhati2 | Python transformation + streamlit dashboard, team contract|

---

## Problem Statement
- We want to understand payment patterns using the contractors approved building permit histories. We combined the approved building permits in New York City with the city's contracting license registry to find job value and frequency patterns by trade and company size. We then used the business emails and company names in the license registry and scraped their websites to find out how they actually collect money and the services they provide. We built a dashboard showing these patterns by trade and size, and scored each contractor as a potential customer for the sales and marketing teams. A B2B payments company selling into construction would use this directly.

---

## Data Sources and Integration Goal

### Sources
| # | Source & Link | Method | What it contains | Update frequency | Access requirements |
| --- | --- | --- | --- | --- | --- |
| 1 | [DOB NOW: Build - Approved Permits](https://data.cityofnewyork.us/Housing-Development/DOB-NOW-Build-Approved-Permits/rbx6-tga4/about_data) | API | Applicant license #, estimated job costs, job classifications, issue dates, job descriptions, and site information | NYC updates daily, collected daily at 6:00 PT | App Token |
| 2 | [DOB License Info](https://data.cityofnewyork.us/Housing-Development/DOB-License-Info/t8hj-ruu2/about_data) | API | License numbers + types + statuses, business names + emails | NYC updates daily, collected weekly (Mondays 6:30 PT) | App Token |
| 3 | Contractor Websites (domains taken from emails + names in source 2) | Scraped | Homepage HTML + Payment methods (Stripe/Square/Paypal) | Daily at 7:00 PT up to 300 new sites per run | None, public homepages only |

The App Token required to access sources 1 and 2 should be held in the DOB_APP_TOKEN variable in the .env file.

### Integration Goal
- The approved building permits include estimated job costs, which serve as our signal for total payment volume. The contracting license registry gives us more information about the companies, such as the trades they specialize in, their contact information, and their legal business names and emails. These can contain their business domains. Those domains take us to the contractors' websites, where we can see what services they offer and how they collect payment. In summary, these data sources allow us to identify patterns and trends by different segments. 

---

## Setup Instructions (Locally)

### Prerequisites
- Python 3.11.5+
- Access to the "nyc-contractor-leads-table-data" bucket in the project "nyc-contractor-leads" or a fresh project.
- A free app token for the NYC Open Data website

### 1. Clone the repository
```bash
git clone https://github.com/andresbc15/nyc-contractor-lead-scoring
cd nyc-contractor-lead-scoring
```

### 2. Install environment requirements
For Mac/Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock.txt
```

For Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

This is because of an error involving install uvloop on Windows.

### 3. Configure environment variables
Copy the example file and fill in your own values:

```bash
cp .env_template .env
```

| Variable | Description | Example |
| --- | --- | --- |
| `GCP_PROJECT_ID` | ID of the prerequisite GCP project | `nyc-contractor-leads` |
| `GCP_BUCKET_NAME` | Name of the required bucket inside the GCP project | `nyc-contractor-leads-table-data` |
| `GCP_SERVICE_ACCOUNT_KEY` | Absolute path to your service account JSON | `/Users/you/.ssh/key.json` |
| `DOB_APP_TOKEN` | Free App Token for the NYC Open Data website | `Tl2qxxxxxxxxxxKPd` |


**How to get the DOB app token:** sign up or sign in at [data.cityofnewyork.us](https://data.cityofnewyork.us), go to your profile, open Developer Settings and click Create New App Token. Copy the App Token (not the Secret Token) into `.env` as `DOB_APP_TOKEN`.

**Fill in `.env`.** Replace each description with the real value. The scripts `source` this file, so:
   - write `KEY=value` with no spaces around `=` and no spaces in the value
   - don't leave the template's description text after the `=`

The GCP_SERVICE_ACCOUNT_KEY is not required. Can leave it blank and alternatively run 
```bash
gcloud auth application-default login
```

### 4. How to call your endpoint
To start the API server,
```bash
fastapi dev app/main.py
```
Open local browser:
[http://localhost:8000/docs](http://localhost:8000/docs)
to see every endpoint and try them from the browser.

| Method | Path | What it does | Parameters |
| --- | --- | --- | --- |
| `POST` | `/extract/permits` | Pulls approved permits from NYC Open Data and saves them to `raw/permits/`, then rebuilds the dashboard tables in `processed/` | `since`: only permits updated after this date (default: yesterday). `backfill`: pull every permit issued since 2025-01-01. Backfills automatically if the bucket has no permits yet. |
| `POST` | `/extract/licenses` | Pulls the license registry to `raw/licenses/`, then saves each license's email domain to `intermediate/` | `max_rows`: rows per request to NYC (default 1000). It still pulls the whole registry. |
| `POST` | `/websites/scrape` | Scrapes the next batch of contractor homepages to `raw/websites/` and saves payment signals to `intermediate/website_signals/` | `limit`: max homepages per run (default 300). Skips if `/extract/licenses` hasn't run yet. |
| `GET` | `/data/{table}` | Returns one processed table as JSON for the dashboard | `table`: `contractors`, `by_trade`, `by_trade_size`, `monthly` or `by_borough` |

Raw and intermediate files are saved as `<stage>/<name>/YYYY_MM_DD_HH_MM_SSZ.json`. The processed tables are saved as `processed/<table>.parquet` and get overwritten each time the transform runs.

To run the dashboard, start the API first, then in a separate terminal run:
```bash
cd dashboard
pip install -r requirements.txt
streamlit run app.py
```
The dashboard runs at http://localhost:8501 and reads data from the API at http://localhost:8000.

---

## Remote Deployment

How to deploy and schedule the project on Google Cloud with `gcp_script.sh`.
Everything runs in your GCP_PROJECT_ID, region `us-west1`, and stays inside the free tier.

### 1. What gets deployed

| Piece | Name | What it does |
|---|---|---|
| Cloud Run service | `nyc-api-server` | FastAPI app (`app/` + `pipeline/`). Collects data, writes it to the bucket and builds the dashboard tables |
| Cloud Run service | `nyc-leads-dashboard` | Streamlit app (`dashboard/`). Shows the data |
| Cloud Scheduler job | `collect-permits` | `POST /extract/permits` every day at 6:00 PT, then rebuilds the dashboard tables in `processed/` |
| Cloud Scheduler job | `collect-licenses` | `POST /extract/licenses` every Monday at 6:30 PT |
| Cloud Scheduler job | `collect-websites` | `POST /websites/scrape` every day at 7:00 PT |
| Secret Manager | `socrata-app-token` | The NYC Open Data token (`DOB_APP_TOKEN`) |

Both services run as the `pipeline-uploader` service account, so **nobody needs a service account key**.
You don't need Docker installed either: `gcloud run deploy --source` uploads the folder, and Cloud Build builds the image in the cloud.

### 2. Commands

Run from the repo root (or anywhere, since the script `cd`s to its own folder).

| Command | What it does |
|---|---|
| `./gcp_script.sh init` | Enables the APIs, creates the `pipeline-uploader` service account and the bucket if they don't exist yet, grants Cloud Build its role, uploads `DOB_APP_TOKEN` to Secret Manager (only if it changed), lets `pipeline-uploader` read it |
| `./gcp_script.sh api` | Builds and deploys the FastAPI service |
| `./gcp_script.sh scheduler` | Deletes and recreates every job in `JOBS`, then fires each once |
| `./gcp_script.sh web` | Builds and deploys the Streamlit dashboard, pointed at the API |
| `./gcp_script.sh urls` | Prints the API URL, its `/docs` page, and the dashboard URL |
| `./gcp_script.sh all` | `init` → `api` → `scheduler` → `web` → `urls` (first-time setup) |

**Make the script runnable** (only if `./gcp_script.sh` says "permission denied")
```bash
chmod +x gcp_script.sh
```

**Fresh project (grader):** install the [gcloud CLI](https://docs.cloud.google.com/sdk/docs/install-sdk), log in, and point it at a project that has billing enabled:
```bash
gcloud auth login
gcloud config set project <PROJECT_ID>
```
Then fill in `.env` with that project ID, a bucket name (the script creates the bucket if it doesn't exist) and your app token, and run:
```bash
./gcp_script.sh all
```

### 3. Check that it worked

```bash
./gcp_script.sh urls                                         # both URLs

gcloud storage ls -r gs://<GCP_BUCKET_NAME>/       # raw/, intermediate/ and processed/
```

On a fresh project the permits job fires before the licenses job, so the dashboard tables are skipped on that first run. Run `collect-permits` once more (Cloud Scheduler → Force run, or `POST /extract/permits` from `/docs`) and `processed/` fills in.

**FastAPI docs:** open `<API URL>/docs` to see every endpoint and try them from the browser. Then open the dashboard URL; the tables and charts should load.

---
## Repository Structure
```
nyc-contractor-lead-scoring/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── routers/
│       ├── __init__.py
│       ├── data.py          
│       ├── licenses.py
│       ├── permits.py
│       └── websites.py
├── dashboard/               
│   ├── .dockerignore
│   ├── .gitignore
│   ├── Dockerfile
│   ├── app.py
│   └── requirements.txt
├── pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── socrata.py
│   ├── storage.py
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── licenses.py
│   │   └── permits.py
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── licenses.py
│   │   └── permits.py
│   ├── transform/
│   │   ├── __init__.py
│   │   └── build.py
│   └── websites/
│       ├── __init__.py
│       ├── domains.py
│       ├── scrape.py
│       └── signals.py       
├── .dockerignore
├── .env_template
├── .gitignore
├── Dockerfile
├── config.sh
├── gcp_script.sh
├── README.md
├── requirements.lock.txt
└── requirements.txt
```