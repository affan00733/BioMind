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

# Vertex AI Vector Search (formerly Matching Engine)
# Provide these to enable Vector Search. Requires an existing endpoint with a deployed index.
MATCHING_ENGINE_ENABLED=false   # or VECTOR_SEARCH_ENABLED=true
# Full resource name: projects/{project}/locations/{location}/indexEndpoints/{indexEndpointId}
MATCHING_ENGINE_INDEX_ENDPOINT=projects/your-project-id/locations/us-central1/indexEndpoints/0000000000000000000
# Deployed index ID inside the endpoint
MATCHING_ENGINE_DEPLOYED_INDEX_ID=your-deployed-index-id
# Aliases also supported:
# VECTOR_SEARCH_INDEX_ENDPOINT=...
# VECTOR_SEARCH_DEPLOYED_INDEX_ID=...
# Number of neighbors per query
MATCHING_ENGINE_NUM_NEIGHBORS=10
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
- **Embeddings**: `text-embedding-005`
- **Vision**: `gemini-2.5-flash-lite` (multimodal)

## 🧭 RAG: Vector Search + Generation

This repo includes a lightweight RAG path using Vertex AI Vector Search (Matching Engine) for retrieval and Gemini for answer generation with citations.

### Configure

Create/update your `.env` with:

```bash
# Required
GOOGLE_CLOUD_PROJECT=trusty-frame-474816-m0
LOCATION=us-central1

# Vertex AI Vector Search (existing endpoint with a deployed index)
MATCHING_ENGINE_INDEX_ENDPOINT=projects/95557543251/locations/us-central1/indexEndpoints/1767612276208041984
MATCHING_ENGINE_DEPLOYED_INDEX_ID=biomind_deployed_index_2

# Optional
MATCHING_ENGINE_NUM_NEIGHBORS=8
EMBEDDING_MODEL=text-embedding-005
GENERATION_MODEL=gemini-2.5-flash-lite
```

Corpus options:

- Local (default sample): `data/corpus.jsonl` (id, text, source)
- Remote (recommended for cloud runs): set `CORPUS_URI` to a GCS path, e.g., `gs://YOUR_BUCKET/path/corpus.jsonl`.

To publish local corpus to GCS:

1. Authenticate: `gcloud auth application-default login`
2. Run: `python scripts/publish_corpus_to_gcs.py --bucket YOUR_BUCKET --dest path/corpus.jsonl`
3. Set in `.env`: `CORPUS_URI=gs://YOUR_BUCKET/path/corpus.jsonl`

If you prefer not to persist UI state to disk, set `UI_PERSIST_STATE=false` in `.env` (history/collections will be in-memory only).

### Run the RAG CLI

```bash
source .venv/bin/activate
python scripts/rag_query.py "What roles do amyloid-beta and tau play in Alzheimer’s disease?" --k 6
```

What it does:
- Embeds the query with `text-embedding-005`
- Retrieves top-k nearest neighbors from the configured Matching Engine endpoint
- Maps neighbor ids to texts from `data/corpus.jsonl`
- Re-ranks and selects passages
- Generates an answer with citations using Gemini
- Prints a compact validation summary (coverage and warnings)

### HTTP API Endpoints (FastAPI)

New endpoints are available for web clients:

- POST /api/rag/search
   - JSON body: { "query": string, "mode": "General" | "Scholar", "k"?: number, "min_score_threshold"?: number, "temperature"?: number, "model"?: string }
   - The optional "model" may be a friendly choice like "gemini" or "claude". Gemini is the default. Claude requires Vertex Anthropic Publisher availability.

- POST /api/rag/search_upload
   - multipart/form-data fields: query (text), mode (text), k (text/number), min_score_threshold (text/number), temperature (text/number), model (text), files (one or more file parts)
   - Supported files: .pdf, .docx, .txt (best-effort extraction). Extracted text is included in the RAG context and cited as [Source ID: upload-n].

Responses include a diagnostics object, e.g. { effective_model, uploaded_docs, neighbors, mapped_docs, ... }.

## �️ LINER-like UI (Streamlit)

A lightweight UI mirrors the LINER layout: Search with General/Scholar, Advanced Search controls, answer with citations, Sources preview, History, Collections, and an Agents (Beta) panel.

### Run the UI

```bash
cd BioMind
source .venv/bin/activate
pip install -r requirements.txt
streamlit run ui/app.py
```

### Features
- Search page: query input, General/Scholar toggle, Advanced Search (Top-K, source filters, threshold, temperature, Upgrade stub)
- Answer with inline [Source ID] citations and a Sources panel with expandable previews
- Save sources to Collections (stored in-memory unless `UI_PERSIST_STATE=true`, which writes to `data/ui_state.json`)
- History of recent queries
- Agents (Beta): Hypothesis Generator, Hypothesis Evaluator (confidence score), Citation Recommender, Literature Review, Research Tracer, Survey Simulator, Peer Review

Theme: Dark theme configured in `.streamlit/config.toml`.

## �📊 Confidence Scoring

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

---

## Run fully on GCP (no local data)

Follow these steps to ensure all storage and retrieval happen on GCP:

1) Enable APIs and authenticate
```
gcloud services enable aiplatform.googleapis.com storage.googleapis.com run.googleapis.com secretmanager.googleapis.com
gcloud auth application-default login
```

2) Configure env in `BioMind/.env`
- Set GOOGLE_CLOUD_PROJECT and LOCATION
- Set MATCHING_ENGINE_INDEX_ENDPOINT and MATCHING_ENGINE_DEPLOYED_INDEX_ID
- Set STRICT_REMOTE_CORPUS=true
- Set CORPUS_URI=gs://<bucket>/<path>/corpus.jsonl

3) Upload corpus.jsonl to GCS
```
python -m scripts.upload_corpus_to_gcs --source ./corpus.jsonl
```

4) Optional local dev (no disk persistence)
```
cd BioMind && source .venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 8025 --reload
```
Frontend:
```
cd web && npm install && npm run dev
# open http://localhost:3000/search
```

5) Deploy backend to Cloud Run
```
cd BioMind
gcloud builds submit --tag gcr.io/$PROJECT/biomind-api
gcloud run deploy biomind-api \
   --image gcr.io/$PROJECT/biomind-api \
   --region us-central1 \
   --allow-unauthenticated \
   --service-account biomind-api@$PROJECT.iam.gserviceaccount.com \
   --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT,LOCATION=us-central1,STRICT_REMOTE_CORPUS=true,EMBEDDING_MODEL=text-embedding-005,GENERATION_MODEL=gemini-2.5-flash-lite,MATCHING_ENGINE_INDEX_ENDPOINT='projects/XXX/locations/us-central1/indexEndpoints/YYY',MATCHING_ENGINE_DEPLOYED_INDEX_ID='biomind_deployed_index_2',CORPUS_URI='gs://<bucket>/<path>/corpus.jsonl',ALLOWED_ORIGINS='https://your-frontend-domain'
```

6) Deploy frontend (Cloud Run SSR or Firebase Hosting)
- Cloud Run SSR:
```
cd web
gcloud builds submit --tag gcr.io/$PROJECT/biomind-web
gcloud run deploy biomind-web \
   --image gcr.io/$PROJECT/biomind-web \
   --region us-central1 \
   --allow-unauthenticated \
   --set-env-vars NEXT_PUBLIC_API_BASE=https://<cloud-run-backend>
```
- Firebase Hosting: build static and deploy; set NEXT_PUBLIC_API_BASE accordingly.

7) Verify
```
curl -sS https://<cloud-run-backend>/healthz
```



# Start backend
cd /Users/mohneet/Documents/GOOGLE_Hackathon_AI_accelerate
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
uvicorn BioMind.api.server:app --reload --host 0.0.0.0 --port 8000

# In a second terminal: frontend
cd /Users/mohneet/Documents/GOOGLE_Hackathon_AI_accelerate/web
npm install
npm run dev