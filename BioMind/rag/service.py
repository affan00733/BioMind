"""
Shared RAG service: retrieval + selection + generation with citations.
Used by both the Streamlit UI and the FastAPI server.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
import os
import asyncio
import time

from langchain_google_vertexai import VertexAIEmbeddings
from langchain.schema import Document

from utils.config_utils import get_config
from utils.corpus_repository import get_corpus_repo
from pathlib import Path
from rag.matching_engine_client import MatchingEngineClient
from rag.context_manager import ContextManager
from rag.response_generator import ResponseGenerator
from utils.hybrid_retriever import get_bq_ids_for_query
from utils.corpus_writer import upsert_corpus_rows


def _bq_corpus_available() -> bool:
    """Return True if BQ corpus dataset+table look available; False otherwise.
    Never raises; safe to call outside try blocks.
    """
    try:
        from google.cloud import bigquery  # type: ignore
        ds = get_config("BQ_CORPUS_DATASET", "")
        tb = get_config("BQ_CORPUS_TABLE", "")
        if not (ds and tb):
            return False
        client = bigquery.Client()
        # Ensure dataset exists
        try:
            client.get_dataset(ds)
        except Exception:
            return False
        # Ensure table exists
        try:
            client.get_table(f"{ds}.{tb}")
        except Exception:
            return False
        return True
    except Exception:
        return False
def _normalize_model_name(choice: Optional[str], default_name: str) -> str:
    """Map user-friendly choices to Vertex AI model names.
    - If choice is a full Vertex model name/path, return as-is.
    - If contains 'claude', map to Anthropic Claude on Vertex.
    - If contains 'gemini' or is 'gemini', use as-is or default.
    - Otherwise, fallback to default.
    """
    if not choice:
        return default_name
    c = choice.strip().lower()
    # Known full paths or names passed through
    if "/" in c or c.startswith("gemini"):
        return choice
    if "claude" in c:
        # Claude 3.5 Sonnet on Vertex (adjust if your project has different availability)
        return "publishers/anthropic/models/claude-3-5-sonnet"
    # Fallback to default Gemini
    return default_name


async def _score_passages(cm: ContextManager, query: str, docs: List[Document]):
    return await cm.score_passages(query, docs)


async def run_rag(
    query: str,
    k: int = 20,
    mode: str = "General",
    source_filters: Optional[List[str]] = None,
    min_score_threshold: float = 0.2,
    temperature: float = 0.3,
    extra_texts: Optional[List[str]] = None,
    model_override: Optional[str] = None,
) -> Dict[str, Any]:
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or get_config("PROJECT_ID")
    location = get_config("LOCATION", "us-central1")
    endpoint = get_config("MATCHING_ENGINE_INDEX_ENDPOINT")
    deployed_id = get_config("MATCHING_ENGINE_DEPLOYED_INDEX_ID")
    embedding_model = get_config("EMBEDDING_MODEL", "text-embedding-005")
    default_model = get_config("GENERATION_MODEL", "gemini-2.5-flash-lite")
    gen_model = _normalize_model_name(model_override, default_model)
    corpus_uri = get_config("CORPUS_URI", "")

    if not project or not endpoint or not deployed_id:
        raise RuntimeError("Missing config: project/endpoint/deployed_id")

    t0 = time.time()
    embedder = VertexAIEmbeddings(project=project, location=location, model_name=embedding_model)
    # Offload sync embed call to thread to avoid blocking event loop
    loop = asyncio.get_event_loop()
    qvec = await loop.run_in_executor(None, embedder.embed_query, query)

    client = MatchingEngineClient(project=project, location=location, index_endpoint_name=endpoint, deployed_index_id=deployed_id)
    t_embed = time.time()
    neighbors = client.search(qvec, num_neighbors=k)
    neighbor_ids = [n.get("datapoint_id") for n in neighbors if n.get("datapoint_id")]

    # Optional: augment with lexical candidates from BigQuery SEARCH()
    if get_config("HYBRID_RETRIEVAL", False):
        try:
            bq_ids = get_bq_ids_for_query(query, limit=max(k, 50))
            neighbor_ids = list({*(str(x) for x in neighbor_ids), *map(str, bq_ids)})
        except Exception:
            # If BQ is not configured or SEARCH not available, ignore
            pass

    # Resolve documents via corpus repository (scalable backend)
    repo = get_corpus_repo()
    backend = str(get_config("CORPUS_BACKEND", "gcs_jsonl")).lower()
    entries: List[Dict[str, Any]] = []
    if backend in {"bq", "bigquery"} and not _bq_corpus_available():
        # Skip BQ lookup entirely; we'll fall back to live connectors
        entries = []
    else:
        try:
            entries = repo.get_docs_by_ids([str(i) for i in neighbor_ids])
        except Exception:
            entries = []

    # If mapping is empty or insufficient, fetch live data from connectors as a fallback
    live_docs: List[Document] = []
    live_persist_rows: List[Dict[str, str]] = []
    try:
        if not entries:
            # PubMed realtime
            try:
                from connectors.pubmed.connector import fetch_pubmed_data_realtime  # type: ignore
                pubmed = fetch_pubmed_data_realtime(query, max_results=max(k, 10)) or []
                for a in pubmed:
                    pmid = str(a.get("pmid", ""))
                    title = a.get("title", "")
                    abstract = a.get("abstract", "")
                    text = (title + "\n\n" + abstract).strip()
                    if text:
                        live_docs.append(
                            Document(
                                page_content=text,
                                metadata={
                                    "source": "pubmed_articles",
                                    "source_id": pmid,
                                    "source_type": "corpus",
                                    "priority": "live",
                                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid.isdigit() else "",
                                },
                            )
                        )
                        live_persist_rows.append({
                            "id": pmid or f"pmid-{hash(text) & 0xfffffff}",
                            "text": text,
                            "source": "pubmed_articles",
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid.isdigit() else "",
                        })
            except Exception:
                pass

            # UniProt realtime
            try:
                from connectors.uniprot.connector import fetch_uniprot_data_realtime  # type: ignore
                uniprot = fetch_uniprot_data_realtime(query, max_results=max(k, 10)) or []
                for p in uniprot:
                    acc = str(p.get("accession", ""))
                    pname = p.get("protein_name", "")
                    genes = p.get("genes", "")
                    seq = p.get("sequence", "")
                    # Keep sequence short to avoid context bloat
                    seq_snip = seq[:600]
                    text = (f"Protein: {pname}\nGenes: {genes}\n\nSequence (partial):\n{seq_snip}").strip()
                    if text:
                        live_docs.append(
                            Document(
                                page_content=text,
                                metadata={
                                    "source": "uniprot_records",
                                    "source_id": acc or p.get("uniprot_id", ""),
                                    "source_type": "corpus",
                                    "priority": "live",
                                    "url": f"https://www.uniprot.org/uniprotkb/{acc}/entry" if acc else "",
                                },
                            )
                        )
                        live_persist_rows.append({
                            "id": acc or p.get("uniprot_id", "") or f"uniprot-{hash(text) & 0xfffffff}",
                            "text": text,
                            "source": "uniprot_records",
                            "url": f"https://www.uniprot.org/uniprotkb/{acc}/entry" if acc else "",
                        })
            except Exception:
                pass

            # DrugBank local
            try:
                from connectors.drugbank.local_connector import fetch_drugbank_local  # type: ignore
                drugbank = await fetch_drugbank_local(query)
                for d in drugbank:
                    live_docs.append(d)
                    live_persist_rows.append({
                        "id": d.metadata.get("drug_id", ""),
                        "text": d.page_content,
                        "source": "drugbank_local",
                        "url": d.metadata.get("url", "")
                    })
            except Exception:
                pass

            # Best-effort persistence into BQ corpus for future queries
            try:
                if live_persist_rows:
                    upsert_corpus_rows(live_persist_rows)
            except Exception:
                pass
    except Exception:
        # Swallow any connector/persistence errors so core RAG flow continues
        pass

    # Optional filtering by mode/source before constructing Documents
    def _src(e: Dict[str, Any]) -> str:
        return str(e.get("metadata", {}).get("source", ""))

    if mode == "Scholar":
        entries = [e for e in entries if _src(e) in {"pubmed_articles", "uniprot_records"}]
    if source_filters:
        allow = set(source_filters)
        entries = [e for e in entries if _src(e) in allow]

    docs: List[Document] = [Document(page_content=e["text"], metadata=e["metadata"]) for e in entries]

    # Prepend any live documents to give them ordering priority (in addition to scoring boost)
    if live_docs:
        docs = [*live_docs, *docs]

    # Optionally include any uploaded extra texts as highest-priority docs
    if extra_texts:
        for idx, t in enumerate(extra_texts):
            if not t or not t.strip():
                continue
            docs.append(
                Document(
                    page_content=t.strip(),
                    metadata={
                        "source": "upload",
                        "source_id": f"upload-{idx+1}",
                        "source_type": "user_upload",
                        "priority": "upload",
                        "url": "",
                    },
                )
            )

    # Build diagnostics to help UI explain empty results
    backend = str(get_config("CORPUS_BACKEND", "gcs_jsonl")).lower()
    if backend in {"bq", "bigquery"}:
        corpus_source = "bq"
    elif corpus_uri and corpus_uri.startswith("gs://"):
        corpus_source = "gcs"
    else:
        corpus_source = "none"
    diagnostics = {
        "neighbors": len(neighbors),
        "neighbor_ids": len(neighbor_ids),
        "mapped_docs": len(docs),
        "corpus_source": corpus_source,
        "corpus_uri": corpus_uri or "",
        "uploaded_docs": len(extra_texts or []),
        "effective_model": gen_model,
        "hybrid": bool(get_config("HYBRID_RETRIEVAL", False)),
    }

    cm = ContextManager(max_context_length=int(get_config("RAG_MAX_CONTEXT_LENGTH", 1200)), project_id=project, location=location)
    scored = await _score_passages(cm, query, docs)
    selected_docs, provenance = cm.select_passages(scored, min_score_threshold=min_score_threshold)
    if not selected_docs:
        return {"response": "No relevant passages found.", "provenance": {"sources": []}, "diagnostics": diagnostics}

    t_retrieve = time.time()
    rg = ResponseGenerator(project_id=project, location=location, model_name=gen_model, temperature=temperature)
    generated = await rg.generate_response(query, selected_docs, provenance)
    validation = rg.validate_response(generated)
    enhanced = rg.enhance_response(generated, validation)
    t_gen = time.time()
    enhanced["diagnostics"] = {
        **diagnostics,
        "timings_ms": {
            "embed": int((t_embed - t0) * 1000),
            "retrieve": int((t_retrieve - t_embed) * 1000),
            "generate": int((t_gen - t_retrieve) * 1000),
            "total": int((t_gen - t0) * 1000),
        },
    }
    return enhanced
