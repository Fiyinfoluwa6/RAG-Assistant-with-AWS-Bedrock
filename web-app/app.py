import os
import logging
import boto3
from dotenv import load_dotenv
from flask import Flask, request, render_template, jsonify
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from bedrock_embeddings import BedrockNovaEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
app = Flask(__name__)

faiss_index_path = os.path.abspath(os.environ.get("FAISS_INDEX_PATH", "../ingestion/faiss_index"))

# In-memory session store
session_store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]

def get_llm():
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

# Initialize services
try:
    embedding_model = BedrockNovaEmbeddings(
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    vector_db = FAISS.load_local(faiss_index_path, embedding_model, allow_dangerous_deserialization=True)
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})

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

    chain = (
        {
            "context": lambda x: format_docs(retriever.invoke(x["question"])),
            "question": lambda x: x["question"],
            "history": lambda x: x.get("history", []),
        }
        | prompt
        | get_llm()
        | StrOutputParser()
    )

    rag_chain = RunnableWithMessageHistory(
        chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )
    logger.info("Services initialized successfully")

except Exception as e:
    logger.error(f"Failed to initialize services: {e}")
    exit(1)


@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json()
        question = data.get("question", "").strip()
        session_id = data.get("session_id", "default")

        if not question:
            return jsonify({"error": "Please enter your question."})
        if question.lower() in ["thank you", "thanks", "thank you!"]:
            return jsonify({"answer": "You're welcome!"})
        if question.lower() in ["bye", "exit", "stop", "end"]:
            return jsonify({"answer": "Goodbye!"})

        answer = rag_chain.invoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}}
        )
        return jsonify({"answer": answer})

    except Exception as e:
        logger.error(f"Failed to process question: {e}")
        return jsonify({"error": "An error occurred while processing your question."})


@app.route("/")
def home():
    return render_template("home.html")


if __name__ == "__main__":
    app.run(debug=True)
