#!/usr/bin/env python3
"""
Generate Vector Search datapoints JSONL from input texts using Vertex AI embeddings,
and optionally upload to a GCS folder (bucket/prefix) suitable for ANN (Tree-AH) index creation.

Input format (JSONL, one per line):
  {"id": "doc-0001", "text": "some text ...", "source": "pubmed"}

Output format (JSONL, one per line) for Vertex AI Matching Engine:
    {"id": "doc-0001", "embedding": [..768 floats..],
     "restricts":[{"namespace":"source","allowTokens":["pubmed"]}]}

If no input is provided, a small sample set will be embedded.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import List, Dict, Any

from langchain_google_vertexai import VertexAIEmbeddings

try:
    from google.cloud import storage
    _HAS_GCS = True
except Exception:
    _HAS_GCS = False


def load_input(path: str | None) -> List[Dict[str, Any]]:
    if not path:
        # Fallback sample
        return [
            {"id": "sample-1", "text": "Alzheimer's disease amyloid-beta aggregation and tau pathology.", "source": "pubmed"},
            {"id": "sample-2", "text": "UniProt entry for APP protein with roles in synapse formation.", "source": "uniprot"},
            {"id": "sample-3", "text": "Drug repurposing candidates targeting amyloid aggregation pathways.", "source": "drugbank"},
        ]
    items: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if "id" in obj and "text" in obj:
                    items.append(obj)
            except Exception:
                continue
    return items


def ensure_dir(path: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def embed_texts(
    records: List[Dict[str, Any]],
    project: str,
    location: str,
    model_name: str,
) -> List[List[float]]:
    texts = [r["text"] for r in records]
    # Batch embeddings for better throughput
    embedder = VertexAIEmbeddings(project=project, location=location, model_name=model_name)
    vectors = embedder.embed_documents(texts)
    return vectors


def write_datapoints_jsonl(
    records: List[Dict[str, Any]],
    embeddings: List[List[float]],
    out_path: str,
) -> None:
    ensure_dir(out_path)
    with open(out_path, "w", encoding="utf-8") as f:
        for rec, vec in zip(records, embeddings):
            src = rec.get("source")
            restricts = []
            if src:
                restricts = [{"namespace": "source", "allowTokens": [str(src)]}]
            obj = {
                "id": rec["id"],
                "embedding": vec,
            }
            if restricts:
                obj["restricts"] = restricts
            f.write(json.dumps(obj) + "\n")


def upload_to_gcs(local_path: str, gcs_folder: str) -> str:
    if not _HAS_GCS:
        raise RuntimeError("google-cloud-storage not available; install and retry")
    if not gcs_folder.startswith("gs://"):
        raise ValueError("gcs_folder must start with gs://")
    # Normalize to prefix
    if not gcs_folder.endswith("/"):
        gcs_folder = gcs_folder + "/"
    # Parse bucket and prefix
    _, _, rest = gcs_folder.partition("gs://")
    bucket_name, _, prefix = rest.partition("/")
    filename = os.path.basename(local_path)
    if not filename:
        ts = time.strftime("%Y%m%d-%H%M%S")
        filename = f"datapoints-{ts}.jsonl"
    blob_name = prefix + filename if prefix else filename
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(local_path)
    return f"gs://{bucket_name}/{blob_name}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Vector Search datapoints JSONL")
    parser.add_argument("--project", required=False, default=os.getenv("GOOGLE_CLOUD_PROJECT"), help="GCP Project ID")
    parser.add_argument("--location", required=False, default=os.getenv("LOCATION", "us-central1"), help="Region (e.g., us-central1)")
    parser.add_argument("--model", required=False, default=os.getenv("EMBEDDING_MODEL", "text-embedding-005"), help="Embedding model name")
    parser.add_argument("--input", required=False, help="Path to input JSONL (id,text,source). If omitted, uses a small sample.")
    parser.add_argument("--out", required=False, default="./data/datapoints.jsonl", help="Output datapoints JSONL path")
    parser.add_argument("--gcs-folder", required=False, help="Optional: gs://bucket/prefix/ to upload the output file")

    args = parser.parse_args()
    if not args.project:
        print("--project is required (or set GOOGLE_CLOUD_PROJECT)", file=sys.stderr)
        return 2

    records = load_input(args.input)
    if not records:
        print("No input records found", file=sys.stderr)
        return 3

    print(f"Embedding {len(records)} records with {args.model} in {args.project}/{args.location}...")
    vectors = embed_texts(records, args.project, args.location, args.model)
    # Quick sanity check for typical dimension (gecko ~ 768)
    dim = len(vectors[0]) if vectors else 0
    print(f"First embedding dimension: {dim}")

    write_datapoints_jsonl(records, vectors, args.out)
    print(f"Wrote datapoints to {args.out}")

    if args.gcs_folder:
        if not _HAS_GCS:
            print("google-cloud-storage not installed; cannot upload to GCS", file=sys.stderr)
            return 4
        uri = upload_to_gcs(args.out, args.gcs_folder)
        print(f"Uploaded to {uri}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
