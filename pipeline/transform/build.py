# Transform part of the project!! (ROLE E)
# Cleaning, license normalization,
# joining all three sources, aggregates by trade and company size

import pandas as pd

# permit codes -> registry name because the join uses type and number
# NOTE: PE/RA/PR are left out because they had no matching DOB license category
TYPE_MAP = { "GC": "GENERAL CONTRACTOR", "P": 
            "MASTER PLUMBER", "F": "FIRE SUPPRESSION CONTRACTOR",
            "R": "RIGGER", "S": "SIGN HANGER", "O": "OIL BURNER INSTALLER", }

# 
def clean_permits(permits):
    """Fix types, drop duplicates, handle missing job costs."""
    data = permits.copy()
    data = data.drop_duplicates()
    data["job_cost"] = pd.to_numeric(data["estimated_job_costs"], errors="coerce")
    data.loc[data["job_cost"] <= 0, "job_cost"] = None
    data["cost_outlier"] = data["job_cost"] > 100_000_000
    data["issued_date"] = pd.to_datetime(data["issued_date"], errors="coerce")
    has_permit = data["work_permit"].notna()
    latest = (data[has_permit]
        .sort_values("issued_date", na_position="first")
        .drop_duplicates("work_permit", keep="last")
    )
    data = pd.concat([latest, data[~has_permit]], ignore_index=True)
    return data

def license_norm(license_number):
    """Put license numbers in one format so permits and licenses can be joined."""
    if pd.isna(license_number):
        return None
    
    cleaned = str(license_number).strip().lstrip("0")
    if cleaned == "":
        return None
    return cleaned

def joint_resources(permits, licenses):
    """Left join permits to licenses on license type and number, so every permit is kept."""
    p = permits.copy()
    p["lic_norm"] = p["applicant_license"].map(license_norm)
    p["license_type_full"] = p["permittee_s_license_type"].map(TYPE_MAP)

    l = licenses.copy()
    l["lic_norm"] = l["license_number"].map(license_norm)
    l = l.drop_duplicates(["license_type", "lic_norm"])

    joined = p.merge(
        l,
        left_on=["license_type_full", "lic_norm"],
        right_on=["license_type", "lic_norm"],
        how="left",
        suffixes=("", "_license"),
    )
    return joined

def aggregate(joined):
    """Build summaries by trade and company size for the dashboard."""
    raise NotImplementedError

def run(dt: str) -> str:
    """Join one day's raw permits and licenses and save the result to processed/."""
    # 1. Load raw permits and licenses with storage.read_raw() into DataFrames
    # 2. Clean and normalize the license number in both
    # 3. Left join permits to licenses on license number
    # 4. Save with storage.write_processed() and return the path
    raise NotImplementedError

if __name__ == "__main__":
    print("Transform skeleton: functions have not been written yet :(")
