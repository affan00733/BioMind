#!/usr/bin/env python3
"""
Quick test to verify the Google GenAI import fix
"""

def test_imports():
    """Test if all imports work correctly."""
    print("🧪 Testing Google GenAI import fixes...")
    
    try:
        # Test basic import
        import google.generativeai as genai
        print("✅ google.generativeai imported successfully")
        
        # Test agent imports
        from agents.coordinator_agent import CoordinatorAgent
        print("✅ Coordinator agent imported")
        
        from agents.retriever_agent import retrieve_relevant_docs
        print("✅ Retriever agent imported")
        
        from agents.literature_agent import summarize_papers
        print("✅ Literature agent imported")
        
        from agents.protein_agent import parse_proteins
        print("✅ Protein agent imported")
        
        from agents.drug_agent import analyze_drugs
        print("✅ Drug agent imported")
        
        from agents.hypothesis_synthesizer import synthesize_hypothesis
        print("✅ Hypothesis synthesizer imported")
        
        from agents.image_agent import analyze_image_with_medgemma_vision
        print("✅ Image agent imported")
        
        from confidence_evaluator import evaluate_confidence
        print("✅ Confidence evaluator imported")
        
        print("\n🎉 All imports successful! The GenAI import issue has been fixed.")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

if __name__ == "__main__":
    test_imports()
