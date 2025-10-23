"""
Utilities to load corpus entries and map vector IDs to source texts/metadata.

Assumes a JSONL corpus at data/corpus.jsonl with fields:
- id: str
- text: str
- source: str (optional)

Provides a simple loader that returns a dict id -> {text, metadata}.
"""

from __future__ import annotations

from typing import Dict, Any, Iterable, Tuple
from pathlib import Path
import json
import io  # ensure stdlib available; remove if unused
import time
from utils.config_utils import get_config
import logging

try:
    from google.cloud import storage
except Exception:
    storage = None
try:
    from google.cloud import bigquery
except Exception:
    bigquery = None

DEFAULT_CORPUS_PATH = Path(__file__).resolve().parents[1] / "data" / "corpus.jsonl"
_CACHE: Tuple[float, Dict[str, Dict[str, Any]]] | None = None
_CACHE_TTL = 300.0  # seconds


def clear_corpus_cache() -> None:
    """Clear the in-process corpus cache so next call reloads from source."""
    global _CACHE
    _CACHE = None


def corpus_stats() -> Dict[str, Any]:
    """Return simple diagnostics about the current corpus cache and source."""
    age = None
    size = None
    if _CACHE:
        age = max(0, time.time() - _CACHE[0])
        size = len(_CACHE[1])
    backend = (get_config("CORPUS_BACKEND", "") or "").lower()
    return {
        "backend": backend or ("bq" if get_config("BQ_CORPUS_TABLE", "") else "gcs_jsonl"),
        "uri": get_config("CORPUS_URI", ""),
        "bq_dataset": get_config("BQ_CORPUS_DATASET", ""),
        "bq_table": get_config("BQ_CORPUS_TABLE", ""),
        "strict": bool(get_config("STRICT_REMOTE_CORPUS", False)),
        "cache_age_sec": age,
        "cache_size": size,
    }


def _derive_url(source: str, sid: str) -> str:
    """Best-effort URL construction for known source types."""
    if not source or not sid:
        return ""
    source = str(source)
    # PubMed article IDs are numeric
    if source == "pubmed_articles" and sid.isdigit():
        return f"https://pubmed.ncbi.nlm.nih.gov/{sid}/"
    # UniProt IDs look like P10636, Q9BXS0, etc.
    if source == "uniprot_records":
        return f"https://www.uniprot.org/uniprotkb/{sid}/entry"
    return ""


def _iter_jsonl_lines() -> Iterable[str]:
    uri = get_config("CORPUS_URI", "")
    strict = bool(get_config("STRICT_REMOTE_CORPUS", False))
    if uri and uri.startswith("gs://") and storage is not None:
        # Read from GCS
        try:
            _, path = uri.split("gs://", 1)
            bucket_name, blob_name = path.split("/", 1)
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            # Support prefix mode when CORPUS_URI ends with '/'
            if blob_name.endswith("/"):
                blobs = list(client.list_blobs(bucket_name, prefix=blob_name))
                jsonl_blobs = sorted([b for b in blobs if b.name.lower().endswith(".jsonl")], key=lambda b: b.name)
                if not jsonl_blobs:
                    logging.error(f"No corpus JSONL objects found under prefix: {uri}")
                    return
                for b in jsonl_blobs:
                    with bucket.blob(b.name).open("r") as f:
                        for line in f:
                            yield line
            else:
                blob = bucket.blob(blob_name)
                if not blob.exists():
                    logging.error(f"Corpus blob not found: {uri}")
                    return
                # Stream lines directly to avoid large memory usage
                with blob.open("r") as f:
                    for line in f:
                        yield line
        except Exception as e:
            logging.error(f"Failed to load corpus from GCS '{uri}': {e}")
            # Gracefully degrade: yield nothing so callers can proceed with empty corpus
            return
    elif uri and uri.startswith("gs://") and storage is None:
        # GCS URI provided but google-cloud-storage is unavailable
        logging.error("google-cloud-storage not available; cannot read CORPUS_URI from GCS")
        if bool(get_config("STRICT_REMOTE_CORPUS", False)):
            raise RuntimeError("STRICT_REMOTE_CORPUS enabled but google-cloud-storage not available to read GCS corpus")
        return
    else:
        if strict:
            raise RuntimeError("STRICT_REMOTE_CORPUS enabled but CORPUS_URI not set or not gs://; provide CORPUS_URI.")
        # Read from local file
        corpus_path = Path(DEFAULT_CORPUS_PATH)
        if not corpus_path.exists():
            return
        with corpus_path.open("r", encoding="utf-8") as f:
            for line in f:
                yield line


def _load_from_bigquery() -> Dict[str, Dict[str, Any]]:
    """Load entire corpus mapping from BigQuery table (id,text,source[,url])."""
    if bigquery is None:
        raise RuntimeError("google-cloud-bigquery not available; install dependency or set CORPUS_BACKEND to gcs_jsonl")
    project = get_config("GOOGLE_CLOUD_PROJECT", "") or None
    dataset = get_config("BQ_CORPUS_DATASET", "")
    table = get_config("BQ_CORPUS_TABLE", "")
    if not (dataset and table):
        raise RuntimeError("BQ_CORPUS_DATASET and BQ_CORPUS_TABLE must be set for BigQuery backend")
    fqtn = f"`{(project + '.') if project else ''}{dataset}.{table}`"
    sql = f"SELECT id, text, source, COALESCE(url, '') AS url FROM {fqtn}"
    client = bigquery.Client(project=project)
    mapping: Dict[str, Dict[str, Any]] = {}
    try:
        for row in client.query(sql).result(page_size=5000):
            _id = str(row["id"])
            text = row["text"] or ""
            source = row["source"] or ""
            url = (row["url"] or "") or _derive_url(source, _id)
            mapping[_id] = {
                "text": text,
                "metadata": {
                    "source": source,
                    "source_id": _id,
                    "source_type": "corpus",
                    "url": url,
                },
            }
    except Exception as e:
        logging.error(f"Failed to load corpus from BigQuery: {e}")
        raise
    return mapping


def load_corpus_map(corpus_path: Path | str = DEFAULT_CORPUS_PATH) -> Dict[str, Dict[str, Any]]:
    """Load a mapping from id -> {text, metadata} from a JSONL corpus file or GCS URI.

    Cached in-process with a short TTL to avoid repeated I/O.
    """
    global _CACHE
    now = time.time()
    if _CACHE and (now - _CACHE[0]) < _CACHE_TTL:
        return _CACHE[1]

    backend = (get_config("CORPUS_BACKEND", "") or "").lower()
    use_bq = backend in ("bq", "bigquery") or bool(get_config("BQ_CORPUS_TABLE", ""))
    if use_bq:
        mapping = _load_from_bigquery()
    else:
        mapping = {}
        for raw in _iter_jsonl_lines() or []:
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            _id = str(obj.get("id"))
            text = obj.get("text", "")
            source = obj.get("source", "")
            url = obj.get("url") or _derive_url(source, _id)
            mapping[_id] = {
                "text": text,
                "metadata": {
                    "source": source,
                    "source_id": _id,
                    "source_type": "corpus",
                    "url": url,
                },
            }
    _CACHE = (now, mapping)
    return mapping
