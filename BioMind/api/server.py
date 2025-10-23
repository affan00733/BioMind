from __future__ import annotations

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from rag.service import run_rag
from utils.file_utils import extract_text_from_file
from utils.corpus_loader import load_corpus_map, clear_corpus_cache, corpus_stats
from utils.uploads_persistence import persist_uploads_if_enabled
from utils.corpus_writer import upsert_corpus_rows
from dotenv import load_dotenv
import os


# Ensure .env variables are loaded for configuration (project, endpoints, etc.)
load_dotenv()

app = FastAPI(title="BioMind RAG API", version="0.1.0")

def _parse_allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS", "")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    # If empty, default to no wildcard for safety in prod; allow localhost for dev
    return parts or ["http://localhost:3000", "http://localhost:3001"]

_allowed = _parse_allowed_origins()
# Support an env var to allow wildcard CORS in development easier
if os.getenv("DEV_ALLOW_ALL_CORS", "false").lower() in ("1", "true", "yes"):
    _allowed = ["*"]
    allow_creds = True
else:
    allow_creds = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed,
    allow_credentials=allow_creds,
    allow_methods=["*"],
    allow_headers=["*"],
)

import logging
logger = logging.getLogger("uvicorn")
logger.info(f"Starting BioMind API - allowed_origins={_allowed}")


class RAGRequest(BaseModel):
    query: str
    k: int = 20
    mode: str = "General"
    source_filters: Optional[List[str]] = None
    min_score_threshold: float = 0.2
    temperature: float = 0.3
    model: Optional[str] = None  # e.g., "gemini", "gpt", "claude" or full model name


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


MAX_FILES = int(os.getenv("UPLOAD_MAX_FILES", "5"))
MAX_TOTAL_MB = float(os.getenv("UPLOAD_MAX_TOTAL_MB", "10"))
ALLOWED_EXTS = {".pdf", ".docx", ".txt"}


@app.get("/admin/corpus/stats")
def admin_corpus_stats():
    return corpus_stats()


@app.post("/admin/corpus/reload")
def admin_corpus_reload():
    clear_corpus_cache()
    return {"ok": True, **corpus_stats()}


@app.post("/admin/corpus/seed")
async def admin_corpus_seed(query: Optional[str] = None, max_results: int = 8):
    """Fetch a small set of live PubMed/UniProt records and persist them into the
    BigQuery corpus table. Returns how many rows were attempted.

    This is a convenience endpoint to quickly warm up an empty corpus table
    without requiring a full RAG query. Safe to call multiple times.
    """
    rows: list[dict[str, str]] = []
    q = (query or "BRCA1 cancer signaling").strip()
    # PubMed realtime
    try:
        from connectors.pubmed.connector import fetch_pubmed_data_realtime  # type: ignore
        arts = fetch_pubmed_data_realtime(q, max_results=max_results) or []
        for a in arts:
            pmid = str(a.get("pmid", ""))
            title = a.get("title", "")
            abstract = a.get("abstract", "")
            text = (title + "\n\n" + abstract).strip()
            if text:
                rows.append(
                    {
                        "id": pmid or f"pmid-{abs(hash(text)) & 0xfffffff}",
                        "text": text,
                        "source": "pubmed_articles",
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid.isdigit() else "",
                    }
                )
    except Exception:
        # Non-fatal; continue with UniProt
        pass

    # UniProt realtime
    try:
        from connectors.uniprot.connector import fetch_uniprot_data_realtime  # type: ignore
        prots = fetch_uniprot_data_realtime(q, max_results=max_results) or []
        for p in prots:
            acc = str(p.get("accession", ""))
            pname = p.get("protein_name", "")
            genes = p.get("genes", "")
            seq = p.get("sequence", "")
            seq_snip = seq[:600]
            text = (f"Protein: {pname}\nGenes: {genes}\n\nSequence (partial):\n{seq_snip}").strip()
            if text:
                rows.append(
                    {
                        "id": acc or p.get("uniprot_id", "") or f"uniprot-{abs(hash(text)) & 0xfffffff}",
                        "text": text,
                        "source": "uniprot_records",
                        "url": f"https://www.uniprot.org/uniprotkb/{acc}/entry" if acc else "",
                    }
                )
    except Exception:
        pass

    inserted = 0
    try:
        if rows:
            inserted = upsert_corpus_rows(rows)
    except Exception:
        inserted = 0
    return {
        "ok": True,
        "query": q,
        "attempted_rows": len(rows),
        "inserted_rows": inserted,
        "dataset": os.getenv("BQ_CORPUS_DATASET", ""),
        "table": os.getenv("BQ_CORPUS_TABLE", ""),
    }


@app.post("/api/rag/search")
async def api_rag_search(req: RAGRequest):
    try:
        result = await run_rag(
            query=req.query,
            k=req.k,
            mode=req.mode,
            source_filters=req.source_filters,
            min_score_threshold=req.min_score_threshold,
            temperature=req.temperature,
            model_override=req.model,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/search_upload")
async def api_rag_search_upload(
    query: str = Form(...),
    k: int = Form(8),
    mode: str = Form("General"),
    min_score_threshold: float = Form(0.4),
    temperature: float = Form(0.3),
    model: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
):
    """
    Multipart endpoint that accepts query plus optional files. Extracts text and includes in RAG context.
    """
    try:
        extra_texts: List[str] = []
        raw_pairs: List[tuple[str, bytes]] = []
        if files:
            if len(files) > MAX_FILES:
                raise HTTPException(status_code=413, detail=f"Too many files; max {MAX_FILES}")
            total_bytes = 0
            for f in files:
                try:
                    name = f.filename or ""
                    ext = os.path.splitext(name)[1].lower()
                    if ext not in ALLOWED_EXTS:
                        raise HTTPException(status_code=415, detail=f"Unsupported file type: {ext}")
                    content = await f.read()
                    raw_pairs.append((name, content))
                    total_bytes += len(content)
                    if total_bytes > MAX_TOTAL_MB * 1024 * 1024:
                        raise HTTPException(status_code=413, detail=f"Total upload size exceeds {MAX_TOTAL_MB}MB")
                    text = extract_text_from_file(f.filename, content)
                    if text and text.strip():
                        extra_texts.append(text.strip())
                except Exception:
                    # Skip file on error, continue others
                    continue

        # Optionally persist uploads to GCS/BQ (no local persistence)
        _ = persist_uploads_if_enabled(extra_texts, raw_pairs, owner_id=None)

        result = await run_rag(
            query=query,
            k=k,
            mode=mode,
            source_filters=None,
            min_score_threshold=min_score_threshold,
            temperature=temperature,
            extra_texts=extra_texts or None,
            model_override=model,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sources/{source_id}")
def api_get_source(source_id: str) -> Dict[str, Any]:
    corpus = load_corpus_map()
    entry = corpus.get(source_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    return entry
