import os

def get_config(key):
    """Retrieve configuration value from environment or defaults."""
    default_config = {
        "PROJECT_ID": os.getenv("GCP_PROJECT_ID", "trusty-frame-474816-m0"),
        "BIGQUERY_DATASET": os.getenv("BIGQUERY_DATASET", "biomind_data")
    }
    return default_config.get(key)
