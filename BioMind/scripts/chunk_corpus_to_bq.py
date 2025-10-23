"""Chunk documents from biomind_corpus.corpus into biomind_corpus.chunks.

Usage:
  .venv/bin/python scripts/chunk_corpus_to_bq.py --project trusty-frame-474816-m0 --batch 500

This will:
- Create the chunks table if missing (schema from pipeline/bq_schema.sql)
- Stream corpus rows and split text into chunks (max_chars default 800)
- Insert chunk rows into BQ in batches
"""
from __future__ import annotations

import argparse
import math
import time
from google.cloud import bigquery
from typing import List, Dict


def ensure_chunks_table(client: bigquery.Client, dataset: str = 'biomind_corpus', table: str = 'chunks') -> None:
    table_id = f"{client.project}.{dataset}.{table}"
    try:
        client.get_table(table_id)
        print(f'chunks table {table_id} already exists')
        return
    except Exception:
        print(f'creating table {table_id}')
    schema = [
        bigquery.SchemaField('id', 'STRING'),
        bigquery.SchemaField('paper_id', 'STRING'),
        bigquery.SchemaField('section', 'STRING'),
        bigquery.SchemaField('position', 'INT64'),
        bigquery.SchemaField('text', 'STRING'),
        bigquery.SchemaField('token_count', 'INT64'),
        bigquery.SchemaField('url', 'STRING'),
    ]
    table = bigquery.Table(table_id, schema=schema)
    client.create_table(table)
    print('created chunks table')


def chunk_text(text: str, max_chars: int = 800) -> List[str]:
    if not text:
        return []
    # naive split by sentences when possible, else fixed window
    out: List[str] = []
    cur = ''
    for part in text.split('\n'):
        part = part.strip()
        if not part:
            continue
        if len(cur) + len(part) + 1 <= max_chars:
            cur = (cur + ' ' + part).strip()
        else:
            if cur:
                out.append(cur)
            if len(part) <= max_chars:
                cur = part
            else:
                # long paragraph; split chunk-wise
                for i in range(0, len(part), max_chars):
                    out.append(part[i:i+max_chars])
                cur = ''
    if cur:
        out.append(cur)
    return out


def stream_corpus_rows(client: bigquery.Client, dataset: str = 'biomind_corpus', table: str = 'corpus'):
    sql = f"SELECT id, text, source, url FROM `{client.project}.{dataset}.{table}`"
    job = client.query(sql)
    for row in job.result():
        yield row


def insert_chunk_batch(client: bigquery.Client, rows: List[Dict], dataset: str = 'biomind_corpus', table: str = 'chunks') -> int:
    if not rows:
        return 0
    table_ref = f"{client.project}.{dataset}.{table}"
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        print('Insert errors (first):', errors[:3])
        return 0
    return len(rows)


def main(project: str, batch_size: int = 500, max_chars: int = 800):
    client = bigquery.Client(project=project)
    ensure_chunks_table(client)
    total_chunks = 0
    batch = []
    start = time.time()
    for r in stream_corpus_rows(client):
        doc_id = str(r.id)
        text = r.text or ''
        url = r.url or ''
        chunks = chunk_text(text, max_chars=max_chars)
        for pos, c in enumerate(chunks):
            cid = f"{doc_id}::chunk::{pos}"
            batch.append({
                'id': cid,
                'paper_id': doc_id,
                'section': 'body',
                'position': pos,
                'text': c,
                'token_count': len(c.split()),
                'url': url,
            })
            if len(batch) >= batch_size:
                inserted = insert_chunk_batch(client, batch)
                total_chunks += inserted
                print(f'Inserted batch {inserted} chunks (total {total_chunks})')
                batch = []
    if batch:
        inserted = insert_chunk_batch(client, batch)
        total_chunks += inserted
        print(f'Final inserted {inserted} chunks')
    elapsed = time.time() - start
    print(f'Done: total_chunks={total_chunks} elapsed_s={elapsed:.1f}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--project', required=True)
    p.add_argument('--batch', type=int, default=500)
    p.add_argument('--max-chars', type=int, default=800)
    args = p.parse_args()
    main(args.project, batch_size=args.batch, max_chars=args.max_chars)
