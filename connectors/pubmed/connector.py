import logging
from Bio import Entrez
from google.cloud import bigquery
import connectors.pubmed.config as config
import time

def fetch_pubmed_data_realtime(query, max_results=10):
    """
    Fetch PubMed articles in real-time based on query.
    Returns list of articles without storing in BigQuery.
    """
    if not config.ENABLE_PUBMED:
        logging.info("PubMed connector is disabled, skipping PubMed data fetch")
        return []
    
    logging.info(f"Fetching PubMed data in real-time for query: {query}")
    Entrez.email = config.PUBMED_EMAIL
    
    try:
        # Search PubMed for the specific query
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        pmids = record.get("IdList", [])
        time.sleep(0.1)  # Rate limiting
    except Exception as e:
        logging.error(f"PubMed search failed: {e}")
        return []

    if not pmids:
        logging.info("No PubMed IDs found for query. Trying keywordized fallback search in Title/Abstract...")
        # Simple keywordization fallback for natural language queries
        import re
        text = query.lower()
        # Keep words with letters/numbers and basic hyphens
        tokens = re.findall(r"[a-z0-9][a-z0-9\-]+", text)
        stop = {
            'the','a','an','and','or','on','in','of','to','for','with','by','about','latest','research','study','studies','effects','effect','impact','what','are','is','how'
        }
        keywords = [t for t in tokens if t not in stop][:8]
        # If we still have nothing, bail out early
        if not keywords:
            return []
        # Build Title/Abstract query
        ta_terms = [f'"{kw}"[Title/Abstract]' if '-' in kw else f'{kw}[Title/Abstract]' for kw in keywords]
        fallback_term = ' OR '.join(ta_terms)
        try:
            handle = Entrez.esearch(db="pubmed", term=fallback_term, retmax=max_results)
            record = Entrez.read(handle)
            pmids = record.get("IdList", [])
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"PubMed fallback search failed: {e}")
            return []
        if not pmids:
            logging.info("Fallback PubMed search also returned 0 IDs.")
            return []

    articles = []
    for pmid in pmids:
        try:
            handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            rec = Entrez.read(handle)
            article = rec["PubmedArticle"][0]["MedlineCitation"]["Article"]
            title = article.get("ArticleTitle", "")
            abstract_list = article.get("Abstract", {}).get("AbstractText", [])
            abstract = " ".join(abstract_list) if abstract_list else ""
            
            articles.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "source": "pubmed_articles",
                "search_score": 1.0  # High relevance for direct query match
            })
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            logging.error(f"Failed to fetch PubMed article {pmid}: {e}")

    logging.info(f"Fetched {len(articles)} PubMed articles in real-time")
    return articles

def run_pubmed_connector():
    """Legacy function - Fetch articles from PubMed and load into BigQuery."""
    logging.info("Starting PubMed connector (batch mode)")
    Entrez.email = config.PUBMED_EMAIL
    try:
        # Search PubMed for query
        handle = Entrez.esearch(db="pubmed", term=config.QUERY, retmax=config.MAX_RESULTS)
        record = Entrez.read(handle)
        pmids = record.get("IdList", [])
    except Exception as e:
        logging.error(f"PubMed search failed: {e}")
        return

    if not pmids:
        logging.info("No PubMed IDs found for query.")
        return

    bq_client = bigquery.Client(project=config.PROJECT_ID)
    dataset_ref = bigquery.DatasetReference(config.PROJECT_ID, config.BIGQUERY_DATASET)
    # Create dataset if not exists
    try:
        bq_client.create_dataset(dataset_ref, exists_ok=True)
    except Exception as e:
        logging.error(f"Failed to create BigQuery dataset: {e}")

    table_ref = f"{config.PROJECT_ID}.{config.BIGQUERY_DATASET}.{config.TABLE_NAME}"

    rows_to_insert = []
    for pmid in pmids:
        try:
            handle = Entrez.efetch(db="pubmed", id=pmid, retmode="xml")
            rec = Entrez.read(handle)
            article = rec["PubmedArticle"][0]["MedlineCitation"]["Article"]
            title = article.get("ArticleTitle", "")
            abstract_list = article.get("Abstract", {}).get("AbstractText", [])
            abstract = " ".join(abstract_list) if abstract_list else ""
            rows_to_insert.append({
                "pmid": pmid,
                "title": title,
                "abstract": abstract
            })
        except Exception as e:
            logging.error(f"Failed to fetch PubMed article {pmid}: {e}")

    if rows_to_insert:
        schema = [
            bigquery.SchemaField("pmid", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("abstract", "STRING"),
        ]
        try:
            table = bigquery.Table(table_ref, schema=schema)
            bq_client.create_table(table, exists_ok=True)
        except Exception as e:
            logging.error(f"Failed to create BigQuery table: {e}")

        errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            logging.error(f"Errors inserting rows into BigQuery: {errors}")
        else:
            logging.info(f"Inserted {len(rows_to_insert)} rows into {config.TABLE_NAME}.")
