from __future__ import annotations

from typing import List
from google.cloud import bigquery
from utils.config_utils import get_config


def _bq_chunks_available() -> bool:
    """Return True if the configured BQ dataset/table for chunks exists.

    This prevents raising 404 errors when HYBRID_RETRIEVAL is enabled but
    the BigQuery tables haven't been created yet. Safe no-op check.
    """
    try:
        dataset = get_config("BQ_CORPUS_DATASET", "biomind_corpus")
        table = get_config("BQ_CHUNKS_TABLE", "corpus")
        if not (dataset and table):
            return False
        client = bigquery.Client()
        try:
            client.get_dataset(dataset)
        except Exception:
            return False
        try:
            client.get_table(f"{dataset}.{table}")
        except Exception:
            return False
        return True
    except Exception:
        return False


def get_bq_ids_for_query(query: str, limit: int = 50) -> List[str]:
    """Return chunk IDs from BigQuery using SEARCH() lexical query.

    If the dataset/table is not available, returns an empty list (fail-open).
    Requires BQ_CORPUS_DATASET and BQ_CHUNKS_TABLE to be set (or use defaults).
    """
    if not _bq_chunks_available():
        return []

    dataset = get_config("BQ_CORPUS_DATASET", "biomind_corpus")
    table = get_config("BQ_CHUNKS_TABLE", "corpus")

    client = bigquery.Client()
    sql = f"""
    SELECT id
    FROM `{dataset}.{table}`
    WHERE SEARCH(ARRAY[STRUCT('text' AS field, text AS value)], @q).score > 0
    ORDER BY SEARCH(ARRAY[STRUCT('text' AS field, text AS value)], @q).score DESC
    LIMIT {limit}
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("q", "STRING", query)]
    )
    try:
        rows = client.query(sql, job_config=job_config).result()
        return [r.id for r in rows]
    except Exception:
        # If query fails (e.g., permissions or dataset missing), return empty
        return []
