import json
import re
from collections import Counter

from free_email_domains import whitelist
from pipeline import storage

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
        # License numbers are reused across license types
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
    # whitelist is the package's list of free email providers (personal)
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

    file_name, data = storage.read_latest_file("licenses")

    print(f"Loaded licenses from {file_name}")

    reduced_data = extract_licenses(data)

    filtered_data = filter_license_types(reduced_data)

    deduped_data = deduplicated_licences(filtered_data)

    data_with_domains = map_licenses_to_domains(deduped_data)

    scrape_targets = select_scrape_targets(data_with_domains)

    # Upload licenses with domains
    domains_blob = storage.write_data("licenses_to_domains", data_with_domains, stage="intermediate")

    # Upload scraping targets
    scraping_blob = storage.write_data("website_domains", scrape_targets, stage="intermediate")

    return {
        "source": file_name,
        "licenses": len(data_with_domains),
        "scrape_targets": len(scrape_targets),
        "uploaded": [domains_blob, scraping_blob],
    }


if __name__ == "__main__":
    print(run())
