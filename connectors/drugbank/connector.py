import logging
import requests
from xml.etree import ElementTree
from google.cloud import bigquery
import connectors.drugbank.config as config
import time

def fetch_drugbank_data_realtime(query, max_results=10):
    """
    Fetch DrugBank drug data in real-time based on query.
    Returns list of drugs without storing in BigQuery.
    """
    if not config.ENABLE_DRUGBANK:
        logging.info("DrugBank connector is disabled, skipping DrugBank data fetch")
        return []
    
    logging.info(f"Fetching DrugBank data in real-time for query: {query}")
    
    if not config.DRUGBANK_API_KEY:
        logging.warning("No DrugBank API key provided. Using mock data.")
        # Return mock data for demonstration
        return [{
            "drug_id": f"DB{mock_id:05d}",
            "name": f"Drug related to {query}",
            "description": f"Drug description for {query}",
            "indication": f"Indication related to {query}",
            "source": "drugbank_entries",
            "search_score": 0.8
        } for mock_id in range(1, min(max_results + 1, 6))]

    base_url = "https://go.drugbank.com"
    headers = {"Authorization": f"Bearer {config.DRUGBANK_API_KEY}"}
    
    try:
        response = requests.get(f"{base_url}/unearth/q?searcher=drugs&query={query}&limit={max_results}", headers=headers)
        response.raise_for_status()
        xml_text = response.text
        root = ElementTree.fromstring(xml_text)
        time.sleep(0.1)  # Rate limiting
    except Exception as e:
        logging.error(f"DrugBank API request failed: {e}")
        return []

    drugs = []
    for drug in root.findall(".//drug"):
        # Extract primary drugbank-id
        drug_ids = [e.text for e in drug.findall("drugbank-id") if e.get("primary") == "true"]
        drug_id = drug_ids[0] if drug_ids else ""
        name = drug.findtext("name") or ""
        description = drug.findtext("description") or ""
        indication = drug.findtext("indication") or ""
        
        drugs.append({
            "drug_id": drug_id,
            "name": name,
            "description": description,
            "indication": indication,
            "source": "drugbank_entries",
            "search_score": 1.0  # High relevance for direct query match
        })

    logging.info(f"Fetched {len(drugs)} DrugBank drugs in real-time")
    return drugs

def run_drugbank_connector():
    """Legacy function - Fetch drug entries from DrugBank and load into BigQuery."""
    logging.info("Starting DrugBank connector (batch mode)")
    if not config.DRUGBANK_API_KEY:
        logging.warning("No DrugBank API key provided. Skipping DrugBank connector.")
        return

    base_url = "https://go.drugbank.com"
    headers = {"Authorization": f"Bearer {config.DRUGBANK_API_KEY}"}
    try:
        response = requests.get(f"{base_url}/unearth/q?searcher=drugs&query={config.QUERY}", headers=headers)
        response.raise_for_status()
        xml_text = response.text
        root = ElementTree.fromstring(xml_text)
    except Exception as e:
        logging.error(f"DrugBank API request failed: {e}")
        return

    rows_to_insert = []
    for drug in root.findall(".//drug"):
        # Extract primary drugbank-id
        drug_ids = [e.text for e in drug.findall("drugbank-id") if e.get("primary") == "true"]
        drug_id = drug_ids[0] if drug_ids else ""
        name = drug.findtext("name") or ""
        description = drug.findtext("description") or ""
        indication = drug.findtext("indication") or ""
        rows_to_insert.append({
            "drug_id": drug_id,
            "name": name,
            "description": description,
            "indication": indication
        })

    if rows_to_insert:
        bq_client = bigquery.Client(project=config.PROJECT_ID)
        dataset_ref = bigquery.DatasetReference(config.PROJECT_ID, config.BIGQUERY_DATASET)
        try:
            bq_client.create_dataset(dataset_ref, exists_ok=True)
        except Exception as e:
            logging.error(f"Failed to create BigQuery dataset: {e}")

        table_ref = f"{config.PROJECT_ID}.{config.BIGQUERY_DATASET}.{config.TABLE_NAME}"
        schema = [
            bigquery.SchemaField("drug_id", "STRING"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("indication", "STRING"),
        ]
        try:
            table = bigquery.Table(table_ref, schema=schema)
            bq_client.create_table(table, exists_ok=True)
        except Exception as e:
            logging.error(f"Failed to create BigQuery table: {e}")

        errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            logging.error(f"Errors inserting DrugBank rows: {errors}")
        else:
            logging.info(f"Inserted {len(rows_to_insert)} rows into {config.TABLE_NAME}.")
