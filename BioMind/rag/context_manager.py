"""
Context Manager component for BioMind RAG pipeline.
Handles context window management, relevance scoring, and passage selection.
"""

from typing import List, Dict, Optional, Tuple
from langchain.schema import Document
from langchain_google_vertexai import VertexAIEmbeddings
import numpy as np
from dataclasses import dataclass
import structlog
from datetime import datetime

logger = structlog.get_logger()

@dataclass
class ScoredPassage:
    """Represents a passage with its relevance scores."""
    content: str
    metadata: Dict
    semantic_score: float
    recency_score: float = 0.0
    quality_score: float = 0.0
    final_score: float = 0.0

class ContextManager:
    def __init__(
        self,
        max_context_length: int = 4000,
        semantic_weight: float = 0.6,
        recency_weight: float = 0.2,
        quality_weight: float = 0.2,
        project_id: str = None,
        location: str = "us-central1"
    ):
        """
        Initialize the context manager.
        
        Args:
            max_context_length: Maximum number of tokens in the context window
            semantic_weight: Weight for semantic similarity in scoring
            recency_weight: Weight for document recency in scoring
            quality_weight: Weight for source quality in scoring
            project_id: Google Cloud project ID
            location: Google Cloud region
        """
        self.max_context_length = max_context_length
        self.semantic_weight = semantic_weight
        self.recency_weight = recency_weight
        self.quality_weight = quality_weight
        
        # Initialize embeddings for re-ranking
        if project_id:
            self.embeddings = VertexAIEmbeddings(
                model_name="text-embedding-005",
                project=project_id,
                location=location
            )

    def calculate_recency_score(self, doc_date: Optional[datetime]) -> float:
        """Calculate recency score based on document date."""
        if not doc_date:
            return 0.5  # Default score for documents without dates
            
        days_old = (datetime.now() - doc_date).days
        if days_old < 0:
            return 0.5  # Future dates get default score
            
        # Exponential decay based on age
        decay_rate = 0.1
        return np.exp(-decay_rate * days_old)

    def calculate_quality_score(self, metadata: Dict) -> float:
        """Calculate quality score based on source metadata."""
        score = 0.5  # Default score
        
        # Priority boost for live-fetched biomedical sources
        try:
            src = (metadata.get('source') or '').lower()
            priority = (metadata.get('priority') or '').lower()
            if priority == 'live' or src in {'pubmed_articles', 'uniprot_records'}:
                score += 0.3
        except Exception:
            pass

        # Source type scoring
        source_type = metadata.get('source_type', '').lower()
        if source_type == 'peer_reviewed':
            score += 0.3
        elif source_type == 'clinical_trial':
            score += 0.25
        elif source_type == 'meta_analysis':
            score += 0.2
            
        # Citation impact
        citation_count = metadata.get('citation_count', 0)
        if citation_count > 0:
            # Log-scale citation score
            citation_score = np.log1p(citation_count) / 10  # Normalize to [0, 1]
            score += min(0.2, citation_score)
            
        # Journal impact factor
        impact_factor = metadata.get('impact_factor', 0)
        if impact_factor > 0:
            impact_score = min(0.1, impact_factor / 50)  # Cap at IF=50
            score += impact_score
            
        return min(1.0, score)

    async def score_passages(
        self,
        query: str,
        passages: List[Document]
    ) -> List[ScoredPassage]:
        """Score passages based on multiple criteria."""
        # Get query embedding for semantic similarity
        query_embedding = await self.embeddings.aembed_query(query)
        passage_embeddings = await self.embeddings.aembed_documents(
            [p.page_content for p in passages]
        )
        
        scored_passages = []
        for passage, embedding in zip(passages, passage_embeddings):
            # Calculate semantic similarity
            semantic_score = np.dot(query_embedding, embedding)
            
            # Calculate recency score
            doc_date = passage.metadata.get('date')
            if isinstance(doc_date, str):
                try:
                    doc_date = datetime.fromisoformat(doc_date)
                except ValueError:
                    doc_date = None
            recency_score = self.calculate_recency_score(doc_date)
            
            # Calculate quality score
            quality_score = self.calculate_quality_score(passage.metadata)
            
            # Calculate final score
            final_score = (
                self.semantic_weight * semantic_score +
                self.recency_weight * recency_score +
                self.quality_weight * quality_score
            )
            
            scored_passage = ScoredPassage(
                content=passage.page_content,
                metadata=passage.metadata,
                semantic_score=semantic_score,
                recency_score=recency_score,
                quality_score=quality_score,
                final_score=final_score
            )
            scored_passages.append(scored_passage)
            
        # Sort by final score
        scored_passages.sort(key=lambda x: x.final_score, reverse=True)
        return scored_passages

    def select_passages(
        self,
        scored_passages: List[ScoredPassage],
        min_score_threshold: float = 0.5
    ) -> Tuple[List[Document], Dict]:
        """
        Select passages for the context window while tracking provenance.
        
        Returns:
            Tuple containing:
            - List of selected Document objects
            - Dictionary containing provenance information
        """
        selected_docs = []
        provenance = {
            'sources': [],
            'selection_criteria': {
                'min_score_threshold': min_score_threshold,
                'max_context_length': self.max_context_length
            }
        }
        
        current_length = 0
        for passage in scored_passages:
            if passage.final_score < min_score_threshold:
                continue
                
            # Rough token count (can be replaced with actual tokenizer)
            passage_length = len(passage.content.split())
            if current_length + passage_length > self.max_context_length:
                break
                
            # Create Document with enhanced metadata
            doc = Document(
                page_content=passage.content,
                metadata={
                    **passage.metadata,
                    'final_score': passage.final_score,
                    'semantic_score': passage.semantic_score,
                    'recency_score': passage.recency_score,
                    'quality_score': passage.quality_score
                }
            )
            selected_docs.append(doc)
            
            # Track provenance
            source_info = {
                'source_id': passage.metadata.get('source_id', 'unknown'),
                'chunk_id': passage.metadata.get('chunk_id', 'unknown'),
                'score': passage.final_score,
                'metadata': {k: v for k, v in passage.metadata.items() 
                           if k not in ['source_id', 'chunk_id']}
            }
            # Bubble up a top-level url field for convenience if present in metadata
            url = passage.metadata.get('url')
            if url:
                source_info['url'] = url
            provenance['sources'].append(source_info)
            
            current_length += passage_length
            
        provenance['total_tokens'] = current_length
        provenance['selected_passages'] = len(selected_docs)
        
        logger.info(
            "Selected passages for context",
            selected_count=len(selected_docs),
            total_tokens=current_length
        )
        
        return selected_docs, provenance