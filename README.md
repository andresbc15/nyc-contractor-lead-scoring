# nyc-contractor-lead-scoring
Which New York City trade contractors look like high-value leads for a B2B payments platform, and how do their job frequency and cost vary by trade and company size?

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
- We want to understand payment patterns using contractors approved building permit histories. We will combine the approved building permits in New York City with the city's contracting license registry to find job value and frequency patterns by trade and company size. We will then use the business emails and company names in the license registry to find their websites and scrape them for how they actually collect money and the services they provide. We will build a dashboard showing these patterns by trade and size. If time permits, we will score contractors as potential customers and pass the top ones to sales or marketing. A B2B payments company selling into construction would use this directly.


---

## Data Sources and Integration Goal

### Sources
| # | Source & Link | Method | What it contains | Update frequency | Access requirements |
| --- | --- | --- | --- | --- | --- |
| 1 | [DOB NOW: Build - Approved Permits](https://data.cityofnewyork.us/Housing-Development/DOB-NOW-Build-Approved-Permits/rbx6-tga4/about_data) | API | Applicant license #, estimated job costs, job classifications, issue dates, job descriptions, and site information | daily | App Token |
| 2 | [DOB License Info](https://data.cityofnewyork.us/Housing-Development/DOB-License-Info/t8hj-ruu2/about_data) | API | License numbers + types + statuses, business names + emails | daily | App Token |
| 3 | Contractor Websites (domains taken from emails + names in source 2) | Scraped | Services offered + Payment methods | Continuous | sends user agents to websites to scrape |

The App Token required to access sources 1 and 2 should be held in the DOB_APP_TOKEN variable in the .env file. An optional DOB_APP_TOKEN_ID is also used. 

### Integration Goal
- The approved building permits include estimated job costs, which serve as our signal for total payment volume. The contracting license registry gives us more information about the companies, such as the trades they specialize in, their contact information, and their legal business names and emails. These can contain their business domains. Those domains take us to the contractors' websites, where we can see what services they offer and how they collect payment. In summary, these data sources allow us to identify patterns and trends by different segments. 

---

## Setup Instructions (Locally)

### Prerequisites
- Python 3.11+
- A GCP service account key with access to the "nyc-contractor-leads-table-data" bucket in the project "nyc-contractor-lead-scoring"
- A free app token for the NYC Open Data website

### 1. Clone the repository
```bash
git clone https://github.com/andresbc15/nyc-contractor-lead-scoring
cd nyc-contractor-lead-scoring
```

### 2. Install environment requirements
For Mac/Linux:
```bash
pip install -r requirements.lock.txt
```

For Windows:
```bash
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

The GCP_SERVICE_ACCOUNT_KEY is not required. Can leave it blank and alternatively run 
```bash
gcloud auth application-default login
```

### 4. How to call your endpoint
To start the API server,
```bash
uvicorn app.main:app --reload
```
Open local browser:
[http://localhost:8000/docs](http://localhost:8000/docs)
For the documentation

```python
requests.post("http://localhost:8000/extract/{name}")
```
Writes to a new file in raw/{name}/ where name = {"permits", "licenses", "scrape"}. extract/licenses will additionally  write to two intermediate files. Instead of extract/scrape, the endpoints is actually "/websites/scrape", which writes to raw/websites/ as well as intermediate/website_status/

Files are formatted as <stage>/<name>/YYYY_MM_DD_HH_MM_SSZ.json.

---

## Remote Deployment
Install gcloud from the link below and login:
[https://docs.cloud.google.com/sdk/docs/install-sdk](https://docs.cloud.google.com/sdk/docs/install-sdk)
```bash
gcloud auth login
```

Fill in all #TODO's in config.sh (API_DIR, WEB_DIR, and JOBS), then run the following command:

```bash
./gcp_script.sh all
```

This runs as a service account with no key file. It deploys the API, creates and runs the scheduler jobs, then deploys the dashboard and prints the URLs.
Instead of all, can also use "init", "api", "scheduler", "web", and "urls" for individual steps.

---
## Repository Structure
```
nyc-contractor-lead-scoring/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── routers/
│       ├── __init__.py
│       ├── licenses.py
│       ├── permits.py
│       └── websites.py
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
│       └── scrape.py
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