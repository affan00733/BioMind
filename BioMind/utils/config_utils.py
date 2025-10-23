"""
Enhanced configuration utilities for BioMind Voice Lab.
Provides centralized access to environment variables and default settings.
"""

import os
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger()

class Config:
    """Configuration manager for BioMind."""
    
    DEFAULTS = {
        # Google Cloud settings
        "PROJECT_ID": "trusty-frame-474816-m0",
        "LOCATION": "us-central1",
        
        # RAG settings
        "RAG_INDEX_NAME": "biomind-search-index",
        "RAG_MAX_CONTEXT_LENGTH": 4000,
        "RAG_MIN_SCORE_THRESHOLD": 0.5,
        "RAG_TEMPERATURE": 0.3,

        # Persistent vector store (deprecated; set false to disable)
        "ENABLE_PERSISTENT_INDEX": False,
        "PERSISTENT_INDEX_PATH": "data/vector_store/store.npz",

        # Vertex AI Matching Engine (managed vector search)
        "MATCHING_ENGINE_ENABLED": False,
        # Full resource name: projects/{project}/locations/{location}/indexEndpoints/{id}
        "MATCHING_ENGINE_INDEX_ENDPOINT": "",
    # Full index resource name for upserts: projects/{project}/locations/{location}/indexes/{id}
    "MATCHING_ENGINE_INDEX_NAME": "",
        # The deployed index ID within the endpoint
        "MATCHING_ENGINE_DEPLOYED_INDEX_ID": "",
        # Default neighbors to retrieve per query
        "MATCHING_ENGINE_NUM_NEIGHBORS": 10,
        
    # Model names
    "EMBEDDING_MODEL": "text-embedding-005",
        "GENERATION_MODEL": "gemini-2.5-flash-lite",
        
        # Connector flags
        "ENABLE_PUBMED": True,
        "ENABLE_UNIPROT": True,
        "ENABLE_DRUGBANK": False,
        "ENABLE_GOOGLE_HEALTH_BLOG": False,

    # Optional remote corpus location (e.g., gs://bucket/path/corpus.jsonl)
    "CORPUS_URI": "",
    # BigQuery corpus tables
    "BQ_DATASET": "biomind_corpus",
    "BQ_PAPERS_TABLE": "papers",
    "BQ_CHUNKS_TABLE": "chunks",
    # Retrieval mode
    "HYBRID_RETRIEVAL": False,
        
        # Cache settings
        "CACHE_TTL_SECONDS": 300,

        # UI persistence (if False, do not write data/ui_state.json)
        "UI_PERSIST_STATE": True,

        # Enforce remote corpus only (no local fallback). If True and CORPUS_URI is empty,
        # code that requires corpus should raise instead of silently proceeding.
        "STRICT_REMOTE_CORPUS": False,
    }
    
    @classmethod
    def get(cls, key: str, default: Optional[Any] = None) -> Any:
        """
        Get configuration value with type conversion.
        
        Args:
            key: Configuration key
            default: Optional default value
        
        Returns:
            Configuration value with appropriate type
        """
        # Use provided default or class default
        default_value = default if default is not None else cls.DEFAULTS.get(key)
        
        # Get value from environment
        value = os.getenv(f"BIOMIND_{key}", os.getenv(key, default_value))
        
        # Type conversion based on default type
        if isinstance(default_value, bool):
            return str(value).lower() == "true" if isinstance(value, str) else bool(value)
        elif isinstance(default_value, int):
            return int(value)
        elif isinstance(default_value, float):
            return float(value)
        
        return value
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all configuration values."""
        config = {}
        for key in cls.DEFAULTS:
            config[key] = cls.get(key)
        return config

def get_config(key: str, default: Optional[Any] = None) -> Any:
    """
    Get configuration value. Main entry point for config access.
    
    Args:
        key: Configuration key
        default: Optional default value
    
    Returns:
        Configuration value with appropriate type
    """
    try:
        return Config.get(key, default)
    except Exception as e:
        logger.error(f"Error getting config {key}: {e}")
        return default
