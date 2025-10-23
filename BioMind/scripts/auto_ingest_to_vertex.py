#!/usr/bin/env python3
"""
End-to-end ingestion script: fetch → chunk → embed → write datapoints JSONL → upload to GCS → upsert to Vertex AI Matching Engine → publish corpus to GCS.

- Sources: PubMed realtime via connectors.pubmed.connector.fetch_pubmed_data_realtime
- Embeddings: VertexAIEmbeddings (text-embedding-005 by default)
- Index: Vertex AI Matching Engine (requires INDEX resource and ENDPOINT/DEPLOYED configured)

Requirements:
- GOOGLE_CLOUD_PROJECT set (or --project)
- .env configured with MATCHING_ENGINE_INDEX_NAME and MATCHING_ENGINE_INDEX_ENDPOINT + MATCHING_ENGINE_DEPLOYED_INDEX_ID
- Application Default Credentials (gcloud auth application-default login)

Example:
  python scripts/auto_ingest_to_vertex.py \
    --query "amyloid beta tau alzheimer" \
    --project YOUR_PROJECT \
    --location us-central1 \
    --gcs-bucket YOUR_BUCKET \
    --gcs-prefix biomind/corpus \
    --index-name projects/YOUR_PROJECT/locations/us-central1/indexes/INDEX_ID
"""

from __future__ import annotations

import argparse
import json
import os
from typing import List, Dict, Any

from langchain_google_vertexai import VertexAIEmbeddings
from google.cloud import aiplatform
from google.cloud import storage
from dotenv import load_dotenv

from connectors.pubmed.connector import fetch_pubmed_data_realtime


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    text = text or ""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0:
            start = 0
        if end == len(text):
            break
    return chunks


def build_records(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for a in articles:
        pmid = str(a.get("pmid"))
        title = a.get("title") or ""
        abstract = a.get("abstract") or ""
        base_id = pmid or f"pmidless-{abs(hash(title))}"
        full_text = (title + "\n\n" + abstract).strip()
        for i, chunk in enumerate(chunk_text(full_text)):
            rec_id = f"{base_id}::c{i}"
            records.append({
                "id": rec_id,
                "text": chunk,
                "source": "pubmed_articles",
            })
    return records


def embed_records(records: List[Dict[str, Any]], project: str, location: str, model: str) -> List[List[float]]:
    embedder = VertexAIEmbeddings(project=project, location=location, model_name=model)
    texts = [r["text"] for r in records]
    return embedder.embed_documents(texts)


def write_jsonl(path: str, items: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")


def upload_gcs(local_path: str, bucket: str, dest: str) -> str:
    client = storage.Client()
    b = client.bucket(bucket)
    blob = b.blob(dest)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket}/{dest}"


def upsert_to_matching_engine(index_name: str, datapoints_jsonl_path: str, project: str | None = None, location: str | None = None) -> None:
    aiplatform.init(project=project, location=location)
    index = aiplatform.MatchingEngineIndex(index_name)
    index.upsert_datapoints(datapoints=datapoints_jsonl_path)


def main() -> int:
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--query", required=True)
    p.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID"))
    p.add_argument("--location", default=os.getenv("LOCATION", "us-central1"))
    p.add_argument("--model", default=os.getenv("EMBEDDING_MODEL", "text-embedding-005"))
    p.add_argument("--gcs-bucket", default=os.getenv("GCS_BUCKET"))
    p.add_argument("--gcs-prefix", default=os.getenv("GCS_PREFIX", "biomind/corpus"))
    p.add_argument("--index-name", default=os.getenv("MATCHING_ENGINE_INDEX_NAME"))
    p.add_argument("--skip-upsert", action="store_true", help="Skip upserting to Matching Engine (useful for Batch indexes)")

    args = p.parse_args()
    # Basic validation and placeholder guards
    if not args.project:
        print("Error: --project or GOOGLE_CLOUD_PROJECT (or GCP_PROJECT_ID) required", flush=True)
        return 2
    if not args.index_name:
        print("Error: --index-name or MATCHING_ENGINE_INDEX_NAME required (projects/.../indexes/ID)", flush=True)
        return 2
    if not args.gcs_bucket:
        print("Error: --gcs-bucket or GCS_BUCKET required (target Cloud Storage bucket)", flush=True)
        return 2

    # Common placeholder mistakes
    if "YOUR_PROJECT" in args.index_name or "INDEX_ID" in args.index_name:
        print("Error: Replace INDEX placeholders in --index-name/MATCHING_ENGINE_INDEX_NAME with your real index resource name.", flush=True)
        return 2
    if args.gcs_bucket.upper() == "YOUR_BUCKET" or "YOUR_BUCKET" in args.gcs_bucket:
        print("Error: Replace YOUR_BUCKET with your real GCS bucket name (or set GCS_BUCKET in .env)", flush=True)
        return 2

    # 1) Fetch articles
    arts = fetch_pubmed_data_realtime(args.query, max_results=25)
    if not arts:
        print("No articles fetched", flush=True)
        return 3

    # 2) Build chunked records
    records = build_records(arts)
    if not records:
        print("No records after chunking", flush=True)
        return 3

    # 3) Embed
    vectors = embed_records(records, args.project, args.location, args.model)

    # 4) Write datapoints jsonl (ME format)
    datapoints = []
    for rec, vec in zip(records, vectors):
        obj = {
            "id": rec["id"],
            "embedding": vec,
            "restricts": [{"namespace": "source", "allowTokens": [rec.get("source") or "pubmed_articles"]}],
        }
        datapoints.append(obj)
    local_dp = "/tmp/biomind_datapoints.jsonl"
    write_jsonl(local_dp, datapoints)

    # 5) Upload datapoints jsonl to GCS
    dp_uri = upload_gcs(local_dp, args.gcs_bucket, f"{args.gcs_prefix.rstrip('/')}/datapoints.jsonl")
    print(f"Uploaded datapoints: {dp_uri}")

    # 6) Upsert to Matching Engine index (optional)
    if args.skip_upsert:
        print("Skipping upsert to Matching Engine (skip requested).")
    else:
        upsert_to_matching_engine(args.index_name, dp_uri, project=args.project, location=args.location)
        print("Upserted datapoints to Matching Engine")

    # 7) Publish corpus.jsonl (ID->text mapping for UI)
    corpus = [{"id": r["id"], "text": r["text"], "source": r.get("source", "pubmed_articles")} for r in records]
    local_corpus = "/tmp/biomind_corpus.jsonl"
    write_jsonl(local_corpus, corpus)
    corpus_uri = upload_gcs(local_corpus, args.gcs_bucket, f"{args.gcs_prefix.rstrip('/')}/corpus.jsonl")
    print(f"Published corpus: {corpus_uri}")
    print("Set CORPUS_URI in .env to:")
    print(f"CORPUS_URI={corpus_uri}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
