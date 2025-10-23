from __future__ import annotations

import hashlib
import time
from typing import List, Tuple, Dict, Any
from utils.config_utils import get_config


def _now_ts() -> int:
    return int(time.time())


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_gs_uri(uri: str) -> Tuple[str, str]:
    assert uri.startswith("gs://"), "URI must start with gs://"
    bucket, _, path = uri[5:].partition("/")
    return bucket, path


def persist_uploads_if_enabled(
    extracted_texts: List[str],
    raw_files: List[Tuple[str, bytes]] | None = None,
    owner_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Persist uploaded files and their extracted texts to GCS/BigQuery if enabled.

    Env flags:
      - PERSIST_UPLOADS=true|false
      - UPLOADS_BUCKET=gs://bucket/prefix (required if persisting)
      - UPLOADS_BQ_DATASET, UPLOADS_BQ_TABLE (optional; if set, rows are inserted)

    Returns a list of records with {id, text_gcs_uri?, raw_gcs_uri?, source, url}
    """
    if not get_config("PERSIST_UPLOADS", False):
        return []

    bucket_uri = get_config("UPLOADS_BUCKET")
    if not bucket_uri or not str(bucket_uri).startswith("gs://"):
        return []

    from google.cloud import storage  # type: ignore
    from google.cloud import bigquery  # type: ignore

    bq_dataset = get_config("UPLOADS_BQ_DATASET")
    bq_table = get_config("UPLOADS_BQ_TABLE")
    do_bq = bool(bq_dataset and bq_table)

    bucket_name, prefix = _parse_gs_uri(bucket_uri)
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    out: List[Dict[str, Any]] = []
    ts = _now_ts()

    # Upload raw files first (optional)
    raw_index: Dict[str, str] = {}
    if raw_files:
        for fname, data in raw_files:
            try:
                file_hash = _hash_bytes(data)
                obj = f"{prefix}uploads/raw/{ts}-{file_hash}-{fname}"
                blob = bucket.blob(obj)
                blob.upload_from_string(data)
                raw_index[file_hash] = f"gs://{bucket_name}/{obj}"
            except Exception:
                continue

    # Upload extracted texts, write BQ rows
    bq_client = None
    if do_bq:
        bq_client = bigquery.Client()
        table_ref = f"{bq_dataset}.{bq_table}"

    for i, text in enumerate(extracted_texts):
        if not text or not text.strip():
            continue
        data = text.encode("utf-8")
        t_hash = _hash_bytes(data)
        text_obj = f"{prefix}uploads/text/{ts}-{t_hash}.txt"
        text_uri = None
        try:
            blob = bucket.blob(text_obj)
            blob.upload_from_string(data, content_type="text/plain")
            text_uri = f"gs://{bucket_name}/{text_obj}"
        except Exception:
            pass

        rec = {
            "id": t_hash,
            "text_gcs_uri": text_uri or "",
            "raw_gcs_uri": "",
            "source": "user_upload",
            "url": "",
            "owner_id": owner_id or "",
            "created_at": ts,
        }

        # Try linking raw if matching hash
        if t_hash in raw_index:
            rec["raw_gcs_uri"] = raw_index[t_hash]

        out.append(rec)

        # Optional: insert into BigQuery table (id, text, source, url)
        if do_bq and bq_client is not None:
            try:
                row = {
                    "id": t_hash,
                    "text": text,
                    "source": "user_upload",
                    "url": text_uri or "",
                }
                errors = bq_client.insert_rows_json(f"{bq_dataset}.{bq_table}", [row])
                _ = errors  # ignore detailed handling for now
            except Exception:
                pass

    return out
