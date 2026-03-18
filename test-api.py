#!/usr/bin/env python3
"""
FastAPI Test Endpoint for RAG System
AWS Bedrock (Claude) + Amazon Nova Embeddings + FAISS
"""

import os
import logging
from typing import Dict
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from bedrock_embeddings import BedrockNovaEmbeddings

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USE_BEDROCK = os.environ.get("USE_BEDROCK", "true").lower() == "true"
faiss_index_path = os.path.abspath(os.environ.get("FAISS_INDEX_PATH", "./faiss_index"))

app = FastAPI(
    title="RAG Test API",
    description="AWS Bedrock + Amazon Nova Embeddings + FAISS",
    version="1.0.0"
)

class QuestionRequest(BaseModel):
    question: str
    session_id: str = "default"

class QuestionResponse(BaseModel):
    answer: str
    status: str = "success"

class HealthResponse(BaseModel):
    status: str
    message: str
    services: Dict[str, str]

rag_chain = None
retriever = None
# In-memory session store
session_store: Dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]

def get_llm():
    import boto3
    from langchain_aws import ChatBedrock
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )
    model_id = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
    logger.info(f"Using Bedrock model: {model_id}")
    return ChatBedrock(
        client=bedrock_client,
        model_id=model_id,
        model_kwargs={"temperature": 0.7, "max_tokens": 1024},
    )

def initialize_services():
    global rag_chain, retriever

    if not all([os.environ.get("AWS_ACCESS_KEY_ID"), os.environ.get("AWS_SECRET_ACCESS_KEY")]):
        raise ValueError("Missing AWS credentials")

    if not os.path.exists(faiss_index_path):
        raise FileNotFoundError(f"FAISS index not found at {faiss_index_path}. Run ingest.py first.")

    embedding_model = BedrockNovaEmbeddings(
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )

    vector_db = FAISS.load_local(faiss_index_path, embedding_model, allow_dangerous_deserialization=True)
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

    llm = get_llm()

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a helpful assistant. Answer questions based on the provided context.
If you don't know the answer from the context, say 'I am sorry, I don't have that information.'
Answer in English (USA).

Context:
{context}"""),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Build LCEL chain
    chain = (
        {
            "context": lambda x: format_docs(retriever.invoke(x["question"])),
            "question": lambda x: x["question"],
            "history": lambda x: x.get("history", []),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    rag_chain = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )

    logger.info("All services initialized successfully")

@app.on_event("startup")
async def startup_event():
    try:
        initialize_services()
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.get("/")
async def root():
    return {
        "message": "RAG Test API",
        "model_provider": "AWS Bedrock",
        "vector_store": "FAISS",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    services = {
        "model_provider": "bedrock",
        "vector_store": "faiss",
        "index": "loaded" if retriever else "not_loaded",
        "rag_chain": "initialized" if rag_chain else "not_initialized",
    }
    status = "healthy" if (retriever and rag_chain) else "unhealthy"
    return HealthResponse(status=status, message=f"System is {status}", services=services)

@app.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    if not rag_chain:
        raise HTTPException(status_code=503, detail="RAG chain not initialized")

    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if question.lower() in ["thank you", "thanks", "thank you!"]:
        return QuestionResponse(answer="You're welcome!")
    if question.lower() in ["bye", "exit", "stop", "end"]:
        return QuestionResponse(answer="Goodbye!")

    try:
        logger.info(f"Processing: {question}")
        answer = rag_chain.invoke(
            {"question": question},
            config={"configurable": {"session_id": request.session_id}}
        )
        return QuestionResponse(answer=answer)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your question")

@app.get("/reset-memory/{session_id}")
async def reset_memory(session_id: str = "default"):
    if session_id in session_store:
        session_store[session_id].clear()
        return {"message": f"Memory cleared for session: {session_id}"}
    return {"message": "Session not found"}

if __name__ == "__main__":
    import uvicorn
    print("\nStarting RAG API — AWS Bedrock + FAISS")
    print("Docs:   http://localhost:8000/docs")
    print("Health: http://localhost:8000/health\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
