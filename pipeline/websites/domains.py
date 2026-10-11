import json
import re
from collections import Counter

from free_email_domains import whitelist
from google.cloud import storage

from pipeline.config import GCP_BUCKET_NAME, GCP_PROJECT_ID

# app/routers/licenses.py uploads to raw/dob_licenses/<YYYY-MM-DD>/dob_licenses.json
LICENSES_PREFIX = "raw/dob_licenses/"
LICENSES_FILE = "dob_licenses.json"
TARGET_COLUMNS = [
    "license_type",
    "license_number",
    "license_status",
    "business_name",
    "business_email",
]
# Prompted Claude Opus 5.5 "provide regex for valid email address"
EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$"
PERMIT_LICENSE_TYPES = {
    "GENERAL CONTRACTOR",
    "MASTER PLUMBER",
    "FIRE SUPPRESSION CONTRACTOR",
    "RIGGER",
    "SIGN HANGER",
    "OIL BURNER INSTALLER",
}


# TO DO: move to pipeline/storage.py once it exists
def get_bucket():
    # No key file: uses Application Default Credentials (gcloud login locally)
    client = storage.Client(project=GCP_PROJECT_ID)
    return client.bucket(GCP_BUCKET_NAME)


# TEMPORARY: move to pipeline/storage.py once it exists
def upload_json_to_gcp(bucket, data, blob_name):
    bucket.blob(blob_name).upload_from_string(
        json.dumps(data), content_type="application/json"
    )
    return blob_name


def latest_licenses_file_name(bucket):
    file_names = [
        blob.name
        for blob in bucket.list_blobs(prefix=LICENSES_PREFIX)
        if blob.name.endswith(f"/{LICENSES_FILE}")
    ]
    if not file_names:
        raise FileNotFoundError(
            f"No files found in {GCP_BUCKET_NAME}/{LICENSES_PREFIX}"
        )
    return max(file_names)


def load_licenses():
    bucket = get_bucket()
    file_name = latest_licenses_file_name(bucket)
    data = bucket.blob(file_name).download_as_bytes()
    # Return touple for logging purposes
    return file_name, json.loads(data)


def extract_licenses(data):
    extracted_data = []
    for row in data:
        extracted_data.append({key: row[key] for key in TARGET_COLUMNS})
    return extracted_data


def filter_license_types(data):
    filtered_data = []
    for row in data:
        if row["license_type"] not in PERMIT_LICENSE_TYPES:
            continue
        if row["license_status"] != "ACTIVE":
            continue
        filtered_data.append(row)
    return filtered_data


def deduplicated_licences(data):
    licenses = set()
    deduped_data = []
    for row in data:
        key = (row["license_type"], row["license_number"])
        if key in licenses:
            continue
        licenses.add(key)
        deduped_data.append(row)
    return deduped_data


def is_valid_email(email):
    return re.fullmatch(EMAIL_REGEX, email) is not None


def is_business_domain(email):
    domain = email.split("@")[1]
    return domain not in whitelist


def extract_business_domain(email):
    # Check if missing
    if not email or email == "":
        return None, "Missing"

    # Clean email
    normalized_email = email.strip().lower()

    # Check if it is a valid email
    if not is_valid_email(email):
        return None, "Invalid"

    # Check if it is a business domain
    if is_business_domain(normalized_email):
        return normalized_email.split("@")[1], "Valid"
    return None, "Personal"


def map_licenses_to_domains(deduped_data):
    result = []
    for row in deduped_data:
        domain, status = extract_business_domain(row["business_email"])
        result.append(
            {
                "license_type": row["license_type"],
                "license_number": row["license_number"],
                "domain": domain,
                "email_status": status,
            }
        )
    return result


def select_scrape_targets(license_domains):
    # Create a dictionary of counts for each domain
    domain_counts = Counter(row["domain"] for row in license_domains if row["domain"])
    return [
        {"domain": domain, "n_licenses": n_licenses}
        for domain, n_licenses in domain_counts.items()
    ]


def run():

    file_name, data = load_licenses()

    print(f"Loaded licenses from {file_name}")

    reduced_data = extract_licenses(data)

    filtered_data = filter_license_types(reduced_data)

    deduped_data = deduplicated_licences(filtered_data)

    data_with_domains = map_licenses_to_domains(deduped_data)

    scrape_targets = select_scrape_targets(data_with_domains)

    # Make blob names
    source_date = file_name.split("/")[2]
    data_with_domains_blob_name = (
        f"intermediate/licenses_to_domains/{source_date}/licenses_to_domains.json"
    )
    scrape_targets_blob_name = (
        f"intermediate/website_domains/{source_date}/website_domains.json"
    )

    # TEMPORARY: should busing functions from storage.py
    bucket = get_bucket()

    # Upload licenses with domains
    upload_json_to_gcp(bucket, data_with_domains, data_with_domains_blob_name)

    # Upload scraping targets
    upload_json_to_gcp(bucket, scrape_targets, scrape_targets_blob_name)

    return {
        "source": file_name,
        "licenses": len(data_with_domains),
        "scrape_targets": len(scrape_targets),
        "uploaded": [data_with_domains_blob_name, scrape_targets_blob_name],
    }


if __name__ == "__main__":
    print(run())
