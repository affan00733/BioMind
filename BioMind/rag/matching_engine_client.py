"""
Thin wrapper around Vertex AI Matching Engine Index Endpoint search.

Requires an existing Index Endpoint with a deployed index. We do not create
or upload datapoints here—only query. Configuration comes from config_utils.
"""

from __future__ import annotations

from typing import List, Dict, Any
import logging
import time
import random

from google.cloud import aiplatform


class MatchingEngineClient:
    def __init__(
        self,
        project: str,
        location: str,
        index_endpoint_name: str,
        deployed_index_id: str,
    ) -> None:
        self.project = project
        self.location = location
        self.index_endpoint_name = index_endpoint_name
        self.deployed_index_id = deployed_index_id

        aiplatform.init(project=project, location=location)
        self.index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
            index_endpoint_name
        )

    def search(
        self,
        query_embedding: List[float],
        num_neighbors: int = 10,
        max_retries: int = 3,
        initial_backoff: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Search nearest neighbors by embedding.

        Returns a list of matches with 'distance' and 'datapoint_id' and metadata
        if available. We normalize response to a simple dict list.
        """
        attempt = 0
        backoff = initial_backoff
        while True:
            try:
                # aiplatform returns List[List[MatchNeighbor]] for public endpoints
                results = self.index_endpoint.find_neighbors(
                    deployed_index_id=self.deployed_index_id,
                    queries=[query_embedding],
                    num_neighbors=num_neighbors,
                )

                out: List[Dict[str, Any]] = []
                if not results:
                    return out
                neighbors = results[0] or []
                for n in neighbors:
                    # MatchNeighbor has fields: id, distance, and optional restricts via from_index_datapoint
                    item = {
                        "datapoint_id": getattr(n, "id", None),
                        "distance": getattr(n, "distance", 0.0),
                        "metadata": {},
                    }
                    # Populate restrict metadata if present
                    try:
                        restricts = getattr(n, "restricts", None)
                        if restricts:
                            item["metadata"] = {r.name: list(r.allow_tokens) for r in restricts}
                    except Exception:
                        pass
                    out.append(item)
                return out
            except Exception as e:
                attempt += 1
                logging.warning(
                    f"Matching Engine search attempt {attempt} failed: {e}"
                )
                if attempt > max_retries:
                    logging.error("Matching Engine search failed after retries; returning empty list")
                    return []
                # Exponential backoff with jitter
                sleep_s = backoff * (1 + random.random())
                time.sleep(sleep_s)
                backoff *= 2
