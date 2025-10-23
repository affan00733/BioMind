from __future__ import annotations

from typing import List, Dict, Any
import os

from google.cloud import bigquery
from langchain_google_vertexai import VertexAIEmbeddings

from rag.matching_engine_client import MatchingEngineClient


def bq_search(dataset: str, chunks_table: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
    client = bigquery.Client()
    sql = f"""
    SELECT id, paper_id, text, url, 
           SAFE_DIVIDE(SEARCH(ARRAY[STRUCT('text' AS field, text AS value)], @q).score, 100) AS lexical_score
    FROM `{dataset}.{chunks_table}`
    WHERE SEARCH(ARRAY[STRUCT('text' AS field, text AS value)], @q).score > 0
    ORDER BY lexical_score DESC
    LIMIT {limit}
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("q", "STRING", query)]
    )
    rows = client.query(sql, job_config=job_config).result()
    return [dict(r) for r in rows]


def vector_search(project: str, location: str, endpoint: str, deployed_id: str, embed_model: str, query: str, k: int = 50) -> List[Dict[str, Any]]:
    embedder = VertexAIEmbeddings(project=project, location=location, model_name=embed_model)
    qvec = embedder.embed_query(query)
    client = MatchingEngineClient(project=project, location=location, index_endpoint_name=endpoint, deployed_index_id=deployed_id)
    neighbors = client.search(qvec, num_neighbors=k)
    # return as dicts with id and score
    out: List[Dict[str, Any]] = []
    for n in neighbors:
        out.append({
            "id": n.get("datapoint_id"),
            "vector_score": float(n.get("distance", 0.0)),
        })
    return out


def hybrid(query: str, k: int = 50) -> List[Dict[str, Any]]:
    dataset = os.getenv("BQ_DATASET", "biomind_corpus")
    chunks_table = os.getenv("BQ_CHUNKS_TABLE", "chunks")
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION", "us-central1")
    endpoint = os.getenv("MATCHING_ENGINE_INDEX_ENDPOINT")
    deployed_id = os.getenv("MATCHING_ENGINE_DEPLOYED_INDEX_ID")
    embed_model = os.getenv("EMBEDDING_MODEL", "text-embedding-005")

    lexical = bq_search(dataset, chunks_table, query, limit=k)
    vector = vector_search(project, location, endpoint, deployed_id, embed_model, query, k=k)

    # Simple merge: keep a dict by id with combined score
    merged: Dict[str, Dict[str, Any]] = {}
    for l in lexical:
        merged[l["id"]] = {"id": l["id"], "lexical_score": float(l.get("lexical_score", 0.0)), "vector_score": 0.0}
    for v in vector:
        m = merged.get(v["id"]) or {"id": v["id"], "lexical_score": 0.0}
        m["vector_score"] = float(v.get("vector_score", 0.0))
        merged[v["id"]] = m

    # Combine by a weighted sum (tune weights)
    results = list(merged.values())
    for r in results:
        # Note: vector_score here is a distance; if ME returns similarity adjust accordingly
        r["score"] = 0.6 * (1.0 - r.get("vector_score", 1.0)) + 0.4 * r.get("lexical_score", 0.0)
    results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return results[:k]


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "glioblastoma EGFR inhibition"
    res = hybrid(q, k=50)
    print({"results": len(res)})
