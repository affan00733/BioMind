import logging
from agents.coordinator_agent import CoordinatorAgent

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    print("🧠 BioMind Voice Lab - Real-Time Biomedical Research Assistant")
    print("=" * 60)
    print("🔴 REAL-TIME MODE: Fetching fresh data from APIs")
    print("⚡ Caching enabled for 5 minutes to optimize performance")
    
    # Show connector status
    import os
    enable_pubmed = os.getenv("ENABLE_PUBMED", "true").lower() == "true"
    enable_uniprot = os.getenv("ENABLE_UNIPROT", "true").lower() == "true"
    enable_drugbank = os.getenv("ENABLE_DRUGBANK", "false").lower() == "true"
    enable_google_health = os.getenv("ENABLE_GOOGLE_HEALTH_BLOG", "false").lower() == "true"
    
    print("📚 Active Data Sources:")
    print(f"   📖 PubMed: {'🟢 ENABLED' if enable_pubmed else '🔴 DISABLED'}")
    print(f"   🧬 UniProt: {'🟢 ENABLED' if enable_uniprot else '🔴 DISABLED'}")
    print(f"   💊 DrugBank: {'🟢 ENABLED' if enable_drugbank else '🔴 DISABLED'}")
    print(f"   🏥 Google Health Blog: {'🟢 ENABLED' if enable_google_health else '🔴 DISABLED'}")
    print("=" * 60)
    
    while True:
        try:
            question = input("\n🔬 Enter your biomedical question (or 'quit' to exit): ")
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if not question.strip():
                print("❌ Please enter a valid question.")
                continue
            
            print(f"\n🚀 Processing: '{question}'")
            print("⏳ Fetching real-time data and generating hypothesis...")
            
            coordinator = CoordinatorAgent()
            hypothesis, confidence = coordinator.run_pipeline(question)
            
            print("\n" + "="*60)
            print("🎯 RESULTS")
            print("="*60)
            print(f"📊 Confidence Score: {confidence:.2f}%")
            print("\n🧬 Generated Hypothesis:")
            print("-" * 40)
            print(hypothesis)
            print("="*60)
            
            # Ask if user wants to continue
            continue_choice = input("\n❓ Ask another question? (y/n): ")
            if continue_choice.lower() not in ['y', 'yes', '']:
                print("👋 Goodbye!")
                break
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            print("Please try again or contact support.")

if __name__ == "__main__":
    main()
