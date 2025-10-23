"""Upsert datapoints JSONL parts from GCS into a deployed Matching Engine index.

This script expects the following env vars (same as other pipeline scripts):
- GOOGLE_CLOUD_PROJECT
- LOCATION (e.g., us-central1)
- DATAPOINTS_GCS (gs://bucket/prefix/datapoints.jsonl)
- MATCHING_ENGINE_INDEX_ENDPOINT
- MATCHING_ENGINE_DEPLOYED_INDEX_ID

It will list matching part files under DATAPOINTS_GCS (looking for .partNNNN.jsonl) and
upsert datapoints in batches.
"""
from __future__ import annotations

import os
import json
import re
from typing import List, Dict

from google.cloud import storage
from google.cloud import aiplatform
from google.cloud import aiplatform_v1 as gapic_aiplatform
import time
import random

PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("LOCATION", "us-central1")
DATAPOINTS_GCS = os.getenv("DATAPOINTS_GCS", "")
INDEX_ENDPOINT = os.getenv("MATCHING_ENGINE_INDEX_ENDPOINT")
DEPLOYED_INDEX_ID = os.getenv("MATCHING_ENGINE_DEPLOYED_INDEX_ID")
# Optional: full index resource name required for datapoint upserts (projects/.../locations/.../indexes/ID)
INDEX_NAME = os.getenv("MATCHING_ENGINE_INDEX_NAME")
RAG_INDEX_NAME = os.getenv("RAG_INDEX_NAME")
BATCH_SIZE = int(os.getenv("UPsert_BATCH_SIZE", "500"))
RETRY_MAX = int(os.getenv("UPsert_RETRY_MAX", "5"))
RETRY_BASE_SECONDS = float(os.getenv("UPsert_RETRY_BASE_SECONDS", "2"))
SLEEP_BETWEEN_PARTS = float(os.getenv("UPsert_SLEEP_BETWEEN_PARTS", "1"))

PART_RE = re.compile(r"\.part(\d{4})\.jsonl$")


def list_parts(gcs_uri: str) -> List[str]:
    if not gcs_uri.startswith("gs://"):
        return []
    client = storage.Client()
    bucket_name, _, prefix = gcs_uri[5:].partition("/")
    bucket = client.bucket(bucket_name)
    blobs = list(client.list_blobs(bucket_name, prefix=prefix))
    parts = [b.name for b in blobs if PART_RE.search(b.name)]
    parts.sort()
    return [f"gs://{bucket_name}/{p}" for p in parts]


def download_blob_to_text(gcs_uri: str) -> str:
    client = storage.Client()
    bucket_name, _, path = gcs_uri[5:].partition("/")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path)
    return blob.download_as_text()


def upsert_part_to_matching_engine(part_gcs: str):
    text = download_blob_to_text(part_gcs)
    lines = [l for l in text.splitlines() if l.strip()]
    datapoints = [json.loads(l) for l in lines]
    # We'll use the IndexServiceClient.upsert_datapoints GAPIC method which operates on Index resources.
    # Initialize GAPIC IndexServiceClient with region-specific endpoint to avoid "global" region errors
    api_endpoint = f"{LOCATION}-aiplatform.googleapis.com"
    client = gapic_aiplatform.IndexServiceClient(client_options={"api_endpoint": api_endpoint})

    # Discover index resource if not provided
    index_resource = INDEX_NAME
    if not index_resource:
        # Try to find by RAG_INDEX_NAME display name
        if RAG_INDEX_NAME:
            parent = f"projects/{PROJECT}/locations/{LOCATION}"
            try:
                for idx in client.list_indexes(parent=parent):
                    if getattr(idx, "display_name", "") == RAG_INDEX_NAME:
                        index_resource = idx.name
                        break
            except Exception as e:
                print(f"Index discovery failed: {e}")
                index_resource = None

    # Fallback: if we have an Index Endpoint and a deployed index id, try to read the endpoint
    # and map the deployed index to its backing index resource name.
    if not index_resource and INDEX_ENDPOINT and DEPLOYED_INDEX_ID:
        try:
            aiplatform.init(project=PROJECT, location=LOCATION)
            ep = aiplatform.MatchingEngineIndexEndpoint(INDEX_ENDPOINT)
            for di in getattr(ep, "deployed_indexes", []) or []:
                # deployed index object may have id and index fields
                di_id = getattr(di, "id", None) or getattr(di, "deployed_index_id", None)
                if str(di_id) == str(DEPLOYED_INDEX_ID):
                    # Try to get backing index resource
                    index_ref = getattr(di, "index", None) or getattr(di, "index_id", None)
                    if index_ref:
                        # index_ref may be a resource name or an ID
                        if isinstance(index_ref, str) and index_ref.startswith("projects/"):
                            index_resource = index_ref
                        else:
                            # construct full resource path
                            index_resource = f"projects/{PROJECT}/locations/{LOCATION}/indexes/{index_ref}"
                        break
        except Exception as e:
            print(f"Index endpoint discovery failed: {e}")

    if not index_resource:
        raise RuntimeError("Could not determine the Index resource name. Set MATCHING_ENGINE_INDEX_NAME or RAG_INDEX_NAME in env.")

    # Build IndexDatapoint objects expected by GAPIC
    for i in range(0, len(datapoints), BATCH_SIZE):
        batch = datapoints[i : i + BATCH_SIZE]
        datapoint_messages = []
        for d in batch:
            vec = d.get("embedding")
            if not isinstance(vec, list):
                continue
            # Build the IndexDatapoint proto mapping
            dp = gapic_aiplatform.IndexDatapoint(
                datapoint_id=str(d.get("id")),
                feature_vector=list(vec),
            )
            # attributes
            attrs = d.get("attributes") or {}
            if attrs:
                # IndexDatapoint 'attributes' is a Struct-like proto; set via a dict on creation
                try:
                    dp.attributes.update({k: str(v) for k, v in attrs.items()})
                except Exception:
                    pass
            # restricts: pass-through if present
            if d.get("restricts"):
                try:
                    # If restricts is a mapping of tokens, attach as-is where supported
                    dp.restricts.extend(d.get("restricts") if isinstance(d.get("restricts"), list) else [d.get("restricts")])
                except Exception:
                    pass
            datapoint_messages.append(dp)

        if not datapoint_messages:
            continue

        request = gapic_aiplatform.UpsertDatapointsRequest(
            index=index_resource,
            datapoints=datapoint_messages,
        )
        # retry with exponential backoff for transient errors (e.g., 429 quota)
        attempt = 0
        while attempt <= RETRY_MAX:
            try:
                resp = client.upsert_datapoints(request=request)
                print(f"Upserted {len(datapoint_messages)} datapoints to index {index_resource}")
                break
            except Exception as e:
                attempt += 1
                # If we've exhausted retries, bubble up the failure for this part
                if attempt > RETRY_MAX:
                    print(f"Failed upsert for {part_gcs} after {RETRY_MAX} retries: {e}")
                    break
                # backoff with jitter
                backoff = RETRY_BASE_SECONDS * (2 ** (attempt - 1))
                jitter = random.uniform(0, backoff * 0.25)
                sleep_for = backoff + jitter
                print(f"Upsert attempt {attempt} failed for {part_gcs}: {e}. Retrying in {sleep_for:.1f}s...")
                time.sleep(sleep_for)
        # small throttle between batches to avoid hitting per-minute throughput too fast
        time.sleep(0.01)


if __name__ == "__main__":
    if not DATAPOINTS_GCS:
        print("Set DATAPOINTS_GCS environment variable to the GCS prefix where parts live")
        raise SystemExit(1)
    if not INDEX_ENDPOINT or not DEPLOYED_INDEX_ID:
        print("Set MATCHING_ENGINE_INDEX_ENDPOINT and MATCHING_ENGINE_DEPLOYED_INDEX_ID environment variables")
        raise SystemExit(1)

    parts = list_parts(DATAPOINTS_GCS)
    if not parts:
        print("No datapoint parts found at", DATAPOINTS_GCS)
        raise SystemExit(0)

    for p in parts:
        upsert_part_to_matching_engine(p)
        # sleep between parts to reduce per-minute throughput pressure
        time.sleep(SLEEP_BETWEEN_PARTS)
