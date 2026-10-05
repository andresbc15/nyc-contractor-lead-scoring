# scoring-contractors-b2b-payments
Which New York City trade contractors look like high-value leads for a B2B payments platform, and how do their job frequency and cost vary by trade and company size?

## Team Members

| Name | GitHubID | Role / Focus |
| --- | --- | --- |
| Nathan Gong | nathan-gong9 | Fastapi implementation, .env, contract review, GCS folder structure |
| Yash Tiwari | yshtiwa | NYC API permits extractor, historical backfill |
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
| 3 | Contractor Websites (domains taken from emails + names in source 2) | Scraped | Services offered + Payment methods | Continuous | `robots.txt` checked per domain |

The App Token required to access sources 1 and 2 should be held in the DOB_APP_TOKEN variable in the .env file

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

### 2. Configure environment variables
Copy the example file and fill in your own values:

```bash
cp .env_template .env
```

| Variable | Description | Example |
| --- | --- | --- |
| `GCP_PROJECT_ID` | ID of the prerequisite GCP project | `nyc-contractor-lead-scoring` |
| `GCP_BUCKET_NAME` | Name of the required bucket inside the GCP project | `nyc-contractor-leads-table-data` |
| `GCP_SERVICE_ACCOUNT_KEY` | Absolute path to your service account JSON | `/Users/you/.ssh/key.json` |
| `DOB_APP_TOKEN` | Free App Token for the NYC Open Data website | `Tl2qvgkiP1w7g9yaBCvtz2KPd` |

### 3. How to call your endpoint
To start the API server,
```bash
uvicorn app.main:app --reload
```

```python
requests.post("http://localhost:8000/extract/permits")
```
Writes to a new .json in raw/permits/

---
## Repository Structure
```
.
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── routers/
│       ├── __init__.py
│       ├── permits.py
│       ├── licenses.py
│       └── enrich.py
├── pipeline/
│   ├── __init__.py
│   ├── config.py
│   ├── socrata.py
│   ├── storage.py
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── permits.py
│   │   ├── licenses.py
│   │   └── websites.py
│   ├── extract/
│   │   ├── __init__.py
│   │   ├── permits.py
│   │   ├── licenses.py
│   │   └── websites.py
│   └── transform/
│       ├── __init__.py
│       └── build.py
├── dashboard/
│   └── app.py
├── .env_template
├── requirements.txt
└── README.md
```
