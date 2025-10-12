import os
BASE_URL = "https://blog.google/technology/health/"
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "trusty-frame-474816-m0")
BIGQUERY_DATASET = "biomind_data"
TABLE_NAME = "google_health_posts"
