import logging
import requests
from google import genai
from utils.config_utils import get_config

def query_drugbank_api(drug_name):
    """
    Query DrugBank API for detailed drug information including targets and mechanisms.
    """
    logging.info(f"Querying DrugBank API for {drug_name}")
    # Placeholder for DrugBank API integration
    # In production, this would use actual DrugBank API calls
    drugbank_info = {
        "targets": ["Target Protein A", "Target Protein B"],
        "mechanism": "Inhibits enzyme activity",
        "pharmacokinetics": "Oral bioavailability: 80%",
        "interactions": ["Drug X", "Drug Y"]
    }
    return drugbank_info

def analyze_drug_targets_with_gemini(drug_info, drugbank_data):
    """
    Use Gemini (Flash-Lite) for advanced drug-target reasoning and mechanism analysis.
    Updated to use the new google.genai Client API.
    """
    logging.info("Analyzing drug targets with Gemini Pro")

    client = genai.Client(
        vertexai=True,
        project=get_config('PROJECT_ID'),
        location="us-central1"
    )
    
    name = drug_info.get("name", "")
    indication = drug_info.get("indication", "")
    
    prompt = f"""
    Perform comprehensive drug-target analysis:
    
    Drug: {name}
    Indication: {indication}
    DrugBank Data: {drugbank_data}
    
    Provide detailed analysis of:
    1. Drug-target interactions and mechanisms
    2. Pharmacological pathways affected
    3. Potential side effects and contraindications
    4. Drug-drug interaction risks
    5. Therapeutic efficacy predictions
    6. Novel target opportunities
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[prompt]
        )
        return response.candidates[0].content.parts[0].text
    except Exception as e:
        logging.error(f"Gemini Pro drug analysis failed: {e}")
        return f"Drug {name} analysis failed"

def analyze_drugs(drugs):
    """
    Enhanced drug analysis using DrugBank API and Gemini Pro for drug-target reasoning.
    Each drug is a dict with 'name' and 'indication'.
    """
    logging.info("Analyzing drug data with DrugBank API and Gemini Pro")
    insights = []
    
    for drug in drugs:
        name = drug.get("name", "")
        indication = drug.get("indication", "")
        
        if not (name or indication):
            insights.append("No drug data available")
            continue
        
        # Query DrugBank API for additional information
        drugbank_data = query_drugbank_api(name)
        
        # Use Gemini Pro for advanced reasoning
        analysis = analyze_drug_targets_with_gemini(drug, drugbank_data)
        
        # Combine basic info with AI analysis
        basic_info = f"Drug: {name}, Indication: {indication}"
        combined_analysis = f"{basic_info}\n\nDrugBank + Gemini Analysis:\n{analysis}"
        insights.append(combined_analysis)
    
    return insights
