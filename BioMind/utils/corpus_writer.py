from __future__ import annotations

from typing import List, Dict
from utils.config_utils import get_config


def upsert_corpus_rows(rows: List[Dict[str, str]]) -> int:
    """Best-effort insert of corpus rows into BigQuery corpus table.

    Each row must have keys: id, text, source, url.
    Returns number of rows attempted (not guaranteed written).
    Silently no-ops if BQ corpus env is not configured.
    """
    dataset = get_config("BQ_CORPUS_DATASET", "")
    table = get_config("BQ_CORPUS_TABLE", "")
    if not (dataset and table and rows):
        return 0
    try:
        from google.cloud import bigquery  # type: ignore
    except Exception:
        # BigQuery client not available; skip persistence
        return 0
    try:
        client = bigquery.Client()
        table_id = f"{dataset}.{table}"
        # Ensure dataset exists
        try:
            client.get_dataset(dataset)
        except Exception:
            client.create_dataset(dataset)
        # Create table if missing with minimal schema
        try:
            client.get_table(table_id)
        except Exception:
            schema = [
                bigquery.SchemaField("id", "STRING"),
                bigquery.SchemaField("text", "STRING"),
                bigquery.SchemaField("source", "STRING"),
                bigquery.SchemaField("url", "STRING"),
            ]
            client.create_table(bigquery.Table(table_id, schema=schema))
        # Insert rows (streaming insert, may duplicate on repeated fetches)
        _ = client.insert_rows_json(table_id, rows)
        return len(rows)
    except Exception:
        return 0
