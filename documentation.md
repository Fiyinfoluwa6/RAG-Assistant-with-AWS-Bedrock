# RAG System Documentation

## What This Project Does

This is a Retrieval-Augmented Generation (RAG) system. It lets you ask questions in plain English and get answers based on your own documents. It works in two steps:

1. **Ingestion** — reads your documents, converts them into vectors (embeddings), and saves them locally
2. **Query** — when you ask a question, it finds the most relevant parts of your documents and sends them to an AI model to generate an answer

---

## Tech Stack

| Component | Tool | Why |
|---|---|---|
| LLM (chat model) | AWS Bedrock — Claude Sonnet 4 | Generates answers |
| Embeddings | AWS Bedrock — Amazon Nova Multimodal | Converts text to vectors |
| Vector Store | FAISS (local file) | Stores and searches embeddings |
| API Framework | FastAPI | Test endpoint |
| Web App | Flask | Chat UI |
| Document Loaders | LangChain | Reads .txt and .pdf files |

---

## Project Structure

```
milvus-open-ai/
│
├── .env                        # All your credentials and config (edit this)
├── bedrock_embeddings.py       # Custom Amazon Nova embeddings class (root copy)
├── test-api.py                 # FastAPI server for testing
├── test-requirements.txt       # Dependencies for the FastAPI server
├── system-workflow-chart.html  # Visual workflow diagram (open in browser)
│
├── ingestion/
│   ├── ingest.py               # Reads documents and saves to FAISS index
│   ├── bedrock_embeddings.py   # Copy of embeddings class used by ingestion
│   ├── test_embedding.py       # One-off script to test Bedrock embeddings
│   ├── requirements.txt        # Dependencies for ingestion
│   └── data/                   # PUT YOUR DOCUMENTS HERE (.txt and .pdf)
│       ├── about-me.txt
│       └── your-file.pdf
│
├── ingestion/faiss_index/      # AUTO-GENERATED after running ingest.py
│   ├── index.faiss             # The vector index
│   └── index.pkl               # Metadata
│
├── web-app/
│   ├── app.py                  # Flask web application
│   ├── bedrock_embeddings.py   # Copy of embeddings class used by web app
│   ├── requirements.txt        # Dependencies for the web app
│   └── templates/
│       └── home.html           # Chat UI frontend
│
└── venv/                       # Python virtual environment (do not edit)
```

---

## Configuration — `.env` File

This is the only file you need to edit to configure the system.

```env
# Set to "true" to use AWS Bedrock, "false" to use OpenAI
USE_BEDROCK=true

# Your AWS credentials (rotate these if exposed)
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-1

# Bedrock model for chat responses
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0

# Bedrock model for embeddings
BEDROCK_EMBEDDING_MODEL_ID=amazon.nova-2-multimodal-embeddings-v1:0

# Path to the FAISS index (auto-created by ingest.py)
FAISS_INDEX_PATH=./ingestion/faiss_index
```

---

## Step-by-Step Setup

### Step 1 — Create and activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

Your terminal prompt should show `(venv)` when active.

### Step 2 — Install dependencies

```bash
# For ingestion
pip install -r ingestion/requirements.txt

# For the FastAPI test server
pip install -r test-requirements.txt
```

### Step 3 — Add your documents

Drop any `.txt` or `.pdf` files into the `ingestion/data/` folder.

### Step 4 — Run ingestion

This reads your documents, generates embeddings using Amazon Nova, and saves the FAISS index locally.

```bash
cd ingestion
python ingest.py
cd ..
```

You should see output like:
```
INFO: Loaded 2 documents from data/
INFO: Split into 12 chunks
INFO: Embedding document 1/12
...
INFO: Saved FAISS index to .../ingestion/faiss_index
```

### Step 5 — Start the FastAPI test server

```bash
python test-api.py
```

You should see:
```
Starting RAG API — AWS Bedrock + FAISS
Docs:   http://localhost:8000/docs
Health: http://localhost:8000/health
```

### Step 6 — Test the API

```bash
# Check all services are healthy
curl http://localhost:8000/health

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about your automation experience"}'

# Open interactive docs in browser
open http://localhost:8000/docs
```

### Step 7 — Run the Flask web app (optional)

```bash
cd web-app
pip install -r requirements.txt
python app.py
```

Then open: http://localhost:5000

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | API info |
| GET | `/health` | Check all services status |
| POST | `/ask` | Ask a question |
| GET | `/reset-memory/{session_id}` | Clear conversation history |
| GET | `/docs` | Interactive Swagger UI |

### Example `/ask` request

```json
{
  "question": "What is your cloud experience?",
  "session_id": "user-123"
}
```

### Example `/ask` response

```json
{
  "answer": "Based on the documents...",
  "status": "success"
}
```

The `session_id` is optional (defaults to `"default"`). Use different session IDs to maintain separate conversations.

---

## How the Embeddings Work

The custom `BedrockNovaEmbeddings` class (in `bedrock_embeddings.py`) wraps the Amazon Nova multimodal embeddings model.

- **Indexing** (`embed_documents`) — uses `GENERIC_INDEX` purpose, called during ingestion
- **Querying** (`embed_query`) — uses `TEXT_RETRIEVAL` purpose, called when you ask a question

The correct request format for the model is:

```json
{
  "schemaVersion": "nova-multimodal-embed-v1",
  "taskType": "SINGLE_EMBEDDING",
  "singleEmbeddingParams": {
    "embeddingPurpose": "GENERIC_INDEX",
    "embeddingDimension": 1024,
    "text": {
      "value": "your text here",
      "truncationMode": "END"
    }
  }
}
```

---

## AWS Requirements

Make sure your AWS IAM user has these permissions:

```json
{
  "Effect": "Allow",
  "Action": "bedrock:InvokeModel",
  "Resource": [
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-2-multimodal-embeddings-v1:0",
    "arn:aws:bedrock:us-east-1::foundation-model/us.anthropic.claude-sonnet-4-20250514-v1:0"
  ]
}
```

Also enable both models in the [Bedrock Model Access console](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess).

---

## Re-ingesting Documents

If you add new documents to `ingestion/data/`, re-run ingestion:

```bash
cd ingestion
python ingest.py
```

This will append new embeddings to the existing FAISS index (`drop_old=False`).

To start fresh (wipe and rebuild the index), change `drop_old=False` to `drop_old=True` in `ingest.py` for one run.

---

## Troubleshooting

| Error | Fix |
|---|---|
| `UnrecognizedClientException: security token invalid` | Your AWS keys are wrong or expired. Rotate them in IAM console |
| `FAISS index not found` | Run `python ingest.py` first from the `ingestion/` folder |
| `No module named 'dotenv'` | Run `source venv/bin/activate` then `pip install -r requirements.txt` |
| `No documents loaded` | Make sure files are in `ingestion/data/` and are `.txt` or `.pdf` |
| `ModuleNotFoundError` | Make sure venv is active: `source venv/bin/activate` |
