import os

DRUGBANK_API_KEY = os.getenv("DRUGBANK_API_KEY", "")
QUERY = "aspirin"
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "trusty-frame-474816-m0")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "biomind_data")
TABLE_NAME = "drugbank_entries"
