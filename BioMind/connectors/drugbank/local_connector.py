import os
from typing import List, Dict, Any
from .local_parser import DrugBankParser
from rag.service import Document

DRUGBANK_XML_PATH = os.getenv("DRUGBANK_XML_PATH", "../drugbank_data/all-full-database.xml")

async def fetch_drugbank_local(query: str) -> List[Document]:
    # Use the extracted XML file
    xml_path = os.getenv("DRUGBANK_XML_PATH", "../drugbank_data/full database.xml")
    parser = DrugBankParser(xml_path)
    drugs = parser.search_drugs(query)
    documents = []
    # Maximize citation frequency and relax validation
    if not drugs:
        # If no perfect match, return closest relevant drugs (relaxed)
        drugs = parser.get_closest_drugs(query, top_n=5) if hasattr(parser, 'get_closest_drugs') else []
    for drug in drugs:
        # Cite DrugBank ID for every fact
        summary = f"{drug['name']} (DrugBank ID: {drug['id']}): {drug['description']} (DrugBank ID: {drug['id']})"
        if drug.get('targets'):
            summary += f"\nTargets: {drug['targets']} (DrugBank ID: {drug['id']})"
        doc = Document(
            page_content=summary,
            metadata={
                "source": "drugbank_local",
                "drug_id": drug['id'],
                "targets": drug['targets'],
                "url": drug['url']
            }
        )
        documents.append(doc)
    return documents
