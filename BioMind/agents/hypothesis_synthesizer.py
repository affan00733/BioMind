# synthesis.py
import logging
from typing import List, Optional, Dict, Any

from google import genai
from utils.config_utils import get_config


def _build_evidence_prompt(
    lit_summaries: List[str],
    prot_info: List[str],
    drug_info: List[str],
    image_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a well-structured evidence section for the model prompt."""
    sections: List[str] = []

    # Literature Findings
    sections.append("Literature Findings:")
    if lit_summaries:
        sections.extend(f"- {s}" for s in lit_summaries)
    else:
        sections.append("- No published research data available.")

    # Protein Analysis
    sections.append("\nProtein Analysis:")
    if prot_info:
        sections.extend(f"- {p}" for p in prot_info)
    else:
        sections.append("- No protein interaction data available.")

    # Drug Information
    sections.append("\nDrug Information:")
    if drug_info:
        sections.extend(f"- {d}" for d in drug_info)
    else:
        sections.append("- No pharmaceutical data available.")

    # Optional: Image / figure context
    if image_info:
        sections.append("\nImaging / Figures:")
        # Keep this generic—caller controls payload shape
        for k, v in image_info.items():
            # Convert nested values to compact strings
            try:
                text = v if isinstance(v, str) else repr(v)
            except Exception:
                text = "<unserializable>"
            sections.append(f"- {k}: {text}")

    return "\n".join(sections)


def _build_prompt(query: str, evidence: str) -> str:
    """Construct the final instruction prompt."""
    return (
        "You are a biomedical research expert. Based on the available evidence below, "
        f"analyze this research question: {query}\n\n"
        f"{evidence}\n\n"
        "Generate a focused biomedical hypothesis and analysis with clear sections:\n\n"
        "1. A specific testable hypothesis\n"
        "2. The underlying biological mechanisms\n"
        "3. Key supporting evidence from the data\n"
        "4. Clinical and therapeutic implications\n"
        "5. Concrete next research steps\n\n"
        "Format exactly as:\n\n"
        "HYPOTHESIS:\n"
        "[A clear, testable scientific hypothesis]\n\n"
        "MECHANISM:\n"
        "[Key biological pathways and mechanisms]\n\n"
        "EVIDENCE:\n"
        "[Summary of supporting data]\n\n"
        "IMPLICATIONS:\n"
        "[Clinical/therapeutic relevance]\n\n"
        "NEXT STEPS:\n"
        "[Specific research priorities]"
    )


def _extract_text_from_genai_response(response: Any) -> str:
    """
    Safely extract text from the Google GenAI response.
    Handles cases with multiple candidates/parts.
    """
    try:
        candidates = getattr(response, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if not content:
                continue
            parts = getattr(content, "parts", None) or []
            # Concatenate any text parts in order
            texts = []
            for part in parts:
                # Some SDKs put text at .text; others at .inline_data / etc.
                text = getattr(part, "text", None)
                if isinstance(text, str) and text.strip():
                    texts.append(text)
            if texts:
                return "\n".join(texts).strip()
    except Exception as e:
        logging.warning(f"Failed to parse GenAI response: {e}")
    return ""


def synthesize_hypothesis(
    query: str,
    lit_summaries: List[str],
    prot_info: List[str],
    drug_info: List[str],
    image_info: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Enhanced hypothesis synthesis using Gemini 2.5 Flash-Lite for cross-domain reasoning.
    Integrates outputs from domain-specific agents to form a coherent hypothesis.
    """
    logging.info("Synthesizing hypothesis with Gemini 2.5 Flash-Lite for cross-domain reasoning")

    evidence = _build_evidence_prompt(lit_summaries, prot_info, drug_info, image_info)
    prompt = _build_prompt(query, evidence)

    try:
        # Initialize the GenAI client (Vertex AI route)
        client = genai.Client(
            vertexai=True,
            project=get_config("PROJECT_ID"),
            location="us-central1",
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[prompt],
        )

        hypothesis = _extract_text_from_genai_response(response)
        if not hypothesis:
            logging.error("Empty hypothesis text parsed from GenAI response.")
            return "Error: Model returned no text. Please verify model name/permissions and try again."

        logging.info("Hypothesis synthesis completed successfully")
        return hypothesis

    except Exception as e:
        logging.error(f"Hypothesis synthesis failed: {e}")
        return f"Error generating hypothesis: {str(e)}"
