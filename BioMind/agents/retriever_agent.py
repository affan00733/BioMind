"""Retriever Agent."""

import logging
import asyncio
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional

from langchain_google_vertexai import VertexAIEmbeddings

from utils.config_utils import get_config
from rag.matching_engine_client import MatchingEngineClient
from utils.cache_utils import api_cache

import connectors.pubmed.connector as pubmed_connector
import connectors.uniprot.connector as uniprot_connector
import connectors.drugbank.connector as drugbank_connector
import connectors.google_health_blog.connector as google_health_connector


class RetrieverAgent:
    """Handles retrieval of biomedical information."""
    
    def __init__(self):
        """Initialize agent."""
        # Ensure .env is loaded for env-based config
        try:
            load_dotenv()
        except Exception:
            pass
        # Standardized config keys with backward-compatible fallbacks
        self.project_id = (
            get_config("PROJECT_ID")
            or get_config("GCP_PROJECT_ID")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
        )
        self.location = (
            get_config("LOCATION", "us-central1")
            or get_config("GCP_LOCATION", "us-central1")
        )
        self.embeddings = VertexAIEmbeddings(
            project=self.project_id,
            location=self.location,
            model_name=get_config("EMBEDDING_MODEL", "textembedding-gecko@latest")
        )
        self.vectors = []
        self.documents = []
        # Managed Vector Search (aka Matching Engine) - optional
        self.me_enabled = (
            get_config("MATCHING_ENGINE_ENABLED", False)
            or get_config("VECTOR_SEARCH_ENABLED", False)
        )
        self.me_client = None
        if self.me_enabled:
            try:
                me_endpoint = (
                    get_config("MATCHING_ENGINE_INDEX_ENDPOINT", "")
                    or get_config("VECTOR_SEARCH_INDEX_ENDPOINT", "")
                )
                me_deployed = (
                    get_config("MATCHING_ENGINE_DEPLOYED_INDEX_ID", "")
                    or get_config("VECTOR_SEARCH_DEPLOYED_INDEX_ID", "")
                )
                if me_endpoint and me_deployed:
                    # Use PROJECT_ID/LOCATION if explicitly set; else fall back to initialized values
                    me_project = get_config("PROJECT_ID") or self.project_id
                    me_location = get_config("LOCATION", self.location)
                    self.me_client = MatchingEngineClient(
                        project=me_project,
                        location=me_location,
                        index_endpoint_name=me_endpoint,
                        deployed_index_id=me_deployed,
                    )
                    logging.info("Matching Engine client initialized")
                else:
                    logging.warning(
                        "Vector Search (Matching Engine) enabled but INDEX_ENDPOINT/DEPLOYED_INDEX_ID not set; skipping ME search"
                    )
                    self.me_enabled = False
            except Exception as e:
                logging.error(f"Failed to initialize Matching Engine client: {e}")
                self.me_enabled = False
        
    async def retrieve_relevant_docs(self, query: str) -> List[Dict]:
        """Get relevant documents from multiple sources.
        
        Args:
            query: The search query string
            
        Returns:
            List of dictionaries containing relevant documents with scores
        """
        self.vectors = []
        self.documents = []
        
        # Optional: first search managed Matching Engine
        me_hits: List[Dict] = []
        if self.me_enabled and self.me_client:
            try:
                qv = await self.embeddings.aembed_query(query)
                # L2-normalize query vector to use with DOT_PRODUCT/Euclidean metrics equivalently to cosine
                try:
                    import math
                    n = math.sqrt(sum(x*x for x in qv)) or 1.0
                    qv = [x / n for x in qv]
                except Exception:
                    pass
                k = get_config("MATCHING_ENGINE_NUM_NEIGHBORS", 10)
                me_neighbors = self.me_client.search(qv, num_neighbors=k)
                # Map ME results to our schema; many deployments don't return raw content
                for n in me_neighbors:
                    meta = n.get("metadata", {}) or {}
                    content = meta.get("content", "")
                    me_hits.append({
                        "source": "matching_engine",
                        "content": content,
                        "metadata": meta,
                        "search_score": 1.0 - float(n.get("distance", 0.0)),
                    })
                logging.info(f"Matching Engine returned {len(me_hits)} hits")
            except Exception as e:
                logging.error(f"Matching Engine search failed: {e}")

        # Gather data from live sources
        documents = []
        try:
            # PubMed articles
            if os.getenv("ENABLE_PUBMED", str(get_config("ENABLE_PUBMED", True))).lower() == "true":
                pubmed_results = pubmed_connector.fetch_pubmed_data_realtime(query)
                for item in pubmed_results:
                    content = f'''Title: {item.get('title', '')}
Abstract: {item.get('abstract', '')}
Authors: {item.get('authors', '')}
Journal: {item.get('journal', '')}
Publication Date: {item.get('pub_date', '')}'''
                    documents.append({
                        "source": "pubmed",
                        "content": content,
                        "metadata": item
                    })
            
            # UniProt protein data
            if os.getenv("ENABLE_UNIPROT", str(get_config("ENABLE_UNIPROT", True))).lower() == "true":
                uniprot_results = uniprot_connector.fetch_uniprot_data_realtime(query)
                for item in uniprot_results:
                    content = f'''Protein: {item.get('protein_name', '')}
Description: {item.get('description', '')}
Function: {item.get('function', '')}
Gene: {item.get('gene', '')}
Organism: {item.get('organism', '')}'''
                    documents.append({
                        "source": "uniprot",
                        "content": content,
                        "metadata": item
                    })
                    
            # DrugBank data
            if os.getenv("ENABLE_DRUGBANK", str(get_config("ENABLE_DRUGBANK", False))).lower() == "true":
                drugbank_results = drugbank_connector.fetch_drugbank_data_realtime(query)
                for item in drugbank_results:
                    content = f'''Drug: {item.get('name', '')}
Description: {item.get('description', '')}
Mechanism: {item.get('mechanism', '')}
Category: {item.get('category', '')}
Indication: {item.get('indication', '')}'''
                    documents.append({
                        "source": "drugbank",
                        "content": content,
                        "metadata": item
                    })
                    
            # Google Health blog posts
            # Honor the connector's config flag name and .env value
            enable_google_health = os.getenv("ENABLE_GOOGLE_HEALTH_BLOG", str(get_config("ENABLE_GOOGLE_HEALTH_BLOG", False))).lower() == "true"
            if enable_google_health:
                blog_results = google_health_connector.fetch_blog_data_realtime(query)
                for item in blog_results:
                    content = f'''Title: {item.get('title', '')}
Summary: {item.get('summary', '')}
Category: {item.get('category', '')}
Published Date: {item.get('pub_date', '')}'''
                    documents.append({
                        "source": "google_health",
                        "content": content,
                        "metadata": item
                    })
        except Exception as e:
            logging.error(f"Error fetching data: {str(e)}", exc_info=True)
            return []
            
        if not documents and not me_hits:
            logging.info("No documents found for query")
            return []

        # Combine and de-duplicate: prefer managed ME hits, then live
        combined = me_hits + documents
        # Generate embeddings for combined set; skip items without content (e.g., bare ME neighbors)
        for doc in combined:
            if not doc.get("content"):
                continue
            try:
                vector = await self.embeddings.aembed_query(doc["content"])
                self.vectors.append(vector)
                self.documents.append(doc)
            except Exception as e:
                logging.error(f"Error generating embedding for {doc['source']}: {str(e)}", exc_info=True)
                continue
                
        if not self.vectors:
            logging.warning("No embeddings generated for any documents")
            return []
                
        # Calculate similarity scores
        try:
            query_vector = await self.embeddings.aembed_query(query)
            similarities = []
            
            for doc_vector in self.vectors:
                dot_product = sum(a * b for a, b in zip(query_vector, doc_vector))
                norm1 = sum(a * a for a in query_vector) ** 0.5
                norm2 = sum(b * b for b in doc_vector) ** 0.5
                similarity = dot_product / (norm1 * norm2) if norm1 and norm2 else 0
                similarities.append(similarity)
                
            # Sort by similarity
            results = []
            sorted_indices = sorted(range(len(similarities)), 
                                  key=lambda i: similarities[i],
                                  reverse=True)
                                  
            for i in sorted_indices:
                doc = self.documents[i]
                results.append({
                    "source": doc["source"],
                    "source_id": i,
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "search_score": similarities[i]
                })
                
            logging.info(f"Found {len(results)} relevant documents")
            return results
            
        except Exception as e:
            logging.error(f"Error calculating similarities: {str(e)}", exc_info=True)
            return []
