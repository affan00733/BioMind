import logging
import requests
from google import genai
from utils.config_utils import get_config

def get_esm2_embedding(sequence):
    """
    Generate ESM2 embedding for protein sequence using ESM API or local model.
    For now, we'll use a placeholder that could be replaced with actual ESM2 API calls.
    """
    logging.info(f"Generating ESM2 embedding for sequence of length {len(sequence)}")
    # Placeholder for ESM2 embedding - in production, this would call ESM2 API
    # or use a local ESM2 model to generate protein embeddings
    return [0.1] * 1280  # ESM2 typically produces 1280-dimensional embeddings

def analyze_protein_with_medgemma(protein_info):
    """
    Use MedGemma Bio (via Gemini) to analyze protein information and predict functions.
    Updated to use the new google.genai Client API instead of deprecated configure().
    """
    logging.info("Analyzing protein with MedGemma Bio")

    # ✅ Initialize GenAI client with Vertex AI routing (new SDK)
    client = genai.Client(
        vertexai=True,
        project=get_config('PROJECT_ID'),
        location="us-central1"
    )
    
    name = protein_info.get("protein_name", "")
    genes = protein_info.get("genes", "")
    sequence = protein_info.get("sequence", "")
    
    prompt = f"""
    Analyze this protein for biomedical insights:
    Protein Name: {name}
    Genes: {genes}
    Sequence Length: {len(sequence)}
    Sequence (first 100 chars): {sequence[:100]}...
    
    Provide:
    1. Predicted function based on sequence analysis
    2. Potential disease associations
    3. Drug target potential
    4. Key functional domains
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[prompt]
        )
        # Prefer the same extraction style used elsewhere in the repo
        return response.candidates[0].content.parts[0].text
    except Exception as e:
        logging.error(f"MedGemma Bio analysis failed: {e}")
        return f"Protein {name} analysis failed"

def parse_proteins(proteins):
    """
    Enhanced protein analysis using ESM2 embeddings and MedGemma Bio.
    Each protein is a dict with 'protein_name', 'genes', 'sequence'.
    """
    logging.info("Parsing protein data with ESM2 and MedGemma Bio")
    parsed_info = []
    
    for protein in proteins:
        seq = protein.get("sequence", "")
        name = protein.get("protein_name", "")
        genes = protein.get("genes", "")
        
        if not (name or seq or genes):
            parsed_info.append("No protein data available")
            continue
            
        # Generate ESM2 embedding for sequence analysis
        if seq:
            esm_embedding = get_esm2_embedding(seq)
            logging.info(f"Generated ESM2 embedding of dimension {len(esm_embedding)}")
        
        # Use MedGemma Bio for functional analysis
        analysis = analyze_protein_with_medgemma(protein)
        
        # Combine basic info with AI analysis
        basic_info = f"Protein: {name}, Genes: {genes}, Sequence Length: {len(seq)}"
        combined_analysis = f"{basic_info}\n\nMedGemma Analysis:\n{analysis}"
        parsed_info.append(combined_analysis)
    
    return parsed_info
