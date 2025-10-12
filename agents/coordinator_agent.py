import logging
from agents.retriever_agent import retrieve_relevant_docs
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

    def run_pipeline(self, question: str):
        logging.info(f"Running pipeline for question: {question}")
        # Retrieve relevant documents from BigQuery
        docs = retrieve_relevant_docs(question)
        logging.info(f"Retrieved {len(docs)} documents from data sources")

        # Separate documents by type (PubMed articles, UniProt entries, DrugBank entries, Google Health Blog posts)
        lit_papers = [d for d in docs if d.get('source') == 'pubmed_articles' and d.get('abstract')]
        uniprot_entries = [d for d in docs if d.get('source') == 'uniprot_records' and d.get('protein_name')]
        drug_entries = [d for d in docs if d.get('source') == 'drugbank_entries' and d.get('name')]
        google_health_posts = [d for d in docs if d.get('source') == 'google_health_blog' and d.get('content')]

        # Summarize literature
        lit_summaries = []
        if lit_papers:
            papers = [{"title": d.get("title", ""), "abstract": d.get("abstract", "")} for d in lit_papers]
            lit_summaries = summarize_papers(papers)

        # Parse proteins
        prot_info = []
        if uniprot_entries:
            proteins = [{"protein_name": d.get("protein_name", ""), "genes": d.get("genes", ""), "sequence": d.get("sequence", "")} for d in uniprot_entries]
            prot_info = parse_proteins(proteins)

        # Analyze drugs
        drug_info = []
        if drug_entries:
            drugs = [{"name": d.get("name", ""), "indication": d.get("indication", "")} for d in drug_entries]
            drug_info = analyze_drugs(drugs)

        # Process Google Health Blog posts (add to literature analysis)
        if google_health_posts:
            google_health_papers = [{"title": d.get("title", ""), "abstract": d.get("content", "")} for d in google_health_posts]
            google_health_summaries = summarize_papers(google_health_papers)
            lit_summaries.extend(google_health_summaries)

        # Placeholder for image info (not implemented in pipeline)
        image_info = ""

        # Synthesize hypothesis
        hypothesis = synthesize_hypothesis(question, lit_summaries, prot_info, drug_info, image_info)
        # Evaluate confidence
        evidence_texts = lit_summaries + prot_info + drug_info
        confidence = evaluate_confidence(hypothesis, evidence_texts)
        return hypothesis, confidence
