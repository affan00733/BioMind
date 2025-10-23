"""
Main RAG pipeline that orchestrates the retrieval, context management, and response generation.
"""

from typing import Dict, Optional
import structlog
from .vertex_retriever import VertexAIRetriever
from .context_manager import ContextManager
from .response_generator import ResponseGenerator

logger = structlog.get_logger()

class RAGPipeline:
    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        max_context_length: int = 4000,
        min_score_threshold: float = 0.5,
        temperature: float = 0.3
    ):
        """
        Initialize the RAG pipeline.
        
        Args:
            project_id: Google Cloud project ID
            location: Google Cloud region
            max_context_length: Maximum context window size
            min_score_threshold: Minimum score for passage selection
            temperature: Temperature for response generation
        """
        self.retriever = VertexAIRetriever(
            project_id=project_id,
            location=location
        )
        
        self.context_manager = ContextManager(
            max_context_length=max_context_length,
            project_id=project_id,
            location=location
        )
        
        self.generator = ResponseGenerator(
            project_id=project_id,
            location=location,
            temperature=temperature
        )
        
        self.min_score_threshold = min_score_threshold

    async def process_query(
        self,
        query: str,
        max_age_days: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> Dict:
        """
        Process a query through the RAG pipeline.
        
        Args:
            query: User's question
            max_age_days: Optional filter for document age
            response_format: Optional structure for the response
        """
        try:
            # 1. Retrieve relevant documents
            logger.info("Retrieving documents", query=query)
            documents = await self.retriever.similarity_search(
                query,
                k=10,
                max_age_days=max_age_days
            )
            
            # 2. Score and select passages
            logger.info("Scoring passages")
            scored_passages = await self.context_manager.score_passages(query, documents)
            
            # 3. Select passages for context window
            selected_docs, provenance = self.context_manager.select_passages(
                scored_passages,
                min_score_threshold=self.min_score_threshold
            )
            
            # 4. Generate response
            logger.info("Generating response")
            response = await self.generator.generate_response(
                query,
                selected_docs,
                provenance,
                response_format
            )
            
            # 5. Validate response
            validation = self.generator.validate_response(response)
            
            # 6. Enhance response with metadata
            enhanced_response = self.generator.enhance_response(response, validation)
            
            logger.info(
                "Query processed successfully",
                query=query,
                documents_retrieved=len(documents),
                passages_selected=len(selected_docs)
            )
            
            return enhanced_response
            
        except Exception as e:
            logger.error(
                "Error processing query",
                error=str(e),
                query=query
            )
            raise

    async def initialize(self, name: str = "biomind-index"):
        """Initialize the pipeline components."""
        # Create Matching Engine index
        await self.retriever.create_index(name)
        logger.info("Pipeline initialized")