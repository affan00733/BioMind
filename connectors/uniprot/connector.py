import logging
import requests
import csv
from io import StringIO
from google.cloud import bigquery
import connectors.uniprot.config as config
import time

def fetch_uniprot_data_realtime(query, max_results=10):
    """
    Fetch UniProt protein data in real-time based on query.
    Returns list of proteins without storing in BigQuery.
    """
    if not config.ENABLE_UNIPROT:
        logging.info("UniProt connector is disabled, skipping UniProt data fetch")
        return []
    
    logging.info(f"Fetching UniProt data in real-time for query: {query}")
    
    params = {
        "query": query,
        "format": "tsv",
        "fields": "accession,protein_name,genes,sequence",
        "size": max_results
    }
    
    try:
        response = requests.get(config.UNIPROT_BASE_URL, params=params)
        response.raise_for_status()
        text = response.text.strip()
        time.sleep(0.1)  # Rate limiting
    except Exception as e:
        logging.error(f"UniProt API request failed: {e}")
        return []

    if not text:
        logging.info("No UniProt data retrieved.")
        return []

    reader = csv.DictReader(StringIO(text), delimiter='\t')
    proteins = []
    for row in reader:
        proteins.append({
            "uniprot_id": row.get("Entry", ""),
            "accession": row.get("Entry", ""),
            "protein_name": row.get("Protein names", ""),
            "genes": row.get("Gene Names", ""),
            "sequence": row.get("Sequence", ""),
            "source": "uniprot_records",
            "search_score": 1.0  # High relevance for direct query match
        })

    logging.info(f"Fetched {len(proteins)} UniProt proteins in real-time")
    return proteins

def run_uniprot_connector():
    """Legacy function - Fetch protein entries from UniProt and load into BigQuery."""
    logging.info("Starting UniProt connector (batch mode)")
    params = {
        "query": config.QUERY,
        "format": "tsv",
        "fields": "accession,protein_name,genes,sequence",
        "size": config.MAX_RESULTS
    }
    try:
        response = requests.get(config.UNIPROT_BASE_URL, params=params)
        response.raise_for_status()
        text = response.text.strip()
    except Exception as e:
        logging.error(f"UniProt API request failed: {e}")
        return

    if not text:
        logging.info("No UniProt data retrieved.")
        return

    reader = csv.DictReader(StringIO(text), delimiter='\t')
    rows_to_insert = []
    for row in reader:
        rows_to_insert.append({
            "uniprot_id": row.get("Entry", ""),
            "accession": row.get("Entry", ""),
            "protein_name": row.get("Protein names", ""),
            "genes": row.get("Gene Names", ""),
            "sequence": row.get("Sequence", "")
        })

    bq_client = bigquery.Client(project=config.PROJECT_ID)
    dataset_ref = bigquery.DatasetReference(config.PROJECT_ID, config.BIGQUERY_DATASET)
    try:
        bq_client.create_dataset(dataset_ref, exists_ok=True)
    except Exception as e:
        logging.error(f"Failed to create BigQuery dataset: {e}")

    table_ref = f"{config.PROJECT_ID}.{config.BIGQUERY_DATASET}.{config.TABLE_NAME}"
    schema = [
        bigquery.SchemaField("uniprot_id", "STRING"),
        bigquery.SchemaField("accession", "STRING"),
        bigquery.SchemaField("protein_name", "STRING"),
        bigquery.SchemaField("genes", "STRING"),
        bigquery.SchemaField("sequence", "STRING"),
    ]
    try:
        table = bigquery.Table(table_ref, schema=schema)
        bq_client.create_table(table, exists_ok=True)
    except Exception as e:
        logging.error(f"Failed to create BigQuery table: {e}")

    if rows_to_insert:
        errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            logging.error(f"Errors inserting rows into BigQuery: {errors}")
        else:
            logging.info(f"Inserted {len(rows_to_insert)} rows into {config.TABLE_NAME}.")
