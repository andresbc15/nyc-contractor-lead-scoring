from datetime import datetime
from pydantic import BaseModel

class PermitRecord(BaseModel):
    # Row from DOB Now: Build - Approved Permits "https://data.cityofnewyork.us/resource/rbx6-tga4.json"
    
    # Standard Info -  always present in every row
    applicant_license: str  #join key to license_number in the licenses.py!!!
    work_type: str
    permit_status: str
    job_filing_number: str | None = None  
    work_permit: str | None = None  
    sequence_number: str | None = None
    filing_reason: str | None = None

    # Location
    house_no: str | None = None
    street_name: str | None = None
    borough: str | None = None
    zip_code: str | None = None
    lot: str | None = None
    block: str | None = None
    bin: str | None = None
    c_b_no: str | None = None
    apt_condo_no_s: str | None = None
    work_on_floor: str | None = None

    # Contractor Details
    permittee_s_license_type: str | None = None
    applicant_first_name: str | None = None
    applicant_middle_name: str | None = None
    applicant_last_name: str | None = None
    applicant_business_name: str | None = None
    applicant_business_address: str | None = None

    # Filing representatives
    filing_representative_first_name: str | None = None
    filing_representative_middle_initial: str | None = None
    filing_representative_last_name: str | None = None
    filing_representative_business_name: str | None = None

    # Dates
    approved_date: datetime | None = None
    issued_date: datetime | None = None  
    expired_date: datetime | None = None

    # Job
    job_description: str | None = None
    estimated_job_costs: str | None = None  # The data arrives as text like "100", convert to int during transform

    # Owner
    owner_business_name: str | None = None
    owner_name: str | None = None
    owner_street_address: str | None = None
    owner_city: str | None = None
    owner_state: str | None = None
    owner_zip_code: str | None = None
    tracking_number: str | None = None

    # Geography
    latitude: float | None = None
    longitude: float | None = None
    community_board: str | None = None  
    council_district: str | None = None
    bbl: str | None = None
    census_tract: str | None = None
    nta: str | None = None
