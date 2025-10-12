def check_consistency(texts):
    """Check if all given texts are identical."""
    return len(set(texts)) == 1
