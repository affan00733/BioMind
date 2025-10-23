#!/usr/bin/env python3
"""
Create and deploy a Vertex AI Matching Engine (Vector Search) index from datapoints stored in GCS.

Prereqs:
- Datapoints JSONL uploaded to a GCS folder (e.g., gs://bucket/prefix/datapoints.jsonl)
- Vertex AI API enabled and ADC configured (gcloud auth application-default login)

This script will:
1) Create a Matching Engine Index (Tree-AH) using the GCS folder as contents_delta_uri
2) Create a Matching Engine Index Endpoint (or reuse an existing one if provided)
3) Deploy the index to the endpoint
4) Print the endpoint resource name and deployed index id for application config
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from google.cloud import aiplatform


def create_index(
    project: str,
    location: str,
    display_name: str,
    gcs_folder: str,
    dimensions: int = 768,
    neighbors: int = 50,
    distance_measure_type: str = "COSINE_DISTANCE",
) -> aiplatform.MatchingEngineIndex:
    aiplatform.init(project=project, location=location)
    if not gcs_folder.endswith("/"):
        gcs_folder = gcs_folder + "/"

    index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=display_name,
        contents_delta_uri=gcs_folder,
        dimensions=dimensions,
        approximate_neighbors_count=neighbors,
        distance_measure_type=distance_measure_type,
    )
    return index


def get_or_create_endpoint(
    project: str,
    location: str,
    endpoint_name: Optional[str],
    endpoint_display_name: str,
    public_endpoint_enabled: bool = True,
    enable_private_service_connect: bool = False,
    network: Optional[str] = None,
) -> aiplatform.MatchingEngineIndexEndpoint:
    aiplatform.init(project=project, location=location)
    if endpoint_name:
        # If a full resource name is provided, attach to it
        return aiplatform.MatchingEngineIndexEndpoint(endpoint_name)
    # Otherwise create a new endpoint
    create_kwargs = {
        "display_name": endpoint_display_name,
    }
    if public_endpoint_enabled:
        create_kwargs["public_endpoint_enabled"] = True
    elif enable_private_service_connect:
        create_kwargs["enable_private_service_connect"] = True
    elif network:
        create_kwargs["network"] = network

    endpoint = aiplatform.MatchingEngineIndexEndpoint.create(**create_kwargs)
    return endpoint


def deploy_index(
    index: aiplatform.MatchingEngineIndex,
    endpoint: aiplatform.MatchingEngineIndexEndpoint,
    deployed_index_id: str,
    machine_type: str = "e2-standard-2",
):
    # Deploy the index to the endpoint. This returns a long-running operation.
    operation = endpoint.deploy_index(
        index=index,
        deployed_index_id=deployed_index_id,
        machine_type=machine_type,
        sync=True,
    )
    return operation


def main() -> int:
    parser = argparse.ArgumentParser(description="Create and deploy Vertex AI Vector Search index")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--location", default=os.getenv("LOCATION", "us-central1"), help="Region (e.g., us-central1)")
    parser.add_argument("--gcs-folder", required=False, help="gs://bucket/prefix/ containing datapoints.json (when creating a new index)")
    parser.add_argument("--index-resource", default=None, help="Existing Matching Engine Index resource name to reuse (projects/.../indexes/ID)")
    parser.add_argument("--index-name", default="biomind-index", help="Display name for the index")
    parser.add_argument("--endpoint-name", default=None, help="Existing Index Endpoint resource name to reuse (optional)")
    parser.add_argument("--endpoint-display-name", default="biomind-index-endpoint", help="Display name if creating a new endpoint")
    parser.add_argument("--deployed-index-id", default="biomind_deployed_index", help="Deployed index ID on the endpoint")
    # Endpoint options
    parser.add_argument("--public-endpoint", action="store_true", default=True, help="Create a public endpoint (default)")
    parser.add_argument("--no-public-endpoint", dest="public_endpoint", action="store_false", help="Do not create a public endpoint")
    parser.add_argument("--enable-psc", action="store_true", default=False, help="Enable Private Service Connect endpoint")
    parser.add_argument("--network", default=None, help="VPC network for Private Service Access (if using PSA)")
    parser.add_argument("--dimensions", type=int, default=int(os.getenv("EMBEDDING_DIMENSIONS", 768)), help="Embedding dimensions")
    parser.add_argument("--neighbors", type=int, default=50, help="Approximate neighbors count")
    parser.add_argument("--distance", default=os.getenv("VS_DISTANCE", "COSINE_DISTANCE"), help="Distance type: COSINE_DISTANCE | SQUARED_L2_DISTANCE | DOT_PRODUCT_DISTANCE")
    parser.add_argument("--machine-type", default=os.getenv("VS_MACHINE_TYPE", "e2-standard-16"), help="Machine type for deployment")

    args = parser.parse_args()

    if args.index_resource:
        index = aiplatform.MatchingEngineIndex(args.index_resource)
        print(f"Using existing index: {index.resource_name}")
    else:
        if not args.gcs_folder:
            print("--gcs-folder is required when not using --index-resource", file=sys.stderr)
            return 2
        print(f"Creating index '{args.index_name}' from {args.gcs_folder} in {args.project}/{args.location}...")
        index = create_index(
            project=args.project,
            location=args.location,
            display_name=args.index_name,
            gcs_folder=args.gcs_folder,
            dimensions=args.dimensions,
            neighbors=args.neighbors,
            distance_measure_type=args.distance,
        )
        print(f"Index created: {index.resource_name}")

    endpoint = get_or_create_endpoint(
        project=args.project,
        location=args.location,
        endpoint_name=args.endpoint_name,
        endpoint_display_name=args.endpoint_display_name,
        public_endpoint_enabled=args.public_endpoint,
        enable_private_service_connect=args.enable_psc,
        network=args.network,
    )
    print(f"Using endpoint: {endpoint.resource_name}")

    print(f"Deploying index to endpoint with deployed_index_id='{args.deployed_index_id}'...")
    deploy_index(index=index, endpoint=endpoint, deployed_index_id=args.deployed_index_id, machine_type=args.machine_type)
    print("Deployment completed.")

    print("\nConfigure your app with:")
    print(f"MATCHING_ENGINE_ENABLED=true")
    print(f"MATCHING_ENGINE_INDEX_ENDPOINT={endpoint.resource_name}")
    print(f"MATCHING_ENGINE_DEPLOYED_INDEX_ID={args.deployed_index_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
