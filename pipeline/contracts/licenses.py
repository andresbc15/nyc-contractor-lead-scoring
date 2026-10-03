from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DobLicenseRow(BaseModel):

    # Ingestion info
    id: str
    version: str
    created_at: datetime
    updated_at: datetime

    # License
    license_sl_no: str
    license_number: str  # join key to permits
    license_type: Optional[str] = None  # null in 2 rows
    license_status: Optional[str] = None  # null in 9 rows; has a few dirty values

    # Licensee
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # Business contact
    business_name: Optional[str] = None
    business_house_number: Optional[str] = None
    business_street_name: Optional[str] = None
    license_business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_zip_code: Optional[str] = None
    business_phone_number: Optional[str] = None
    business_email: Optional[str] = None

    # Geocoded location
    lat: Optional[float] = None
    long: Optional[float] = None
    cb: Optional[str] = None # community board
    cd: Optional[str] = None # council district
    ct: Optional[str] = None # census tract
    bin: Optional[str] = None # building identification number
    bbl: Optional[str] = None # borough-block-lot
    nta: Optional[str] = None # neighborhood tabulation area
