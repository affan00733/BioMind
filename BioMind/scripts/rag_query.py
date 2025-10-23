#!/usr/bin/env python3
"""
End-to-end RAG runner for BioMind.

Usage:
  python scripts/rag_query.py "your question here" --k 8

Reads .env, retrieves top-k via Matching Engine, fetches texts from corpus map,
re-ranks/selects context, and generates an answer with citations using Gemini.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.config_utils import get_config
from utils.corpus_loader import load_corpus_map
from rag.matching_engine_client import MatchingEngineClient
from rag.context_manager import ContextManager
from rag.response_generator import ResponseGenerator
from langchain.schema import Document
from langchain_google_vertexai import VertexAIEmbeddings


def build_docs_from_ids(ids: List[str], corpus_map) -> List[Document]:
    docs: List[Document] = []
    for _id in ids:
        entry = corpus_map.get(str(_id))
        if not entry:
            continue
        docs.append(
            Document(page_content=entry["text"], metadata=entry["metadata"])
        )
    return docs


def main() -> int:
    load_dotenv()

    if len(sys.argv) == 1:
        print("Provide a query, e.g.: python scripts/rag_query.py 'How does tau aggregation progress?'\n")
        return 1

    parser = argparse.ArgumentParser(description="Run a RAG query against Matching Engine")
    parser.add_argument("query", type=str, help="User question")
    parser.add_argument("--k", type=int, default=int(get_config("MATCHING_ENGINE_NUM_NEIGHBORS", 8)), help="Top-k neighbors")
    args = parser.parse_args()

    project = os.getenv("GOOGLE_CLOUD_PROJECT") or get_config("PROJECT_ID")
    location = get_config("LOCATION", "us-central1")
    endpoint = get_config("MATCHING_ENGINE_INDEX_ENDPOINT")
    deployed_id = get_config("MATCHING_ENGINE_DEPLOYED_INDEX_ID")
    embedding_model = get_config("EMBEDDING_MODEL", "text-embedding-005")
    gen_model = get_config("GENERATION_MODEL", "gemini-2.5-flash-lite")

    if not project or not endpoint or not deployed_id:
        print("Missing required config: project/endpoint/deployed_id")
        return 2

    # Embed query
    embedder = VertexAIEmbeddings(project=project, location=location, model_name=embedding_model)
    qvec = embedder.embed_query(args.query)

    # Retrieve
    client = MatchingEngineClient(
        project=project,
        location=location,
        index_endpoint_name=endpoint,
        deployed_index_id=deployed_id,
    )
    neighbors = client.search(qvec, num_neighbors=args.k)
    if not neighbors:
        print("No neighbors found; check index content/deployment")
        return 3

    neighbor_ids = [n.get("datapoint_id") for n in neighbors if n.get("datapoint_id")]
    print(f"Retrieved {len(neighbor_ids)} neighbors: {neighbor_ids}")

    # Build documents from corpus map
    corpus_map = load_corpus_map()
    docs = build_docs_from_ids(neighbor_ids, corpus_map)
    if not docs:
        print("Could not map neighbor ids to corpus texts; ensure data/corpus.jsonl matches index ids.")
        return 4

    # Re-rank/select context
    cm = ContextManager(max_context_length=int(get_config("RAG_MAX_CONTEXT_LENGTH", 1200)), project_id=project, location=location)
    # score_passages is async; run via a simple event loop shim
    import asyncio

    async def do_score():
        return await cm.score_passages(args.query, docs)

    scored_passages = asyncio.run(do_score())
    selected_docs, provenance = cm.select_passages(scored_passages, min_score_threshold=float(get_config("RAG_MIN_SCORE_THRESHOLD", 0.4)))
    if not selected_docs:
        print("No passages passed the threshold; try lowering RAG_MIN_SCORE_THRESHOLD")
        return 5

    # Generate
    rg = ResponseGenerator(project_id=project, location=location, model_name=gen_model, temperature=float(get_config("RAG_TEMPERATURE", 0.3)))

    async def do_generate():
        return await rg.generate_response(args.query, selected_docs, provenance)

    generated = asyncio.run(do_generate())
    # Validate and enhance
    validation = rg.validate_response(generated)
    result = rg.enhance_response(generated, validation)

    # Print formatted output
    print("\n==== Answer ====")
    print(result["response"].strip())
    print("\n---- Sources ----")
    for s in result["provenance"]["sources"]:
        sid = s.get("source_id")
        meta = s.get("metadata", {})
        print(f"[{sid}] source={meta.get('source','')} score={s.get('score'):.3f}")

    # Optional validation summary
    if "validation" in result:
        v = result["validation"]
        print("\n---- Validation ----")
        print(f"passed={v.get('passed')} source_coverage={v.get('source_coverage'):.2f}")
        if v.get("warnings"):
            print("warnings:")
            for w in v["warnings"]:
                print(f" - {w}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
