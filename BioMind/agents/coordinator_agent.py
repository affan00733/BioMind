import logging
import asyncio
from agents.retriever_agent import RetrieverAgent
from agents.literature_agent import summarize_papers
from agents.protein_agent import parse_proteins
from agents.drug_agent import analyze_drugs
from agents.hypothesis_synthesizer import synthesize_hypothesis
from confidence_evaluator import evaluate_confidence

class CoordinatorAgent:
    """
    Coordinator to run the entire pipeline of agents.
    """
    def __init__(self):
        logging.info("Coordinator initialized")
        self.retriever = RetrieverAgent()

    async def run_pipeline(self, question: str):
        logging.info(f"Running pipeline for question: {question}")
        # Retrieve relevant documents from data sources
        docs = await self.retriever.retrieve_relevant_docs(question)
        logging.info(f"Retrieved {len(docs)} documents from data sources")

        # If we have no evidence at all, return a helpful prompt instead of a speculative hypothesis
        if not docs:
            guidance = (
                "No evidence was retrieved from the enabled sources for this question. "
                "Try refining your query with more specific biomedical keywords (e.g., a condition, biomarker, or pathway), "
                "or type 'help' to see example queries."
            )
            return guidance, 0.0

        # Separate documents by type (PubMed articles, UniProt entries, DrugBank entries, Google Health Blog posts)
        lit_papers = [d for d in docs if d.get('source') == 'pubmed' and d.get('content')]
        uniprot_entries = [d for d in docs if d.get('source') == 'uniprot' and d.get('content')]
        drug_entries = [d for d in docs if d.get('source') == 'drugbank' and d.get('content')]
        # Fix: retriever uses source "google_health" (not "google_health_blog")
        google_health_posts = [d for d in docs if d.get('source') == 'google_health' and d.get('content')]

        # Summarize literature
        lit_summaries = []
        if lit_papers:
            # Pass structured fields expected by summarize_papers (title, abstract)
            papers = []
            for d in lit_papers:
                meta = d.get("metadata", {}) or {}
                title = meta.get("title", "")
                abstract = meta.get("abstract", "")
                # Fallback: try to parse from concatenated content if metadata missing
                if (not title or not abstract) and isinstance(d.get("content"), str):
                    content = d["content"]
                    try:
                        # Very simple extraction from the templated content
                        import re
                        t_match = re.search(r"^Title:\s*(.*)$", content, re.MULTILINE)
                        a_match = re.search(r"^Abstract:\s*(.*)$", content, re.MULTILINE)
                        if t_match and not title:
                            title = t_match.group(1).strip()
                        if a_match and not abstract:
                            abstract = a_match.group(1).strip()
                    except Exception:
                        pass
                # Only add if we have at least some text
                if title or abstract:
                    papers.append({"title": title, "abstract": abstract})
            if papers:
                lit_summaries = summarize_papers(papers)

        # Parse proteins
        prot_info = []
        if uniprot_entries:
            # Provide fields expected by parse_proteins (protein_name, genes, sequence)
            proteins = []
            for d in uniprot_entries:
                meta = d.get("metadata", {}) or {}
                proteins.append({
                    "protein_name": meta.get("protein_name", ""),
                    "genes": meta.get("genes", meta.get("gene", "")),
                    "sequence": meta.get("sequence", ""),
                })
            prot_info = parse_proteins(proteins)

        # Analyze drugs
        drug_info = []
        if drug_entries:
            # Provide fields expected by analyze_drugs (name, indication)
            drugs = []
            for d in drug_entries:
                meta = d.get("metadata", {}) or {}
                drugs.append({
                    "name": meta.get("name", ""),
                    "indication": meta.get("indication", meta.get("description", "")),
                })
            drug_info = analyze_drugs(drugs)

        # Process Google Health Blog posts (add to literature analysis)
        if google_health_posts:
            # Map fields to match summarize_papers signature
            google_papers = []
            for d in google_health_posts:
                meta = d.get("metadata", {}) or {}
                title = meta.get("title", "")
                # Use 'summary' as a proxy for abstract
                abstract = meta.get("summary", meta.get("description", ""))
                if title or abstract:
                    google_papers.append({"title": title, "abstract": abstract})
            if google_papers:
                google_health_summaries = summarize_papers(google_papers)
                lit_summaries.extend(google_health_summaries)

        # Placeholder for image info (not implemented in pipeline)
        image_info = {}

        # Synthesize hypothesis
        hypothesis = synthesize_hypothesis(question, lit_summaries, prot_info, drug_info, image_info)
        # Evaluate confidence
        evidence_texts = lit_summaries + prot_info + drug_info
        conf = evaluate_confidence(hypothesis, evidence_texts)
        # Backwards compatibility: accept either numeric percentage or structured dict
        if isinstance(conf, dict) and 'confidence_percentage' in conf:
            confidence = conf['confidence_percentage']
        elif isinstance(conf, (int, float)):
            confidence = float(conf)
        else:
            confidence = 0.0
        return hypothesis, confidence
