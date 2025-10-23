"""
Response Generator component for BioMind RAG pipeline.
Handles prompt construction, response generation, and source attribution.
"""

from typing import List, Dict, Optional, Union
from langchain.schema import Document
from langchain_google_vertexai import ChatVertexAI
import json
import structlog
from datetime import datetime
import re
from confidence_evaluator import evaluate_confidence

logger = structlog.get_logger()

class ResponseGenerator:
    def __init__(
    self,
    project_id: str,
    location: str = "us-central1",
    model_name: str = "gemini-2.5-flash-lite",
    temperature: float = 0.3,
    max_output_tokens: int = 4096,
    ):
        """
        Initialize the response generator.
        
        Args:
            project_id: Google Cloud project ID
            location: Google Cloud region
            model_name: Vertex AI model name
            temperature: Temperature for response generation
            max_output_tokens: Maximum tokens in the response
        """
        # Use ChatVertexAI for Gemini chat/text models
        self.model_name = model_name
        self.temperature = temperature
        self.llm = ChatVertexAI(
            model_name=model_name,
            project=project_id,
            location=location,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )

    def construct_prompt(
        self,
        query: str,
        context_docs: List[Document],
        response_format: Optional[Dict] = None
    ) -> str:
        """Construct a grounded, citation-focused prompt for the LLM."""
        # Summarize sources with IDs and URLs to encourage grounded citations
        sources_index_lines: list[str] = ["Sources Index:"]
        for i, doc in enumerate(context_docs, start=1):
            sid = str(doc.metadata.get("source_id", "unknown"))
            url = str(doc.metadata.get("url", ""))
            src = str(doc.metadata.get("source", ""))
            sources_index_lines.append(f"[{i}] id={sid} source={src} url={url}")

        # Base prompt with emphasis on comprehensive citation
        prompt = [
            "You are a biomedical research assistant. Provide detailed, comprehensive answers using EXTENSIVE citations.",
            "CRITICAL CITATION REQUIREMENTS:",
            "- EVERY sentence must include [Source ID: <id>] citations. Never write uncited sentences.",
            "- Use multiple sources per sentence when possible: [Source ID: 123, 456]",
            "- Synthesize information from ALL provided sources, citing each one multiple times.",
            "- Provide detailed explanations with 3-4 paragraphs per section minimum.",
            "- Be scientifically rigorous and comprehensive. Include specific mechanisms, pathways, and evidence.",
            "- Output sections exactly as follows:",
            "  1) Title",
            "  2) Testable hypotheses (exactly 3 bullets) — each with 2-3 sentences and extensive [Source ID] citations",
            "  3) Proposed experiments (exactly 2 bullets) — detailed protocols with specific endpoints and [Source ID] citations",
            "  4) Risks and confounders (detailed bullets with citations)",
            "  5) Limitations (detailed with citations)",
            "",
            f"Query: {query}",
            "",
            "Context (verbatim excerpts with IDs):",
        ]

        # Add context passages with Source IDs to enforce grounding
        for doc in context_docs:
            source_id = doc.metadata.get('source_id', 'unknown')
            prompt.append(f"\n[Source ID: {source_id}]\n{doc.page_content}")

        # Append a compact index of sources to make URLs available for the model
        prompt.append("\n" + "\n".join(sources_index_lines))

        # Optional explicit response schema (still allows free-form text but biases layout)
        if response_format:
            prompt.append("\nPlease adhere to this JSON-like outline when structuring the sections (do not output raw JSON):")
            prompt.append(json.dumps(response_format, indent=2))

        return "\n".join(prompt)

    def format_response(
        self,
        response: str,
        provenance: Dict,
        query: str
    ) -> Dict:
        """Format the response with metadata and provenance information."""
        return {
            "query": query,
            "response": response,
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "temperature": self.temperature,
            },
            "provenance": provenance
        }

    async def generate_response(
        self,
        query: str,
        context_docs: List[Document],
        provenance: Dict,
        response_format: Optional[Dict] = None
    ) -> Dict:
        """
        Generate a response using the provided context.
        
        Args:
            query: User's question
            context_docs: List of relevant documents
            provenance: Provenance information from context selection
            response_format: Optional structure for the response
        """
        try:
            # Construct prompt
            prompt = self.construct_prompt(query, context_docs, response_format)
            
            # Generate response with Gemini chat model (async invoke)
            raw = await self.llm.ainvoke(prompt)

            # LangChain Chat models typically return an AIMessage; extract the text robustly
            generated_text: str
            if hasattr(raw, "content"):
                content = getattr(raw, "content")
                if isinstance(content, str):
                    generated_text = content
                elif isinstance(content, list):
                    # Join any text-bearing parts; tolerate dicts/objects
                    parts: list[str] = []
                    for part in content:
                        if isinstance(part, str):
                            parts.append(part)
                        elif isinstance(part, dict):
                            # common patterns: {"type": "text", "text": "..."}
                            txt = part.get("text") or part.get("content")
                            if isinstance(txt, str):
                                parts.append(txt)
                        elif hasattr(part, "text") and isinstance(getattr(part, "text"), str):
                            parts.append(getattr(part, "text"))
                        else:
                            parts.append(str(part))
                    generated_text = "\n".join(p for p in parts if p)
                else:
                    generated_text = str(content)
            elif hasattr(raw, "text") and isinstance(getattr(raw, "text"), str):
                generated_text = raw.text  # fallback for alternative message shapes
            elif isinstance(raw, str):
                generated_text = raw
            elif isinstance(raw, dict) and "text" in raw and isinstance(raw["text"], str):
                generated_text = raw["text"]
            else:
                # Final fallback to ensure we always return a string
                generated_text = str(raw)
            
            # Format response with metadata and provenance
            formatted_response = self.format_response(
                generated_text,
                provenance,
                query
            )
            
            logger.info(
                "Generated response",
                query=query,
                context_docs=len(context_docs),
                response_length=len(generated_text) if isinstance(generated_text, str) else None,
            )
            
            return formatted_response
            
        except Exception as e:
            logger.error(
                "Error generating response",
                error=str(e),
                query=query
            )
            raise

    def validate_response(self, response: Dict) -> Dict:
        """
        Validate the generated response for quality and source attribution.
        
        Args:
            response: Generated response with metadata
        
        Returns:
            Dictionary with validation results and any warnings
        """
        validation = {
            "passed": True,
            "warnings": [],
            "source_coverage": 0.0
        }
        
        # Check source citations
        cited_sources = set()
        for match in re.finditer(r'\[Source ID: ([^\]]+)\]', response['response']):
            cited_sources.add(match.group(1))
            
        available_sources = {
            source['source_id'] 
            for source in response['provenance']['sources']
        }
        
        # Calculate source coverage
        if available_sources:
            validation['source_coverage'] = len(cited_sources) / len(available_sources)
            
        # Add warnings for uncited sources (even more lenient for DrugBank and short answers)
        uncited = available_sources - cited_sources
        # Only fail if >90% uncited and not DrugBank
        is_drugbank = any('drugbank' in str(s).lower() for s in available_sources)
        uncited_threshold = 0.9 if is_drugbank else 0.7
        if len(uncited) > len(available_sources) * uncited_threshold:
            validation['warnings'].append(
                f"Many sources were not cited: {', '.join(list(uncited)[:5])}{' ...' if len(uncited) > 5 else ''}"
            )
            # Only fail if not DrugBank
            if not is_drugbank:
                validation['passed'] = False
        elif uncited:
            validation['warnings'].append(
                f"Some sources were not cited: {', '.join(list(uncited)[:3])}{' ...' if len(uncited) > 3 else ''}"
            )

        # Check response length (even more lenient)
        if len(response['response'].split()) < 15:
            validation['warnings'].append("Response may be too short")
            # Don't fail validation for short responses
            
        # Check for potential hallucination markers
        hallucination_markers = [
            "I believe",
            "I think",
            "probably",
            "might be",
            "could be"
        ]
        
        for marker in hallucination_markers:
            if marker in response['response'].lower():
                validation['warnings'].append(
                    f"Potential speculation detected: '{marker}'"
                )
                
        return validation

    def enhance_response(
        self,
        response: Dict,
        validation: Dict
    ) -> Dict:
        """
        Enhance the response with additional metadata and improvements.
        
        Args:
            response: Original response
            validation: Validation results
        
        Returns:
            Enhanced response with additional metadata
        """
        enhanced = response.copy()
        
        # Add validation results
        enhanced['validation'] = validation
        
        # Add source summary
        source_summary = []
        for source in response['provenance']['sources']:
            summary = {
                'id': source['source_id'],
                'type': source['metadata'].get('source_type', 'unknown'),
                'date': source['metadata'].get('date', 'unknown'),
                'relevance_score': source['score']
            }
            source_summary.append(summary)
            
        enhanced['source_summary'] = source_summary
        
        # Add confidence metrics
        # Compute enhanced confidence using the evidence texts we used as context
        evidence_texts = [s.get('text') or '' for s in response.get('provenance', {}).get('sources', [])]
        try:
            conf = evaluate_confidence(response.get('response', ''), evidence_texts)
        except Exception:
            conf = None

        # Keep backward-compatible summary fields
        enhanced['confidence_metrics'] = {
            'source_coverage': validation['source_coverage'],
            'average_source_score': sum(s['score'] for s in response['provenance']['sources']) / len(response['provenance']['sources']) if response['provenance']['sources'] else 0,
            'validation_passed': validation['passed'],
            # New structured confidence breakdown (if available)
            'detailed': conf,
        }
        
        return enhanced