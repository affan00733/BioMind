import logging
import base64
from google.cloud import vision
from google import genai
from utils.config_utils import get_config

def analyze_image_with_medgemma_vision(image_path):
    """
    Analyze biomedical images using MedGemma Vision Model for specialized interpretation.
    """
    logging.info("Analyzing biomedical image with MedGemma Vision Model")
    
    try:
        # Read and encode image
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create multimodal content for MedGemma Vision
        multimodal_content = [
            {
                "text": """
                Analyze this biomedical image and provide detailed interpretation:
                
                1. **Image Type**: Identify the type of biomedical visualization (microscopy, X-ray, MRI, etc.)
                2. **Anatomical/Structural Elements**: Describe visible structures, cells, tissues, or organs
                3. **Pathological Features**: Identify any abnormalities, lesions, or disease markers
                4. **Quantitative Analysis**: Measure dimensions, counts, or other measurable features
                5. **Clinical Significance**: Interpret findings in medical context
                6. **Research Implications**: Suggest research directions or hypotheses
                
                Focus on biomedical accuracy and clinical relevance.
                """
            },
            {
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": image_data
                }
            }
        ]
        
        # Use Gemini for multimodal analysis (MedGemma Vision equivalent)
        client = genai.Client(vertexai=True,
                              project=get_config('PROJECT_ID'),
                              location="us-central1")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=multimodal_content
        )
        
        return response.candidates[0].content.parts[0].text
        
    except Exception as e:
        logging.error(f"MedGemma Vision analysis failed: {e}")
        return f"Image analysis failed: {str(e)}"

def analyze_image(image_path):
    """
    Enhanced biomedical image analysis using MedGemma Vision Model.
    Combines traditional vision API with specialized biomedical interpretation.
    """
    logging.info("Starting enhanced biomedical image analysis")
    
    # First, get basic vision analysis
    basic_labels = []
    try:
        client = vision.ImageAnnotatorClient()
        with open(image_path, "rb") as image_file:
            content = image_file.read()
        image = vision.Image(content=content)
        response = client.label_detection(image=image)
        basic_labels = [label.description for label in response.label_annotations]
        if response.error.message:
            logging.error(f"Vision API error: {response.error.message}")
    except Exception as e:
        logging.error(f"Basic vision analysis failed: {e}")
    
    # Then, use MedGemma Vision for specialized biomedical analysis
    biomedical_analysis = analyze_image_with_medgemma_vision(image_path)
    
    # Combine results
    combined_analysis = f"""
    **Basic Vision Analysis**: {', '.join(basic_labels) if basic_labels else 'No basic labels detected'}
    
    **MedGemma Vision Biomedical Analysis**:
    {biomedical_analysis}
    """
    
    return combined_analysis
