# Transform part of the project!! (ROLE E)
# Cleaning, license normalization,
# joining all three sources, aggregates by trade and company size

def clean_permits():
    """Fix types, drop duplicates, handle missing job costs."""
    raise NotImplementedError

def license_norm():
    """Put license numbers in one format so permits and licenses can be joined."""
    raise NotImplementedError

def joint_resources():
    """Left join permits to licenses on license number, so every permit is kept."""
    raise NotImplementedError

def aggregate():
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
