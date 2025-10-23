import re

def clean_text(text):
    """Simple text cleaning."""
    text = re.sub(r'\s+', ' ', text).strip()
    return text
