from __future__ import annotations

from typing import List, Dict, Any
from utils.config_utils import get_config


class CorpusRepository:
    def get_docs_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Return list of {text, metadata} for given ids.

        metadata must include: {source, source_id, source_type, url}
        """
        raise NotImplementedError


class GCSJsonlCorpus(CorpusRepository):
    def __init__(self) -> None:
        from utils.corpus_loader import load_corpus_map

        self._load = load_corpus_map

    def get_docs_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        m = self._load()  # uses TTL cache under the hood
        out: List[Dict[str, Any]] = []
        for i in ids:
            d = m.get(str(i))
            if d:
                out.append(d)
        return out


class BigQueryCorpus(CorpusRepository):
    def __init__(self) -> None:
        from google.cloud import bigquery  # type: ignore

        self._bq = bigquery.Client()
        # Prefer explicit corpus table if provided, else fall back to chunks table
        corpus_ds = get_config("BQ_CORPUS_DATASET")
        corpus_tbl = get_config("BQ_CORPUS_TABLE")
        if corpus_ds and corpus_tbl:
            self._dataset = corpus_ds
            self._table = corpus_tbl
            self._is_chunks = False
        else:
            # Fall back to general dataset/chunks table
            self._dataset = get_config("BQ_DATASET", "biomind_corpus")
            self._table = get_config("BQ_CHUNKS_TABLE", "chunks")
            self._is_chunks = True

    def get_docs_by_ids(self, ids: List[str]) -> List[Dict[str, Any]]:
        if not ids:
            return []
        tbl = f"`{self._dataset}.{self._table}`"
        if self._is_chunks:
            query = f"""
                SELECT id, text, 'paper_chunk' AS source, COALESCE(url, '') AS url
                FROM {tbl}
                WHERE id IN UNNEST(@ids)
            """
        else:
            query = f"""
                SELECT id, text, source, COALESCE(url, '') AS url
                FROM {tbl}
                WHERE id IN UNNEST(@ids)
            """
        from google.cloud import bigquery  # type: ignore
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ArrayQueryParameter("ids", "STRING", [str(i) for i in ids])]
        )
        try:
            job = self._bq.query(query, job_config=job_config)
            rows = list(job)
        except Exception:
            # Dataset/table may not exist yet; return empty to allow live fallback
            return []
        out: List[Dict[str, Any]] = []
        for r in rows:
            sid = str(r["id"]) if "id" in r else str(r.id)
            text = r["text"] if "text" in r else getattr(r, "text", "")
            source = r["source"] if "source" in r else getattr(r, "source", "")
            url = r["url"] if "url" in r else getattr(r, "url", "")
            out.append(
                {
                    "text": text,
                    "metadata": {
                        "source": source,
                        "source_id": sid,
                        "source_type": "corpus",
                        "url": url or "",
                    },
                }
            )
        return out


def get_corpus_repo() -> CorpusRepository:
    backend = str(get_config("CORPUS_BACKEND", "gcs_jsonl")).lower()
    if backend in ("bq", "bigquery"):
        return BigQueryCorpus()
    return GCSJsonlCorpus()
