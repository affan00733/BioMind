from __future__ import annotations

import io
import os
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Tuple

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from google.cloud import storage
from langchain_google_vertexai import VertexAIEmbeddings


PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID", "")
LOCATION = os.getenv("LOCATION", "us-central1")
UPLOADS_BUCKET = os.getenv("UPLOADS_BUCKET", "")  # gs://bucket/prefix
DATAPOINTS_GCS = os.getenv("DATAPOINTS_GCS", "")  # gs://bucket/prefix
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-005")
MAX_FILES = int(os.getenv("MAX_FILES", "200"))
CHUNK_CHAR_LIMIT = int(os.getenv("CHUNK_CHAR_LIMIT", "5000"))
MARK_DONE = os.getenv("MARK_DONE", "true").lower() == "true"


def _parse_gs_uri(gs_uri: str) -> Tuple[str, str]:
    assert gs_uri.startswith("gs://"), "URI must start with gs://"
    path = gs_uri[5:]
    bucket, _, prefix = path.partition("/")
    return bucket, prefix


def _list_new_texts(client: storage.Client, bucket: str, prefix: str, limit: int) -> List[str]:
    blobs = client.list_blobs(bucket, prefix=prefix)
    out: List[str] = []
    for b in blobs:
        if not b.name.endswith(".txt"):
            continue
        done = client.bucket(bucket).blob(b.name + ".done")
        if done.exists():
            continue
        out.append(b.name)
        if len(out) >= limit:
            break
    return out


def _read_text(client: storage.Client, bucket: str, name: str) -> str:
    bio = io.BytesIO()
    client.bucket(bucket).blob(name).download_to_file(bio)
    return bio.getvalue().decode("utf-8", errors="ignore")


def _write_jsonl(client: storage.Client, bucket: str, name: str, lines: List[dict]) -> str:
    data = ("\n".join(json.dumps(l) for l in lines)).encode("utf-8")
    client.bucket(bucket).blob(name).upload_from_string(data, content_type="application/json")
    return f"gs://{bucket}/{name}"


def _mark_done(client: storage.Client, bucket: str, name: str):
    client.bucket(bucket).blob(name + ".done").upload_from_string("", content_type="text/plain")


def process_once(max_files: int = MAX_FILES) -> dict:
    if not UPLOADS_BUCKET or not DATAPOINTS_GCS:
        raise RuntimeError("UPLOADS_BUCKET and DATAPOINTS_GCS must be set")

    up_bucket, up_prefix = _parse_gs_uri(UPLOADS_BUCKET)
    if up_prefix and not up_prefix.endswith("/"):
        up_prefix += "/"
    text_prefix = up_prefix + "uploads/text/"

    dp_bucket, dp_prefix = _parse_gs_uri(DATAPOINTS_GCS)
    if dp_prefix and not dp_prefix.endswith("/"):
        dp_prefix += "/"

    storage_client = storage.Client()
    files = _list_new_texts(storage_client, up_bucket, text_prefix, max_files)
    if not files:
        return {"processed": 0, "datapoints_uri": None}

    embedder = VertexAIEmbeddings(project=PROJECT, location=LOCATION, model_name=EMBEDDING_MODEL)

    # Read and embed in small batches
    lines: List[dict] = []
    batch_texts: List[str] = []
    batch_ids: List[str] = []
    BATCH = 64
    processed = 0

    def flush_batch():
        nonlocal lines, batch_texts, batch_ids
        if not batch_texts:
            return
        vecs = embedder.embed_documents(batch_texts)
        for pid, vec in zip(batch_ids, vecs):
            # Vertex AI Vector Search expects keys: datapoint_id, feature_vector, restricts
            lines.append({
                "datapoint_id": pid,
                "feature_vector": vec,
                "restricts": [{"namespace": "source", "allow": ["user_upload"]}],
            })
        batch_texts = []
        batch_ids = []

    for name in files:
        text = _read_text(storage_client, up_bucket, name)[:CHUNK_CHAR_LIMIT]
        # Use the hashed filename (persist step uses sha256-based name)
        base = os.path.basename(name)
        pid = os.path.splitext(base)[0]
        batch_texts.append(text)
        batch_ids.append(pid)
        processed += 1
        if len(batch_texts) >= BATCH:
            flush_batch()
        if MARK_DONE:
            _mark_done(storage_client, up_bucket, name)

    flush_batch()

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Write a .json file to satisfy CLI extension checks; content is newline-delimited JSON objects
    out_obj = f"{dp_prefix}ingest/{ts}/datapoints.json"
    out_uri = _write_jsonl(storage_client, dp_bucket, out_obj, lines)
    return {"processed": processed, "datapoints_uri": out_uri}


app = FastAPI()


class RunBody(BaseModel):
    max_files: Optional[int] = None


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.post("/run")
def run(body: RunBody):
    m = body.max_files if body and body.max_files else MAX_FILES
    result = process_once(max_files=int(m))
    return JSONResponse(result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
