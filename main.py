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

    # Example queries helper (so users know what to ask)
    def _print_examples():
        print("\n💡 Example biomedical queries you can try:")
        print("   • Summarize the latest research on long COVID and neurological effects")
        print("   • What biomarkers are associated with early-stage Alzheimer's disease?")
        print("   • How does intermittent fasting impact inflammatory pathways?")
        print("   • Generate a testable hypothesis on gut microbiome and anxiety")
        if enable_pubmed:
            print("\n📖 PubMed-focused:")
            print("   • What are recent clinical trial findings for GLP-1 agonists in NASH?")
            print("   • Find emerging risk factors for post-viral myocarditis")
        if enable_uniprot:
            print("\n🧬 Protein/UniProt-focused:")
            print("   • Which proteins interact with ACE2 and how might that affect viral entry?")
            print("   • List UniProt annotations for TP53 variants relevant to cancer")
        if enable_drugbank:
            print("\n💊 Drug/DrugBank-focused:")
            print("   • Compare mechanism and adverse effects of metformin vs. pioglitazone")
            print("   • Identify potential drug–drug interactions for Paxlovid")
        if enable_google_health:
            print("\n🏥 Public health/news (Google Health Blog):")
            print("   • Summarize recent public health guidance on RSV vaccines")
        print("\nTip: Type 'help' to see these examples again.")

    # Show initial examples
    _print_examples()
    
    while True:
        try:
            question = input("\n🔬 Enter your biomedical question (type 'help' for examples, or 'quit' to exit): ")
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            # Show examples on demand
            if question.strip().lower() in ['help', 'examples', '?']:
                _print_examples()
                continue
                
            if not question.strip():
                print("❌ Please enter a valid question.")
                _print_examples()
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
