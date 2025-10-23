from __future__ import annotations

import os
from typing import List, Dict

from google.cloud import documentai_v1 as documentai
from google.cloud import bigquery

from pipeline.schemas import Chunk

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
PROCESSOR = os.getenv("DOCAI_PROCESSOR")  # projects/../locations/../processors/..
DATASET = os.getenv("BQ_DATASET", "biomind_corpus")
CHUNKS_TABLE = os.getenv("BQ_CHUNKS_TABLE", "chunks")


def chunk_blocks(text: str, max_tokens: int = 200) -> List[str]:
    # naive whitespace splitter; replace with a tokenizer if needed
    words = text.split()
    out: List[str] = []
    cur: List[str] = []
    for w in words:
        cur.append(w)
        if len(cur) >= max_tokens:
            out.append(" ".join(cur))
            cur = []
    if cur:
        out.append(" ".join(cur))
    return out


def run_docai(gcs_uri: str) -> str:
    client = documentai.DocumentProcessorServiceClient()
    name = PROCESSOR
    gcs_input = documentai.GcsDocument(uri=gcs_uri, mime_type="application/pdf")
    input_config = documentai.BatchDocumentsInputConfig(gcs_documents=documentai.GcsDocuments(documents=[gcs_input]))
    request = documentai.ProcessRequest(name=name, inline_document=None, raw_document=None,
                                        skip_human_review=True, field_mask=None, process_options=None,
                                        input_documents=input_config)
    # For simplicity, call process_document (single) when available; Batch used above as example signature
    # Here, we fallback to process_document on the first page
    single_request = documentai.ProcessRequest(name=name, raw_document=None, inline_document=None,
                                               skip_human_review=True, gcs_document=gcs_input)
    result = client.process_document(request=single_request)
    doc = result.document
    return doc.text or ""


def upsert_chunks_bq(dataset: str, table: str, chunks: List[Chunk]) -> int:
    client = bigquery.Client()
    rows = [c.to_bq() for c in chunks]
    if not rows:
        return 0
    table_id = f"{dataset}.{table}"
    errors = client.insert_rows_json(table_id, rows)
    if errors:
        pass
    return len(rows)


if __name__ == "__main__":
    # Example CLI usage (assumes DOC AI output); in Cloud Run you’d wrap this as HTTP similar to ingest.
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper_id", required=True)
    parser.add_argument("--pdf_gcs_uri", required=True)
    parser.add_argument("--url", default="")
    args = parser.parse_args()

    full_text = run_docai(args.pdf_gcs_uri)
    blocks = chunk_blocks(full_text, max_tokens=200)
    chunks: List[Chunk] = []
    for i, t in enumerate(blocks):
        chunks.append(Chunk(id=f"{args.paper_id}-c{i+1}", paper_id=args.paper_id, section="body", position=i+1,
                            text=t, token_count=len(t.split()), url=args.url))
    written = upsert_chunks_bq(DATASET, CHUNKS_TABLE, chunks)
    print({"chunks_written": written})
