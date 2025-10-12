import os

UNIPROT_BASE_URL = "https://rest.uniprot.org/uniprotkb/search"
QUERY = "organism_id:9606"
MAX_RESULTS = 5
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "trusty-frame-474816-m0")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "biomind_data")
TABLE_NAME = "uniprot_records"
