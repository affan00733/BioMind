"""Parse first N drugs from DrugBank XML and insert into BigQuery corpus table.

Usage:
  .venv/bin/python scripts/upsert_drugbank_to_bq.py --xml '/path/to/full database.xml' --n 200

Requires GOOGLE_APPLICATION_CREDENTIALS or ADC and google-cloud-bigquery installed in the venv.
"""
import argparse
import uuid
from xml.etree import ElementTree as ET
from google.cloud import bigquery
from typing import Iterator, Dict, Set
import time

NS = 'http://www.drugbank.ca'


def stream_drugs(xml_path: str) -> Iterator[Dict]:
    """Stream DrugBank <drug> entries as dicts (memory-light)."""
    it = ET.iterparse(xml_path, events=('end',))
    for ev, el in it:
        if el.tag == f'{{{NS}}}drug':
            dbid = el.findtext(f'./{{{NS}}}drugbank-id')
            # Some entries have multiple drugbank-id elements; prefer those with primary attr if present
            if not dbid:
                ids = el.findall(f'./{{{NS}}}drugbank-id')
                if ids:
                    dbid = ids[0].text
            name = el.findtext(f'./{{{NS}}}name') or ''
            desc = el.findtext(f'./{{{NS}}}description') or ''
            url = f'https://go.drugbank.com/drugs/{dbid}' if dbid else ''
            doc_id = dbid or str(uuid.uuid4())
            text = (name + "\n\n" + desc).strip()
            yield {
                'id': doc_id,
                'text': text,
                'source': 'drugbank_local',
                'url': url,
            }
            el.clear()


def fetch_existing_ids(client: bigquery.Client, dataset: str = 'biomind_corpus', table: str = 'corpus') -> Set[str]:
    """Return set of existing ids in the corpus table that look like DrugBank entries."""
    q = f"SELECT id FROM `{client.project}.{dataset}.{table}` WHERE LOWER(source) LIKE '%drugbank%'"
    ids = set()
    try:
        for row in client.query(q).result():
            ids.add(str(row.id))
    except Exception:
        # If table missing or query fails, return empty set to allow full ingest
        return set()
    return ids


def batch_insert(client: bigquery.Client, rows: list, dataset: str = 'biomind_corpus', table: str = 'corpus') -> int:
    if not rows:
        return 0
    table_ref = f"{client.project}.{dataset}.{table}"
    # Insert in a single API call for the batch
    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        print('Insert errors (first 5):', errors[:5])
        # Do not stop on errors; return number of succeeded rows heuristic
        return 0
    return len(rows)


def ingest_all(xml_path: str, project: str = None, batch_size: int = 500, skip_existing: bool = True):
    client = bigquery.Client(project=project)
    existing = set()
    if skip_existing:
        print('Fetching existing DrugBank ids (this may take a moment)...')
        existing = fetch_existing_ids(client)
        print(f'Found {len(existing)} existing DrugBank ids; these will be skipped')

    total_parsed = 0
    total_inserted = 0
    batch = []
    start = time.time()
    for doc in stream_drugs(xml_path):
        total_parsed += 1
        if skip_existing and doc['id'] in existing:
            if total_parsed % 5000 == 0:
                print(f'skipped {total_parsed} parsed so far (existing present)')
            continue
        batch.append(doc)
        if len(batch) >= batch_size:
            inserted = batch_insert(client, batch)
            total_inserted += inserted
            print(f'Parsed {total_parsed} — inserted {inserted} rows (total inserted {total_inserted})')
            batch = []
    # final batch
    if batch:
        inserted = batch_insert(client, batch)
        total_inserted += inserted
        print(f'Final batch inserted {inserted} rows')

    elapsed = time.time() - start
    print(f'Ingest complete: parsed={total_parsed} inserted={total_inserted} elapsed_s={elapsed:.1f}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--xml', required=True)
    p.add_argument('--project', default=None)
    p.add_argument('--batch-size', type=int, default=500)
    p.add_argument('--skip-existing', action='store_true', default=True)
    args = p.parse_args()
    ingest_all(args.xml, project=args.project, batch_size=args.batch_size, skip_existing=args.skip_existing)
