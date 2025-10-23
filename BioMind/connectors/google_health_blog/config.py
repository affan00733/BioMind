import os

# Enable/Disable flag for Google Health Blog connector
ENABLE_GOOGLE_HEALTH_BLOG = os.getenv("ENABLE_GOOGLE_HEALTH_BLOG", "false").lower() == "true"

BASE_URL = "https://blog.google/technology/health/"
PROJECT_ID = os.getenv("GCP_PROJECT_ID", "trusty-frame-474816-m0")
BIGQUERY_DATASET = "biomind_data"
TABLE_NAME = "google_health_posts"
