from __future__ import annotations

import os
import json
from typing import List, Dict, Iterable
import datetime

from google.cloud import bigquery
from langchain_google_vertexai import VertexAIEmbeddings

DATASET = os.getenv("BQ_DATASET", "biomind_corpus")
CHUNKS_TABLE = os.getenv("BQ_CHUNKS_TABLE", "chunks")
OUTPUT_GCS = os.getenv("DATAPOINTS_GCS", "")  # gs://bucket/prefix/datapoints.jsonl
PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
EMBED_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-005")


def ensure_needs_embedding_schema(client: bigquery.Client, dataset: str = DATASET, table: str = CHUNKS_TABLE):
    """Ensure the chunks table has needs_embedding (BOOL) and inserted_at (TIMESTAMP) columns.
    If columns are missing, add them and set existing rows to needs_embedding = FALSE.
    """
    table_id = f"{client.project}.{dataset}.{table}"
    try:
        tbl = client.get_table(table_id)
    except Exception:
        # Table missing; nothing to ensure here.
        return
    schema_names = {f.name for f in tbl.schema}
    updated = False
    new_fields = []
    if 'needs_embedding' not in schema_names:
        new_fields.append(bigquery.SchemaField('needs_embedding', 'BOOL'))
        updated = True
    if 'inserted_at' not in schema_names:
        new_fields.append(bigquery.SchemaField('inserted_at', 'TIMESTAMP'))
        updated = True
    if updated:
        tbl.schema = list(tbl.schema) + new_fields
        client.update_table(tbl, ['schema'])
        # Set existing rows to needs_embedding = FALSE to avoid re-embedding old data
        try:
            client.query(f"UPDATE `{table_id}` SET needs_embedding = FALSE WHERE TRUE").result()
        except Exception:
            pass


def fetch_chunks_needing_embedding(client: bigquery.Client, limit: int = 2000) -> List[Dict]:
    """Fetch a batch of chunks where needs_embedding = TRUE, ordered by inserted_at asc."""
    table_ref = f"{client.project}.{DATASET}.{CHUNKS_TABLE}"
    sql = f"""
    SELECT id, paper_id, text, url
    FROM `{table_ref}`
    WHERE needs_embedding = TRUE
    ORDER BY COALESCE(inserted_at, TIMESTAMP('1970-01-01')) ASC
    LIMIT @limit
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("limit", "INT64", limit)]
    )
    rows = client.query(sql, job_config=job_config).result()
    out = []
    for r in rows:
        out.append({"id": r.id, "paper_id": r.paper_id, "text": r.text, "url": getattr(r, "url", "") or ""})
    return out


def mark_chunks_embedded(client: bigquery.Client, ids: List[str]):
    if not ids:
        return
    table_ref = f"{client.project}.{DATASET}.{CHUNKS_TABLE}"
    # Update in batches to avoid long SQL
    for i in range(0, len(ids), 500):
        batch = ids[i : i + 500]
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("ids", "ARRAY<STRING>", batch)]
        )
        sql = f"""
        UPDATE `{table_ref}`
        SET needs_embedding = FALSE
        WHERE id IN UNNEST(@ids)
        """
        client.query(sql, job_config=job_config).result()


def write_jsonl_to_gcs(records: List[Dict], gcs_uri: str) -> None:
    from google.cloud import storage
    b, _, p = gcs_uri[5:].partition("/")
    bucket = storage.Client().bucket(b)
    # If a folder path is provided, append filename
    if p.endswith("/") or p == "":
        p = p + "datapoints.jsonl"
    blob = bucket.blob(p)
    lines = [json.dumps(r) for r in records]
    blob.upload_from_string("\n".join(lines), content_type="application/json")


def write_jsonl_to_gcs_append(records: List[Dict], gcs_uri: str) -> None:
    """Write records to a GCS object (overwrite). For append behavior we produce numbered parts.
    This helper kept for compatibility; prefer writing part files externally."""
    write_jsonl_to_gcs(records, gcs_uri)


def main(batch_size: int = 256, part_size: int = 2000):
    """Stream all chunks, embed in batches, and write multiple datapoints JSONL part files to GCS.

    part_size: number of datapoints per GCS part file.
    """
    if not OUTPUT_GCS or not OUTPUT_GCS.startswith("gs://"):
        print('Set DATAPOINTS_GCS to a gs:// path to write datapoints')
        return

    embedder = VertexAIEmbeddings(project=PROJECT, location=LOCATION, model_name=EMBED_MODEL)

    client = bigquery.Client(project=PROJECT) if PROJECT else bigquery.Client()
    # Ensure the chunks table has the needs_embedding schema so we can run incremental updates
    ensure_needs_embedding_schema(client, DATASET, CHUNKS_TABLE)

    part_index = 0
    part_records: List[Dict] = []
    batch: List[Dict] = []
    total = 0

    # Repeatedly fetch batches of chunks that need embedding and process until none remain.
    while True:
        rows = fetch_chunks_needing_embedding(client, limit=2000)
        if not rows:
            break

        for c in rows:
            batch.append(c)
            if len(batch) >= batch_size:
                texts = [b["text"] for b in batch]
                vecs = embedder.embed_documents(texts)
                for b, v in zip(batch, vecs):
                    part_records.append({
                        "id": b["id"],
                        "embedding": v,
                        "restricts": {"paper_id": b["paper_id"]},
                        "crowding_tag": "paper_chunk",
                        "attributes": {"url": b.get("url", "")},
                    })
                batch = []

            # flush part if reached part_size
            if len(part_records) >= part_size:
                part_index += 1
                out_uri = OUTPUT_GCS.rstrip('/') + f'.part{part_index:04d}.jsonl'
                write_jsonl_to_gcs(part_records, out_uri)
                # mark the written chunk ids as embedded
                mark_chunks_embedded(client, [r["id"] for r in part_records])
                print(f'Wrote part {part_index} with {len(part_records)} datapoints to {out_uri}')
                total += len(part_records)
                part_records = []

    # final flush for any remaining batch
    if batch:
        texts = [b["text"] for b in batch]
        vecs = embedder.embed_documents(texts)
        for b, v in zip(batch, vecs):
            part_records.append({
                "id": b["id"],
                "embedding": v,
                "restricts": {"paper_id": b["paper_id"]},
                "crowding_tag": "paper_chunk",
                "attributes": {"url": b.get("url", "")},
            })
        batch = []

    if part_records:
        part_index += 1
        out_uri = OUTPUT_GCS.rstrip('/') + f'.part{part_index:04d}.jsonl'
        write_jsonl_to_gcs(part_records, out_uri)
        # mark the written chunk ids as embedded
        mark_chunks_embedded(client, [r["id"] for r in part_records])
        print(f'Wrote final part {part_index} with {len(part_records)} datapoints to {out_uri}')
        total += len(part_records)

    print({"datapoints": total, "parts": part_index, "output_prefix": OUTPUT_GCS})


if __name__ == "__main__":
    main()
