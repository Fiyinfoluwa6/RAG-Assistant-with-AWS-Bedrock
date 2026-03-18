# RAG Assistant with AWS Bedrock

A Retrieval-Augmented Generation (RAG) system that lets you chat with your own documents using AWS Bedrock for both the LLM and embeddings, with FAISS as a local vector store. No Docker required.

---

## What's New

The original project used OpenAI and Milvus (Docker). This version has been fully updated to:

- Replace OpenAI LLM with **AWS Bedrock (Claude Sonnet 4)**
- Replace OpenAI embeddings with **Amazon Nova Multimodal Embeddings**
- Replace Milvus (Docker) with **FAISS** (local file, no Docker needed)
- Add a **FastAPI test endpoint** for quick API testing
- Add **PDF support** alongside `.txt` files in ingestion
- Upgrade to **LangChain v1.x** (LCEL pattern, no deprecated chains)
- Redesign the **Flask chat UI** with dark theme, markdown rendering, and syntax highlighting

---

## Tech Stack

| Component | Tool |
|---|---|
| LLM | AWS Bedrock — `us.anthropic.claude-sonnet-4-20250514-v1:0` |
| Embeddings | AWS Bedrock — `amazon.nova-2-multimodal-embeddings-v1:0` |
| Vector Store | FAISS (local file) |
| API Framework | FastAPI |
| Web App | Flask |
| Document Loaders | LangChain (`.txt` and `.pdf`) |

---

## Project Structure

```
RAG-Assistant-with-AWS-Bedrock/
│
├── .env.example                # Copy this to .env and fill in your credentials
├── bedrock_embeddings.py       # Custom LangChain embeddings wrapper for Amazon Nova
├── test-api.py                 # FastAPI server for testing
├── test-requirements.txt       # Dependencies for FastAPI server
├── documentation.md            # Full setup and usage documentation
├── system-workflow-chart.html  # Visual workflow diagram
│
├── ingestion/
│   ├── ingest.py               # Loads documents → generates embeddings → saves FAISS index
│   ├── bedrock_embeddings.py   # Copy of embeddings class
│   ├── requirements.txt        # Ingestion dependencies
│   └── data/                   # Drop your .txt and .pdf files here
│
└── web-app/
    ├── app.py                  # Flask web application
    ├── bedrock_embeddings.py   # Copy of embeddings class
    ├── requirements.txt        # Web app dependencies
    └── templates/
        └── home.html           # Chat UI (dark theme, markdown, syntax highlighting)
```

---

## Prerequisites

- Python 3.10+
- AWS account with Bedrock access
- Both models enabled in [Bedrock Model Access](https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess):
  - `amazon.nova-2-multimodal-embeddings-v1:0`
  - `us.anthropic.claude-sonnet-4-20250514-v1:0`
- IAM user with `bedrock:InvokeModel` permission for both models

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/Fiyinfoluwa6/RAG-Assistant-with-AWS-Bedrock.git
cd RAG-Assistant-with-AWS-Bedrock
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
USE_BEDROCK=true
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
BEDROCK_EMBEDDING_MODEL_ID=amazon.nova-2-multimodal-embeddings-v1:0
FAISS_INDEX_PATH=/absolute/path/to/ingestion/faiss_index
```

### 4. Add your documents

Drop `.txt` or `.pdf` files into `ingestion/data/`.

### 5. Run ingestion

```bash
pip install -r ingestion/requirements.txt
cd ingestion
python ingest.py
cd ..
```

This generates the FAISS index at `ingestion/faiss_index/`.

---

## Running the App

### FastAPI test server

```bash
pip install -r test-requirements.txt
python test-api.py
```

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

```bash
# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this document about?"}'
```

### Flask web app

```bash
pip install -r web-app/requirements.txt
python web-app/app.py
```

Open: http://localhost:5000

---

## Chat UI Features

- Dark theme with smooth animations
- Markdown rendering for structured AI responses
- Syntax highlighted code blocks with copy button
- Typing indicator while waiting for response
- Auto-resizing input textarea
- Suggestion chips on the welcome screen
- Session-based conversation memory
- Enter to send, Shift+Enter for new line

---

## How It Works

```
Documents (.txt / .pdf)
        ↓
   ingest.py
        ↓
Amazon Nova Embeddings (AWS Bedrock)
        ↓
   FAISS Index (local file)
        ↓
   User asks question
        ↓
Query embedded → Top 5 similar chunks retrieved
        ↓
Claude Sonnet 4 (AWS Bedrock) generates answer
        ↓
   Response returned
```

---

## Security

- Never commit your `.env` file — it is gitignored
- Use `.env.example` as a template
- Rotate AWS keys immediately if exposed
- Manage IAM permissions with least privilege

---

## Original Project

This project is based on [sprider/milvus-open-ai](https://github.com/sprider/milvus-open-ai), updated to use AWS Bedrock and FAISS.
