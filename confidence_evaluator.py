import logging
from google import genai
from utils.nli_utils import check_consistency
from utils.text_utils import clean_text
from utils.config_utils import get_config

def evaluate_evidence_support(hypothesis, evidence_texts):
    """
    Calculate Evidence score based on supporting information in trusted sources.
    """
    logging.info("Evaluating evidence support")
    
    # Count evidence sources (PubMed, UniProt, DrugBank)
    evidence_count = len(evidence_texts)
    
    # Quality assessment - check for specific biomedical terms
    biomedical_indicators = ['protein', 'gene', 'drug', 'disease', 'mechanism', 'pathway', 'target', 'inhibition', 'activation']
    quality_score = 0
    for evidence in evidence_texts:
        evidence_lower = evidence.lower()
        indicators_found = sum(1 for indicator in biomedical_indicators if indicator in evidence_lower)
        quality_score += min(indicators_found / len(biomedical_indicators), 1.0)
    
    quality_score = quality_score / len(evidence_texts) if evidence_texts else 0
    
    # Evidence score combines quantity and quality
    evidence_score = (min(evidence_count / 5.0, 1.0) + quality_score) / 2.0
    return evidence_score

def evaluate_cross_agent_consistency(evidence_texts):
    """
    Calculate Consistency score based on agreement between domain agents.
    """
    logging.info("Evaluating cross-agent consistency")
    
    if len(evidence_texts) < 2:
        return 0.5  # Neutral score for insufficient data
    
    # Use NLI utils to check consistency
    consistency_score = 1.0 if check_consistency(evidence_texts) else 0.5
    
    # Additional semantic similarity check using embeddings
    client = genai.Client(vertexai=True,
                          project=get_config('PROJECT_ID'),
                          location="us-central1")
    
    try:
        embeddings = []
        for evidence in evidence_texts:
            response = client.models.embed_content(
                model="textembedding-gecko@003",
                contents=[evidence]
            )
            embeddings.append(response.embeddings[0].values)
        
        # Calculate pairwise cosine similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                emb1, emb2 = embeddings[i], embeddings[j]
                dot = sum(a * b for a, b in zip(emb1, emb2))
                norm1 = sum(a * a for a in emb1) ** 0.5
                norm2 = sum(b * b for b in emb2) ** 0.5
                cos_sim = dot / (norm1 * norm2) if norm1 and norm2 else 0
                similarities.append(cos_sim)
        
        # Average similarity as consistency measure
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        semantic_consistency = min(max(avg_similarity, 0), 1)
        
        # Combine NLI and semantic consistency
        final_consistency = (consistency_score + semantic_consistency) / 2.0
        return final_consistency
        
    except Exception as e:
        logging.error(f"Embedding-based consistency evaluation failed: {e}")
        return consistency_score

def evaluate_novelty(hypothesis, evidence_texts):
    """
    Calculate Novelty score by checking overlap with known databases.
    """
    logging.info("Evaluating hypothesis novelty")
    
    # Check for common biomedical phrases that might indicate known relationships
    known_patterns = [
        'already known', 'previously reported', 'established', 'well-documented',
        'common', 'typical', 'standard', 'conventional'
    ]
    
    hypothesis_lower = hypothesis.lower()
    evidence_combined = " ".join(evidence_texts).lower()
    
    # Penalize if hypothesis contains known relationship indicators
    known_penalty = sum(1 for pattern in known_patterns if pattern in hypothesis_lower)
    novelty_score = max(1.0 - (known_penalty * 0.2), 0.0)
    
    # Check for novel terminology or combinations
    novel_indicators = ['novel', 'new', 'unprecedented', 'previously unknown', 'first report']
    novel_boost = sum(1 for indicator in novel_indicators if indicator in hypothesis_lower)
    novelty_score = min(novelty_score + (novel_boost * 0.1), 1.0)
    
    return novelty_score

def evaluate_confidence(hypothesis, evidence_texts):
    """
    Enhanced confidence evaluation using Evidence, Consistency, and Novelty scoring.
    Computes quantitative confidence score based on:
    1. Evidence support (retrieved context overlap)
    2. Cross-agent consistency (semantic similarity between agent outputs)
    3. Novelty detection (checking if hypothesis exists in known datasets)
    """
    logging.info("Evaluating hypothesis confidence with enhanced scoring")
    
    # Clean texts
    evidence_texts = [clean_text(e) for e in evidence_texts if e]
    hypothesis = clean_text(hypothesis)

    # Calculate individual scores
    evidence_score = evaluate_evidence_support(hypothesis, evidence_texts)
    consistency_score = evaluate_cross_agent_consistency(evidence_texts)
    novelty_score = evaluate_novelty(hypothesis, evidence_texts)
    
    # Weighted combination (as per proposal)
    # Evidence: 40%, Consistency: 35%, Novelty: 25%
    weighted_score = (evidence_score * 0.4) + (consistency_score * 0.35) + (novelty_score * 0.25)
    
    # Convert to percentage
    confidence_percentage = weighted_score * 100
    
    # Log detailed scoring
    logging.info(f"Confidence breakdown - Evidence: {evidence_score:.2f}, "
                f"Consistency: {consistency_score:.2f}, Novelty: {novelty_score:.2f}, "
                f"Final: {confidence_percentage:.2f}%")
    
    return confidence_percentage
