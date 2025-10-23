# BioMind Voice Lab 🧠

A **real-time** multi-agent biomedical research assistant that integrates Fivetran, Google Cloud, and Vertex AI services to deliver fresh, evidence-backed hypothesis generation from live data sources.

## 🧠 System Overview

BioMind Voice Lab combines multiple specialized AI agents to process biomedical queries, **fetch fresh data in real-time** from live APIs, and generate confident hypotheses with quantitative scoring.

### 🔴 **REAL-TIME FEATURES**
- **Live Data Fetching**: Queries PubMed, UniProt, and DrugBank APIs in real-time
- **Smart Caching**: 5-minute cache to optimize performance and reduce API calls
- **Fallback System**: BigQuery vector search if APIs are unavailable
- **Rate Limiting**: Built-in API rate limiting to prevent overload

### Architecture Components

- **Real-Time Data Fetching**: Live API calls to PubMed, UniProt, DrugBank (no pre-loading required!)
- **Smart Retriever Agent**: Real-time data fetching with intelligent caching and BigQuery fallback
- **Coordinator Agent**: Gemini Pro for task orchestration and agent routing
- **Domain Agents**:
  - Literature Agent: MedGemma/Gemini 1.5 Flash for paper summarization
  - Protein Agent: ESM2 + MedGemma Bio for UniProt sequence analysis
  - Drug Agent: Gemini Pro + DrugBank API for drug-target reasoning
  - Image Agent: MedGemma Vision for biomedical figure interpretation
- **Hypothesis Synthesizer**: Cross-domain reasoning and hypothesis formation
- **Confidence Evaluator**: Evidence, Consistency, and Novelty scoring

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Google Cloud Platform account
- GCP project with billing enabled
- Google Cloud SDK installed

### 1. Install Google Cloud SDK

```bash
# macOS
brew install --cask google-cloud-sdk

# Linux/Windows
# Download from https://cloud.google.com/sdk/docs/install
```

### 2. Authenticate and Set Project

```bash
# Authenticate with your Google account
gcloud auth login

# Set the active project (replace with your project ID)
gcloud config set project trusty-frame-474816-m0

# Verify configuration
gcloud config list
```

### 3. Enable Required APIs

```bash
gcloud services enable \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com \
  servicemanagement.googleapis.com \
  serviceusage.googleapis.com
```

### 4. Create Application Default Credentials

```bash
gcloud auth application-default login
```

### 5. Create Cloud Storage Bucket

```bash
BUCKET_NAME=biomind-lab-data-trusty
gsutil mb -l us-central1 gs://$BUCKET_NAME
```

### 6. Create BigQuery Dataset

```bash
bq --location=US mk --dataset trusty-frame-474816-m0:biomind_data
```

### 7. Set Up Virtual Environment

```bash
# Navigate to project directory
cd /path/to/biomind-lab

# Create virtual environment
python3 -m venv biomind_env
source biomind_env/bin/activate  # On Windows: biomind_env\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 8. Set Environment Variables

```bash
export GCP_PROJECT_ID="trusty-frame-474816-m0"
export GOOGLE_CLOUD_PROJECT="trusty-frame-474816-m0"
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
```

### 9. Test the Setup

```bash
python - <<'EOF'
from google import genai

client = genai.Client(vertexai=True, project="trusty-frame-474816-m0", location="us-central1")
response = client.models.generate_content(
    model="gemini-2.5-flash-lite",
    contents=["Summarize the importance of protein folding in neurodegenerative diseases."]
)
print("✅ GenAI call successful!")
print(response.candidates[0].content.parts[0].text)
EOF
```

## 📖 Usage

### 🚀 Real-Time Usage

```python
from agents.coordinator_agent import CoordinatorAgent

# Initialize the coordinator
coordinator = CoordinatorAgent()

# Ask a biomedical question - gets FRESH data!
question = "Find potential protein-drug links for Alzheimer's related amyloid aggregation."
hypothesis, confidence = coordinator.run_pipeline(question)

print(f"Generated Hypothesis:\n{hypothesis}")
print(f"Confidence Score: {confidence:.2f}%")
```

### Running the Real-Time Application

```bash
python main.py
```

**What happens in real-time:**
1. 🔍 **Live API Calls**: Fetches fresh data from enabled sources (PubMed, UniProt, DrugBank)
2. ⚡ **Smart Caching**: Uses cached data if available (5-minute TTL)
3. 🧬 **AI Analysis**: Literature, protein, and drug agents process the fresh data
4. 🎯 **Hypothesis Generation**: Cross-domain synthesis with confidence scoring
5. 📊 **Real-Time Results**: Latest findings with evidence and citations

**No data pre-loading required!** 🎉
**🔌 Connector Control**: Enable/disable data sources via environment variables

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set these environment variables:

```bash
# GCP Configuration
GCP_PROJECT_ID=trusty-frame-474816-m0
BIGQUERY_DATASET=biomind_data

# Connector Enable/Disable Flags
ENABLE_PUBMED=true
ENABLE_UNIPROT=true
ENABLE_DRUGBANK=false
ENABLE_GOOGLE_HEALTH_BLOG=false

# API Keys and Authentication
PUBMED_EMAIL=your-actual-email@domain.com
DRUGBANK_API_KEY=your-actual-drugbank-api-key
```

#### 🔌 **Connector Control Flags**

- **`ENABLE_PUBMED=true`**: Enable/disable PubMed literature search
- **`ENABLE_UNIPROT=true`**: Enable/disable UniProt protein database
- **`ENABLE_DRUGBANK=false`**: Enable/disable DrugBank API (default: disabled)
- **`ENABLE_GOOGLE_HEALTH_BLOG=false`**: Enable/disable Google Health Blog (default: disabled)

#### 🤔 **Why Google Health Blog is Disabled by Default**

Google Health Blog is disabled by default because:
1. **Web Scraping**: It requires scraping Google's blog pages (not an official API)
2. **Rate Limiting**: More prone to being blocked or rate-limited
3. **Relevance**: Less structured biomedical data compared to PubMed/UniProt
4. **Reliability**: Web scraping is less reliable than official APIs

**💡 Pro Tips**: 
- Set `ENABLE_DRUGBANK=false` if you don't have DrugBank API access
- Enable `ENABLE_GOOGLE_HEALTH_BLOG=true` if you want additional health blog insights
- The system works perfectly with just PubMed and UniProt!

### Model Configuration

The system uses the following models:
- **Text Generation**: `gemini-2.5-flash-lite` (working model)
- **Embeddings**: `textembedding-gecko@003`
- **Vision**: `gemini-2.5-flash-lite` (multimodal)

## 📊 Confidence Scoring

The confidence evaluator computes scores based on three factors:

1. **Evidence (40%)**: Supporting information from trusted sources (PubMed, UniProt, DrugBank)
2. **Consistency (35%)**: Agreement between domain agent outputs
3. **Novelty (25%)**: Detection of new relationships not in existing databases

## 🏗️ Project Structure

```
biomind-lab/
├── agents/                    # Specialized AI agents
│   ├── coordinator_agent.py   # Main orchestration
│   ├── retriever_agent.py     # Data retrieval and search
│   ├── literature_agent.py    # Paper analysis
│   ├── protein_agent.py       # Protein sequence analysis
│   ├── drug_agent.py          # Drug-target reasoning
│   ├── image_agent.py         # Biomedical image analysis
│   └── hypothesis_synthesizer.py # Cross-domain synthesis
├── connectors/                # Data source connectors
│   ├── pubmed/               # PubMed API integration
│   ├── uniprot/              # UniProt database
│   ├── drugbank/             # DrugBank API
│   └── google_health_blog/   # Google Health Blog
├── utils/                    # Utility functions
│   ├── config_utils.py       # Configuration management
│   ├── nli_utils.py          # Natural language inference
│   └── text_utils.py         # Text processing
├── pipelines/                # Data processing pipelines
│   └── data_ingestion.py     # Data ingestion workflows
├── main.py                   # Application entry point
├── confidence_evaluator.py   # Hypothesis confidence scoring
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## 🔬 Example Use Cases

### 1. Drug Discovery Research
```
Query: "Find potential protein-drug links for Alzheimer's related amyloid aggregation."
Output: Hypothesis about compound X inhibiting amyloid-beta aggregation via protein Y binding
Confidence: 78% (high evidence, good consistency, moderate novelty)
```

### 2. Disease Mechanism Analysis
```
Query: "How do mutations in BRCA1 affect protein function and cancer risk?"
Output: Detailed mechanistic analysis of BRCA1 mutations, protein folding, and cancer pathways
Confidence: 85% (strong evidence, high consistency, low novelty)
```

### 3. Drug Repurposing
```
Query: "Can existing diabetes drugs be repurposed for neurodegenerative diseases?"
Output: Analysis of metabolic pathways, drug mechanisms, and potential cross-disease applications
Confidence: 72% (moderate evidence, good consistency, high novelty)
```

## 🚨 Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   gcloud auth application-default login
   ```

2. **API Not Enabled**
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

3. **BigQuery Dataset Missing**
   ```bash
   bq --location=US mk --dataset trusty-frame-474816-m0:biomind_data
   ```

4. **Model Not Found**
   - Ensure you're using the correct project ID
   - Check that Vertex AI is enabled in your region (us-central1)

### Logging

The application uses Python's logging module. To increase verbosity:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is part of the Google AI Accelerator challenge.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the Google Cloud documentation
3. Create an issue in the repository

## 🔮 Future Enhancements

- Real-time data streaming with Pub/Sub
- Advanced ESM2 model integration
- Custom MedGemma model deployment
- Multi-language support
- API endpoint development
- Web interface for non-technical users
