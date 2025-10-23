from __future__ import annotations

"""
Build a corpus.jsonl in GCS from persisted upload texts in GCS.
- Reads:  <UPLOADS_BUCKET>/uploads/text/*.txt  (UPLOADS_BUCKET env, e.g., gs://biomind-lab-data-trusty/biomind)
- Writes: CORPUS_URI (e.g., gs://biomind-lab-data-trusty/biomind/corpus/corpus.jsonl)
Each line: {"id": "<sha256>", "text": "...", "source": "user_upload"}
"""

import io
import os
import json
from urllib.parse import urlparse
from google.cloud import storage
from dotenv import load_dotenv


def parse_gs_uri(gs_uri: str):
    assert gs_uri.startswith("gs://")
    p = urlparse(gs_uri)
    return p.netloc, p.path.lstrip("/")


def main():
    load_dotenv()  # allow reading BioMind/.env when run from project root
    uploads_bucket_uri = os.getenv("UPLOADS_BUCKET", "gs://biomind-lab-data-trusty/biomind")
    corpus_uri = os.getenv("CORPUS_URI", "gs://biomind-lab-data-trusty/biomind/corpus/corpus.jsonl")

    u_bucket, u_prefix = parse_gs_uri(uploads_bucket_uri)
    if u_prefix and not u_prefix.endswith("/"):
        u_prefix += "/"
    text_prefix = u_prefix + "uploads/text/"

    o_bucket, o_path = parse_gs_uri(corpus_uri)

    client = storage.Client()

    lines = []
    for blob in client.list_blobs(u_bucket, prefix=text_prefix):
        name = blob.name
        if not name.endswith(".txt"):
            continue
        # Use filename stem as id (persist step uses sha256-based names)
        doc_id = os.path.splitext(os.path.basename(name))[0]
        bio = io.BytesIO()
        client.bucket(u_bucket).blob(name).download_to_file(bio)
        text = bio.getvalue().decode("utf-8", errors="ignore").strip()
        if not text:
            continue
        lines.append(json.dumps({"id": doc_id, "text": text, "source": "user_upload"}))

    if not lines:
        print(f"No texts found under gs://{u_bucket}/{text_prefix}")
        return

    out_buf = io.BytesIO(("\n".join(lines)).encode("utf-8"))
    client.bucket(o_bucket).blob(o_path).upload_from_file(out_buf, content_type="application/json")
    print(f"Wrote {len(lines)} lines to {corpus_uri}")


if __name__ == "__main__":
    main()
