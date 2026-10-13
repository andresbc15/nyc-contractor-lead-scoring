# Transform part of the project!! (ROLE E)
# Cleaning, license normalization,
# joining all three sources, aggregates by trade and company size

import pandas as pd

# permit codes -> registry name because the join uses type and number
# NOTE: PE/RA/PR are left out because they had no matching DOB license category
TYPE_MAP = { "GC": "GENERAL CONTRACTOR", "P": 
            "MASTER PLUMBER", "F": "FIRE SUPPRESSION CONTRACTOR",
            "R": "RIGGER", "S": "SIGN HANGER", "O": "OIL BURNER INSTALLER", }


SIZE_BINS = [0, 5, 39, 249, float("inf")]
SIZE_LABELS = ["Small", "Mid", "Large", "Very large"]

def clean_permits(permits):
    """Fix types, drop duplicates, handle missing job costs."""
    data = permits.copy()
    data = data.drop_duplicates()
    data["job_cost"] = pd.to_numeric(data["estimated_job_costs"], errors="coerce")
    # costs under $100 aren't real job costs: there is spike of token $1 entries, treating them as not recorded.
    data.loc[data["job_cost"] < 100, "job_cost"] = None
    data["cost_outlier"] = data["job_cost"] > 100_000_000 
    data["issued_date"] = pd.to_datetime(data["issued_date"], errors="coerce")
    has_permit = data["work_permit"].notna()
    latest = (data[has_permit]
        .sort_values("issued_date", na_position="first")
        .drop_duplicates("work_permit", keep="last")
    )
    data = pd.concat([latest, data[~has_permit]], ignore_index=True)
    # standardizing borough as it appears in two capitalizations ("Manhattan" / "MANHATTAN")
    data["borough"] = data["borough"].str.strip().str.title()
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

# helper function
def summarize(data, by):
    """Permits, contractors and job cost for any grouping."""
    return data.groupby(by, observed=True).agg(
        n_permits=("work_permit", "size"),
        n_contractors=("contractor_id", "nunique"),
        median_job_cost=("job_cost", "median"),
        total_job_cost=("cost_for_totals", "sum"),
    ).reset_index()

def aggregate(joined):
    """Build summaries by trade and company size for the dashboard."""
    data = joined.copy()
    # one ID per contractor: license type + number (note: numbers repeat across types)
    data["contractor_id"] = data["permittee_s_license_type"] + "-" + data["lic_norm"].astype(str)

    # PE/RA/PR are engineers/architects who file permits, not contractors
    is_contractor = data["license_type_full"].notna()
    data.loc[~is_contractor, "contractor_id"] = None

    # totals leave out flagged outliers so a few typos can't dominate them
    data["cost_for_totals"] = data["job_cost"].where(~data["cost_outlier"])
    data["month"] = data["issued_date"].dt.to_period("M").dt.to_timestamp()

    # Contractor summary: one row per contractor
    contractors = data[is_contractor].groupby("contractor_id").agg(
        license_type=("permittee_s_license_type", "first"),
        business_name=("business_name", "first"),
        license_status=("license_status", "first"),
        business_email=("business_email", "first"),
        business_phone=("business_phone_number", "first"),
        n_permits=("work_permit", "size"),
        median_job_cost=("job_cost", "median"),
        total_job_cost=("cost_for_totals", "sum"),
        first_permit=("issued_date", "min"),
        last_permit=("issued_date", "max"),
        main_work_type=("work_type", lambda s: s.mode().iat[0] if not s.mode().empty else None),
    ).reset_index()
    contractors["size_tier"] = pd.cut(contractors["n_permits"], bins=SIZE_BINS, labels=SIZE_LABELS)

    # giving every permit its contractor's size tier, for the trade x size table
    data = data.merge(contractors[["contractor_id", "size_tier"]], on="contractor_id", how="left")

    return {
        "contractors": contractors,
        "by_trade": summarize(data, "work_type"),
        "by_trade_size": summarize(data, ["work_type", "size_tier"]),
        "monthly": summarize(data, ["month", "work_type"]),
        "by_borough": summarize(data, "borough"),
    }

if __name__ == "__main__":
    print("Transform skeleton: functions have not been written yet :(")
