from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, List

# BigQuery tables (logical schema; create externally via bq or python client)
# dataset.papers(id STRING, title STRING, abstract STRING, doi STRING, source STRING, url STRING,
#                published DATE, journal STRING, authors ARRAY<STRING>, pdf_gcs_uri STRING,
#                created_at TIMESTAMP, updated_at TIMESTAMP)
#
# dataset.chunks(id STRING, paper_id STRING, section STRING, position INT64,
#                text STRING, token_count INT64, url STRING, created_at TIMESTAMP)

@dataclass
class Paper:
    id: str
    title: str
    abstract: str
    doi: Optional[str]
    source: str  # pubmed|arxiv|biorxiv|...
    url: Optional[str]
    published: Optional[str]
    journal: Optional[str]
    authors: Optional[List[str]]
    pdf_gcs_uri: Optional[str]

    def to_bq(self) -> Dict:
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "doi": self.doi or "",
            "source": self.source,
            "url": self.url or "",
            "published": self.published,
            "journal": self.journal or "",
            "authors": self.authors or [],
            "pdf_gcs_uri": self.pdf_gcs_uri or "",
        }

@dataclass
class Chunk:
    id: str
    paper_id: str
    section: str
    position: int
    text: str
    token_count: int
    url: Optional[str]

    def to_bq(self) -> Dict:
        return {
            "id": self.id,
            "paper_id": self.paper_id,
            "section": self.section,
            "position": self.position,
            "text": self.text,
            "token_count": self.token_count,
            "url": self.url or "",
        }
