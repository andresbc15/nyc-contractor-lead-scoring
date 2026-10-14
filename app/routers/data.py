import json
from fastapi import APIRouter, HTTPException
from pipeline import storage

TABLES = {"contractors", "by_trade", "by_trade_size", "monthly", "by_borough"}

router = APIRouter(prefix="/data")

@router.get("/{table}")
def send_table(table: str):
    """
    returns the GCP dataset in json format for the Streamlit dashboard to use
    """
    if table not in TABLES:
        raise HTTPException(status_code=404, detail=f"{table} is not a valid table")

    try:
        df = storage.read_parquet(table)
    except (Exception) as e:
        raise HTTPException(status_code=404, detail=f"{table} is not generated yet")
    table_data = json.loads(df.to_json(orient="records", date_format="iso"))
    return {"table": table, "rows": len(table_data), "data": table_data}