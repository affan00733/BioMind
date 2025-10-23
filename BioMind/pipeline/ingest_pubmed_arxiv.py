from __future__ import annotations

import json
import os
import time
from typing import List, Dict, Any

import requests
import feedparser
from google.cloud import storage
from google.cloud import bigquery

from pipeline.schemas import Paper

# Minimal ingest for PubMed (via E-utilities) and arXiv (RSS/Atom) to demonstrate the pattern.
# Writes papers table rows and downloads PDFs to GCS when available.

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION", "us-central1")
DATASET = os.getenv("BQ_DATASET", "biomind_corpus")
PAPERS_TABLE = os.getenv("BQ_PAPERS_TABLE", "papers")
PDF_BUCKET = os.getenv("RAW_PDF_BUCKET")  # gs://bucket/prefix


def _parse_gs(uri: str) -> tuple[str, str]:
    assert uri.startswith("gs://")
    b, _, p = uri[5:].partition("/")
    return b, p


def _safe_get(d: Dict, *keys, default=""):
    for k in keys:
        d = d.get(k, {}) if isinstance(d, dict) else {}
    return d or default


def ingest_arxiv(category: str = "cs.CL", max_results: int = 50) -> List[Paper]:
    url = f"http://export.arxiv.org/api/query?search_query=cat:{category}&start=0&max_results={max_results}"
    feed = feedparser.parse(url)
    papers: List[Paper] = []
    for entry in feed.entries:
        pid = entry.get("id")
        title = entry.get("title", "").strip()
        summary = entry.get("summary", "").strip()
        link = entry.get("link")
        pdf_link = None
        for l in entry.get("links", []):
            if l.get("type") == "application/pdf":
                pdf_link = l.get("href")
                break
        authors = [a.get("name") for a in entry.get("authors", []) if a.get("name")]
        papers.append(Paper(
            id=pid,
            title=title,
            abstract=summary,
            doi=None,
            source="arxiv",
            url=link,
            published=entry.get("published"),
            journal="arXiv",
            authors=authors,
            pdf_gcs_uri=None,
        ))
    return papers


def ingest_pubmed(term: str = "cancer", retmax: int = 50) -> List[Paper]:
    # ESearch -> ESummary for basic fields
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    es = requests.get(f"{base}/esearch.fcgi", params={"db": "pubmed", "term": term, "retmode": "json", "retmax": retmax})
    ids = es.json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    esum = requests.get(f"{base}/esummary.fcgi", params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"})
    result = esum.json().get("result", {})
    papers: List[Paper] = []
    for pid in ids:
        r = result.get(pid, {})
        title = r.get("title", "")
        journal = _safe_get(r, "fulljournalname")
        pubdate = _safe_get(r, "pubdate")
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"
        # PDF URL resolution can be complex; often via PMC. We store metadata now.
        papers.append(Paper(
            id=str(pid),
            title=title,
            abstract="",
            doi=_safe_get(r, "elocationid"),
            source="pubmed",
            url=url,
            published=pubdate,
            journal=journal,
            authors=[a.get("name") for a in r.get("authors", []) if a.get("name")],
            pdf_gcs_uri=None,
        ))
    return papers


def download_pdf_to_gcs(http_url: str, bucket_uri: str, rel_name: str) -> str | None:
    if not bucket_uri or not bucket_uri.startswith("gs://"):
        return None
    try:
        r = requests.get(http_url, timeout=30)
        if r.status_code != 200 or not r.content:
            return None
        b, p = _parse_gs(bucket_uri)
        if p and not p.endswith("/"):
            p += "/"
        dest = f"{p}raw_pdfs/{int(time.time())}-{os.path.basename(rel_name)}.pdf"
        storage.Client().bucket(b).blob(dest).upload_from_string(r.content, content_type="application/pdf")
        return f"gs://{b}/{dest}"
    except Exception:
        return None


def upsert_papers_bq(dataset: str, table: str, papers: List[Paper]) -> int:
    client = bigquery.Client()
    rows = [p.to_bq() for p in papers]
    if not rows:
        return 0
    table_id = f"{dataset}.{table}"
    errors = client.insert_rows_json(table_id, rows)
    if errors:
        # Best-effort insert
        pass
    return len(rows)


# Cloud Run style HTTP server to trigger via Scheduler
from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/run")
async def run(request: Request):
    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    source = body.get("source", "pubmed_arxiv")
    term = body.get("term", "cancer")
    arxiv_cat = body.get("arxiv_category", "q-bio.BM")
    retmax = int(body.get("retmax", 25))

    papers: List[Paper] = []
    if source in ("pubmed", "pubmed_arxiv", "all"):
        papers += ingest_pubmed(term=term, retmax=retmax)
    if source in ("arxiv", "pubmed_arxiv", "all"):
        papers += ingest_arxiv(category=arxiv_cat, max_results=retmax)

    # Optionally try to download PDFs for arXiv entries only (direct link available)
    if PDF_BUCKET:
        for p in papers:
            if p.source == "arxiv":
                # arXiv id is URL; we look for a pdf link again
                try:
                    feed = feedparser.parse(p.id)
                    pdf_link = None
                    for l in feed.entries[0].get("links", []):
                        if l.get("type") == "application/pdf":
                            pdf_link = l.get("href")
                            break
                    if pdf_link:
                        gcs_uri = download_pdf_to_gcs(pdf_link, PDF_BUCKET, rel_name=p.id.split("/")[-1])
                        if gcs_uri:
                            p.pdf_gcs_uri = gcs_uri
                except Exception:
                    pass

    inserted = upsert_papers_bq(DATASET, PAPERS_TABLE, papers)
    return JSONResponse({"inserted_rows": inserted, "papers": len(papers)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
