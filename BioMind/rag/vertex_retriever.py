"""
Enhanced retriever component for BioMind RAG pipeline using Google Vertex AI Matching Engine.
"""

from typing import List, Dict, Optional
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_vertexai import VertexAIEmbeddings
from utils.config_utils import get_config
from google.cloud import aiplatform
import datetime
import structlog
from typing import Optional, Dict

logger = structlog.get_logger()

class VertexAIRetriever:
    def __init__(self, project_id: str, location: str = "us-central1"):
        """
        Initialize the retriever with Google Cloud project settings.
        
        Args:
            project_id: Google Cloud project ID
            location: Google Cloud region (default: us-central1)
        """
        self.project_id = project_id
        self.location = location
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=location)
        
        # Initialize text splitter for document chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", "!", "?", ";"]
        )
        
        # Initialize Vertex AI embeddings (model from config)
        embedding_model = get_config("EMBEDDING_MODEL", "text-embedding-005")
        self.embeddings = VertexAIEmbeddings(
            model_name=embedding_model,
            project=project_id,
            location=location,
        )
        
        # Will hold the index and index endpoint
        self.index = None
        self.index_endpoint = None

    async def create_index(self, name: str, dimensions: int = 768):
        """
        Create a new Vertex AI vector search index.
        
        Args:
            name: Name for the index
            dimensions: Dimension of the embeddings (default: 768 for text-embedding-gecko)
        """
        # Configure index metadata
        metadata = {
            "dimensions": dimensions,
            "approximate_neighbors_count": 50,
            "description": "BioMind vector search index"
        }
        
        # Use Vertex AI index service
        index_endpoint = aiplatform.IndexEndpoint.create(
            display_name=f"{name}-endpoint",
            location=self.location,
            metadata=metadata
        )
        self.index_endpoint = index_endpoint
        
        # Create ANN index
        self.index = self.index_endpoint.create_index(
            content_dimension=dimensions,
            display_name=name,
            metadata=metadata
        )
        
        logger.info("Created Vertex AI vector search index and endpoint", 
                   index_id=self.index.name)
        return self.index

    def process_documents(self, documents: List[Document]) -> List[Document]:
        """Process and chunk documents."""
        chunks = []
        for doc in documents:
            # Add source tracking
            if not hasattr(doc.metadata, 'source_id'):
                doc.metadata['source_id'] = f"doc_{hash(doc.page_content)}"
            
            # Split into chunks
            doc_chunks = self.text_splitter.split_text(doc.page_content)
            
            # Create Document objects for chunks with metadata
            for i, chunk in enumerate(doc_chunks):
                chunk_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        'chunk_id': i,
                        'total_chunks': len(doc_chunks)
                    }
                )
                chunks.append(chunk_doc)
        
        return chunks

    async def index_documents(self, documents: List[Document]):
        """
        Index documents in Vertex AI vector search.
        """
        # Process documents into chunks
        chunks = self.process_documents(documents)
        
        # Generate embeddings
        embeddings = await self.embeddings.aembed_documents(
            [chunk.page_content for chunk in chunks]
        )
        
        # Prepare index data points
        datapoints = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            datapoint = {
                "datapoint_id": f"chunk_{i}",
                "feature_vector": embedding,
                "metadata": {
                    "content": chunk.page_content,
                    **chunk.metadata
                }
            }
            datapoints.append(datapoint)
        
        # Index datapoints in batches
        batch_size = 100
        for i in range(0, len(datapoints), batch_size):
            batch = datapoints[i:i + batch_size]
            # Update the index with batch
            self.index_endpoint.update_index(
                index=self.index.name,
                datapoints=batch
            )
        
        logger.info("Indexed documents", count=len(chunks))

    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        max_age_days: Optional[int] = None
    ) -> List[Document]:
        """
        Perform similarity search using Vertex AI vector search.
        
        Args:
            query: Query text
            k: Number of results to return
            max_age_days: Optional filter for document age
        """
        # Generate query embedding
        query_embedding = await self.embeddings.aembed_query(query)
        
        # Prepare query parameters
        query_params = {
            "deployed_index_id": self.index.name,
            "queries": [{"values": query_embedding}],
            "num_neighbors": k
        }
        
        # Add date filter if specified
        if max_age_days:
            current_date = datetime.datetime.now()
            cutoff_date = current_date - datetime.timedelta(days=max_age_days)
            query_params["filter"] = {
                "date": {
                    "gte": cutoff_date.isoformat()
                }
            }
        
        # Perform nearest neighbor search
        response = self.index_endpoint.match(
            **query_params
        )
        
        # Convert results back to Documents
        results = []
        if response and response.matches:
            matches = response.matches[0]  # First query's results
            for match in matches:
                metadata = match.metadata
                doc = Document(
                    page_content=metadata.pop('content', ''),
                    metadata={
                        **metadata,
                        'score': match.distance
                    }
                )
                results.append(doc)
        
        return results

    def filter_by_date(self, documents: List[Document], max_age_days: int) -> List[Document]:
        """Filter documents by date if date information is available."""
        current_date = datetime.datetime.now()
        filtered_docs = []
        
        for doc in documents:
            doc_date = doc.metadata.get('date')
            if doc_date:
                try:
                    date_diff = (current_date - doc_date).days
                    if date_diff <= max_age_days:
                        filtered_docs.append(doc)
                except:
                    filtered_docs.append(doc)
            else:
                filtered_docs.append(doc)
                
        return filtered_docs