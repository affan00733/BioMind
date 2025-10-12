import logging
from connectors.pubmed.connector import run_pubmed_connector
from connectors.uniprot.connector import run_uniprot_connector
from connectors.drugbank.connector import run_drugbank_connector

def run_all_connectors():
    """Run all data ingestion connectors to BigQuery."""
    logging.info("Starting data ingestion pipeline")
    run_pubmed_connector()
    run_uniprot_connector()
    run_drugbank_connector()
    logging.info("Completed data ingestion pipeline")
