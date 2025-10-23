#!/usr/bin/env python3
"""
Upload a local corpus.jsonl to GCS and print the CORPUS_URI to use.

Usage:
  python scripts/publish_corpus_to_gcs.py --bucket YOUR_BUCKET --dest path/corpus.jsonl [--src data/corpus.jsonl]

Requires Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS with storage.admin.
"""

import argparse
from pathlib import Path
from google.cloud import storage


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bucket", required=True, help="GCS bucket name")
    p.add_argument("--dest", required=True, help="Destination path in bucket (e.g., path/corpus.jsonl)")
    p.add_argument("--src", default=str(Path(__file__).resolve().parents[1] / "data" / "corpus.jsonl"))
    args = p.parse_args()

    src = Path(args.src)
    if not src.exists():
        raise SystemExit(f"Source not found: {src}")

    client = storage.Client()
    bucket = client.bucket(args.bucket)
    blob = bucket.blob(args.dest)
    blob.upload_from_filename(str(src))
    uri = f"gs://{args.bucket}/{args.dest}"
    print(f"Uploaded corpus to {uri}")
    print("Set CORPUS_URI in .env to:")
    print(f"CORPUS_URI={uri}")


if __name__ == "__main__":
    main()
