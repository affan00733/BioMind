import os

PUBMED_EMAIL = os.getenv("PUBMED_EMAIL", "your-email@example.com")
QUERY = "cancer immunotherapy"
MAX_RESULTS = 5
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "trusty-frame-474816-m0")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "biomind_data")
TABLE_NAME = "pubmed_articles"
