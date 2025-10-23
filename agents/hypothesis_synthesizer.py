import logging
from google import genai
from utils.config_utils import get_config

def synthesize_hypothesis(query, lit_summaries, prot_info, drug_info, image_info):
    """
    Enhanced hypothesis synthesis using Gemini 2.5 Flash-Lite for cross-domain reasoning.
    Integrates outputs from all domain-specific agents to form a coherent hypothesis.
    """
    logging.info("Synthesizing hypothesis with Gemini 2.5 Flash-Lite for cross-domain reasoning")

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
    1. Cross-links literature, protein, and drug findings
    2. Explains biological mechanisms
    3. Grounds reasoning in cited evidence
    4. Highlights novel or unexpected patterns
    5. Mentions possible therapeutic implications
    6. Suggests next research steps

    **Output Format**:
    - Hypothesis Statement
    - Mechanistic Explanation
    - Evidence Summary
    - Confidence Factors
    - Research Implications
    """

    try:
        # ✅ Use the new GenAI client (no genai.configure!)
        client = genai.Client(
            vertexai=True,
            project=get_config("PROJECT_ID"),
            location="us-central1"
        )

        # ✅ Use the new model name
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[prompt]
        )

        hypothesis = response.candidates[0].content.parts[0].text
        logging.info("Hypothesis synthesis completed successfully")

    except Exception as e:
        logging.error(f"Hypothesis synthesis failed: {e}")
        hypothesis = f"Hypothesis synthesis failed for query: {query}"

    return hypothesis
