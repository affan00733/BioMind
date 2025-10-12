import logging
from google import genai
from utils.config_utils import get_config

def synthesize_hypothesis(query, lit_summaries, prot_info, drug_info, image_info):
    """
    Enhanced hypothesis synthesis using Gemini 1.5 Pro for cross-domain reasoning and scoring.
    Integrates outputs from all domain-specific agents to form a coherent hypothesis.
    """
    logging.info("Synthesizing hypothesis with Gemini 1.5 Pro for cross-domain reasoning")
    
    prompt = f"""
    **Biomedical Research Question**: {query}
    
    **Available Evidence**:
    
    **Literature Analysis**:
    {chr(10).join(lit_summaries) if lit_summaries else "No literature data available"}
    
    **Protein Analysis**:
    {chr(10).join(prot_info) if prot_info else "No protein data available"}
    
    **Drug Analysis**:
    {chr(10).join(drug_info) if drug_info else "No drug data available"}
    
    **Image Analysis**:
    {image_info if image_info else "No image data available"}
    
    **Instructions**:
    Based on the above multi-domain evidence, synthesize a comprehensive biomedical hypothesis that:
    
    1. **Cross-Domain Integration**: Links findings across literature, protein, and drug domains
    2. **Mechanistic Reasoning**: Explains the biological mechanisms involved
    3. **Evidence-Based**: Grounded in the provided data and citations
    4. **Novel Insights**: Identifies potential new relationships or discoveries
    5. **Clinical Relevance**: Considers therapeutic implications
    6. **Research Direction**: Suggests next steps for validation
    
    **Output Format**:
    - **Hypothesis Statement**: Clear, testable hypothesis
    - **Mechanistic Explanation**: Biological pathways and interactions
    - **Evidence Summary**: Key supporting evidence from each domain
    - **Confidence Factors**: What makes this hypothesis strong/weak
    - **Research Implications**: Potential applications and next steps
    """

    client = genai.Client(vertexai=True,
                          project=get_config('PROJECT_ID'),
                          location="us-central1")
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",  # Using the working model
            contents=[prompt]
        )
        hypothesis = response.candidates[0].content.parts[0].text
        logging.info("Hypothesis synthesis completed successfully")
    except Exception as e:
        logging.error(f"Hypothesis synthesis failed: {e}")
        hypothesis = f"Hypothesis synthesis failed for query: {query}"
    
    return hypothesis
