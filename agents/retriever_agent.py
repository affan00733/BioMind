import logging
from google.cloud import bigquery
from google.cloud import aiplatform
from google import genai
from utils.config_utils import get_config
from utils.cache_utils import api_cache
import connectors.pubmed.connector as pubmed_connector
import connectors.uniprot.connector as uniprot_connector
import connectors.drugbank.connector as drugbank_connector
import connectors.google_health_blog.connector as google_health_connector

def embed_text(text):
    """Generate embedding for text using Vertex AI Gemini embeddings."""
    from google import genai
    from utils.config_utils import get_config
    import logging

    try:
        # ✅ Create Vertex AI client using new SDK
        client = genai.Client(
            vertexai=True,
            project=get_config("PROJECT_ID"),
            location="us-central1"
        )

        # ✅ Correct embedding model and parameter name (confirmed)
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=[text]
        )

        embedding = response.embeddings[0].values
        return embedding

    except Exception as e:
        logging.error(f"Embedding generation failed: {e}")
        return None



def create_vertex_matching_engine_index():
    """
    Create or get Vertex AI Matching Engine index for vector search.
    This is a placeholder for the actual Matching Engine setup.
    """
    logging.info("Setting up Vertex AI Matching Engine index")
    
    # Initialize Vertex AI
    aiplatform.init(
        project=get_config('PROJECT_ID'),
        location="us-central1"
    )
    
    # In production, this would create/configure the actual Matching Engine index
    # For now, we'll use BigQuery with vector similarity search as a fallback
    logging.info("Using BigQuery vector similarity search as Matching Engine fallback")
    return True

def search_with_matching_engine(query, query_embedding, top_k=20):
    """
    Search using Vertex AI Matching Engine for vector retrieval.
    Falls back to BigQuery vector search if Matching Engine is not available.
    """
    logging.info("Searching with Vertex AI Matching Engine")
    
    try:
        # Placeholder for actual Matching Engine search
        # In production, this would use the Matching Engine API
        logging.info("Matching Engine search would be implemented here")
        
        # For now, fall back to BigQuery vector search
        return search_with_bigquery_vectors(query, query_embedding, top_k)
        
    except Exception as e:
        logging.error(f"Matching Engine search failed: {e}")
        return search_with_bigquery_vectors(query, query_embedding, top_k)

def search_with_bigquery_vectors(query, query_embedding, top_k=20):
    """
    Enhanced BigQuery vector search with improved similarity scoring.
    """
    logging.info("Performing enhanced BigQuery vector search")
    
    bq_client = bigquery.Client(project=get_config('PROJECT_ID'))
    dataset = get_config('BIGQUERY_DATASET')
    
    # Define search tables with their relevance weights
    search_config = {
        "pubmed_articles": {"weight": 1.0, "fields": ["title", "abstract"]},
        "uniprot_records": {"weight": 0.8, "fields": ["protein_name", "description"]},
        "drugbank_entries": {"weight": 0.9, "fields": ["name", "description"]}
    }
    
    candidates = []
    
    for table_name, config in search_config.items():
        table_ref = f"{get_config('PROJECT_ID')}.{dataset}.{table_name}"
        
        if query_embedding:
            try:
                # Enhanced vector similarity search with field weighting
                query_str = f"""
                SELECT 
                    *,
                    embedding <=> ARRAY{query_embedding} AS similarity_score,
                    ({config['weight']} * (1 - (embedding <=> ARRAY{query_embedding}))) AS weighted_score
                FROM `{table_ref}`
                WHERE embedding IS NOT NULL
                ORDER BY weighted_score DESC
                LIMIT {top_k}
                """
                
                results = bq_client.query(query_str).result()
                for row in results:
                    # Add source information
                    row_dict = dict(row)
                    row_dict['source'] = table_name
                    row_dict['search_score'] = row_dict['weighted_score']
                    candidates.append(row_dict)
                    
            except Exception as e:
                logging.warning(f"Vector search failed for {table_name}: {e}")
                # Fallback to keyword search
                try:
                    # Build WHERE clause separately to avoid f-string backslash issue
                    where_conditions = ' OR '.join([f"{field} LIKE '%{query}%'" for field in config['fields']])
                    keyword_query = (
                        f"SELECT *, 0.5 AS search_score, '{table_name}' AS source "
                        f"FROM `{table_ref}` "
                        f"WHERE {where_conditions} "
                        f"LIMIT {top_k}"
                    )
                    keyword_results = bq_client.query(keyword_query).result()
                    
                    for row in keyword_results:
                        candidates.append(dict(row))
                        
                except Exception as e2:
                    logging.error(f"Keyword search also failed for {table_name}: {e2}")
    
    # Sort by search score and return top results
    candidates.sort(key=lambda x: x.get('search_score', 0), reverse=True)
    return candidates[:top_k]

def fetch_data_realtime(query, max_results_per_source=5):
    """
    Fetch data from all sources in real-time based on the query with caching.
    Returns combined results from PubMed, UniProt, and DrugBank.
    """
    logging.info(f"Fetching real-time data for query: {query}")
    
    # Log which connectors are enabled
    import connectors.pubmed.config as pubmed_config
    import connectors.uniprot.config as uniprot_config
    import connectors.drugbank.config as drugbank_config
    import connectors.google_health_blog.config as google_health_config
    
    enabled_connectors = []
    if pubmed_config.ENABLE_PUBMED:
        enabled_connectors.append("PubMed")
    if uniprot_config.ENABLE_UNIPROT:
        enabled_connectors.append("UniProt")
    if drugbank_config.ENABLE_DRUGBANK:
        enabled_connectors.append("DrugBank")
    if google_health_config.ENABLE_GOOGLE_HEALTH_BLOG:
        enabled_connectors.append("Google Health Blog")
    
    logging.info(f"Enabled connectors: {', '.join(enabled_connectors) if enabled_connectors else 'None'}")
    
    all_candidates = []
    
    # Fetch from PubMed with caching
    try:
        # Check cache first
        cached_pubmed = api_cache.get(query, "pubmed")
        if cached_pubmed:
            pubmed_data = cached_pubmed
            logging.info(f"Using cached PubMed data: {len(pubmed_data)} articles")
        else:
            pubmed_data = pubmed_connector.fetch_pubmed_data_realtime(query, max_results_per_source)
            api_cache.set(query, "pubmed", pubmed_data)
            logging.info(f"Fetched and cached {len(pubmed_data)} PubMed articles")
        
        all_candidates.extend(pubmed_data)
    except Exception as e:
        logging.error(f"PubMed real-time fetch failed: {e}")
    
    # Fetch from UniProt with caching
    try:
        cached_uniprot = api_cache.get(query, "uniprot")
        if cached_uniprot:
            uniprot_data = cached_uniprot
            logging.info(f"Using cached UniProt data: {len(uniprot_data)} proteins")
        else:
            uniprot_data = uniprot_connector.fetch_uniprot_data_realtime(query, max_results_per_source)
            api_cache.set(query, "uniprot", uniprot_data)
            logging.info(f"Fetched and cached {len(uniprot_data)} UniProt proteins")
        
        all_candidates.extend(uniprot_data)
    except Exception as e:
        logging.error(f"UniProt real-time fetch failed: {e}")
    
    # Fetch from DrugBank with caching
    try:
        cached_drugbank = api_cache.get(query, "drugbank")
        if cached_drugbank:
            drugbank_data = cached_drugbank
            logging.info(f"Using cached DrugBank data: {len(drugbank_data)} drugs")
        else:
            drugbank_data = drugbank_connector.fetch_drugbank_data_realtime(query, max_results_per_source)
            api_cache.set(query, "drugbank", drugbank_data)
            logging.info(f"Fetched and cached {len(drugbank_data)} DrugBank drugs")
        
        all_candidates.extend(drugbank_data)
    except Exception as e:
        logging.error(f"DrugBank real-time fetch failed: {e}")
    
    # Fetch from Google Health Blog with caching
    try:
        cached_google_health = api_cache.get(query, "google_health_blog")
        if cached_google_health:
            google_health_data = cached_google_health
            logging.info(f"Using cached Google Health Blog data: {len(google_health_data)} posts")
        else:
            google_health_data = google_health_connector.fetch_google_health_blog_data_realtime(query, max_results_per_source)
            api_cache.set(query, "google_health_blog", google_health_data)
            logging.info(f"Fetched and cached {len(google_health_data)} Google Health Blog posts")
        
        all_candidates.extend(google_health_data)
    except Exception as e:
        logging.error(f"Google Health Blog real-time fetch failed: {e}")
    
    logging.info(f"Total real-time data fetched: {len(all_candidates)} items")
    return all_candidates

def retrieve_relevant_docs(query, top_k=20):
    """
    Real-time document retrieval that fetches fresh data from APIs.
    Falls back to BigQuery if real-time fetching fails.
    """
    logging.info(f"Retrieving relevant documents for query: {query}")
    
    # Try real-time fetching first
    try:
        realtime_candidates = fetch_data_realtime(query, max_results_per_source=7)
        
        if realtime_candidates:
            logging.info(f"Successfully fetched {len(realtime_candidates)} documents in real-time")
            
            # Log search results summary
            sources = {}
            for candidate in realtime_candidates:
                source = candidate.get('source', 'unknown')
                sources[source] = sources.get(source, 0) + 1
            
            logging.info(f"Real-time search results by source: {sources}")
            return realtime_candidates[:top_k]
        else:
            logging.warning("Real-time fetching returned no results, falling back to BigQuery")
    except Exception as e:
        logging.error(f"Real-time fetching failed: {e}, falling back to BigQuery")
    
    # Fallback to BigQuery vector search
    logging.info("Falling back to BigQuery vector search")
    create_vertex_matching_engine_index()
    
    query_embedding = embed_text(query)
    if not query_embedding:
        logging.error("Failed to generate query embedding")
        return []
    
    candidates = search_with_matching_engine(query, query_embedding, top_k)
    logging.info(f"Retrieved {len(candidates)} documents from BigQuery fallback")
    
    return candidates
