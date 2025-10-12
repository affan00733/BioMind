import logging
from google import genai
from utils.config_utils import get_config

def summarize_papers(papers):
    """
    Enhanced literature summarization using MedGemma or Gemini 1.5 Flash.
    Each paper is a dict with 'title' and 'abstract'.
    """
    logging.info("Starting enhanced literature summarization with MedGemma/Gemini")
    client = genai.Client(vertexai=True,
                          project=get_config('PROJECT_ID'),
                          location="us-central1")
    summaries = []
    
    for i, paper in enumerate(papers):
        title = paper.get("title", "")
        abstract = paper.get("abstract", "")
        
        prompt = f"""
        Analyze this biomedical research paper and provide a comprehensive summary:
        
        Title: {title}
        Abstract: {abstract}
        
        Please provide:
        1. **Key Findings**: Main discoveries and results
        2. **Methodology**: Research methods used
        3. **Clinical Significance**: Medical implications
        4. **Citations**: Relevant references and related work
        5. **Research Gaps**: Areas for future investigation
        6. **Biomedical Context**: How this fits into broader medical knowledge
        
        Focus on biomedical accuracy and clinical relevance.
        """
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=[prompt]
            )
            summary = response.candidates[0].content.parts[0].text
            
            # Add paper metadata to summary
            enhanced_summary = f"**Paper {i+1}: {title}**\n\n{summary}\n\n---"
            summaries.append(enhanced_summary)
            
        except Exception as e:
            logging.error(f"Literature summarization failed for paper {i+1}: {e}")
            summaries.append(f"**Paper {i+1}: {title}**\n\nSummarization failed.\n\n---")
    
    return summaries
