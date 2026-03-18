import os
import logging
from dotenv import load_dotenv
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from bedrock_embeddings import BedrockNovaEmbeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
aws_region = os.environ.get("AWS_REGION", "us-east-1")
faiss_index_path = os.path.abspath(os.environ.get("FAISS_INDEX_PATH", "../faiss_index"))

if not all([aws_access_key_id, aws_secret_access_key]):
    logger.error("Missing required environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
    exit(1)


def load_docs(directory_path):
    try:
        documents = []

        # Load .txt files
        txt_loader = DirectoryLoader(directory_path, glob="**/*.txt", loader_cls=TextLoader)
        documents.extend(txt_loader.load())

        # Load .pdf files
        pdf_loader = DirectoryLoader(directory_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
        documents.extend(pdf_loader.load())

        logger.info(f"Loaded {len(documents)} documents from {directory_path}")
        return documents
    except Exception as e:
        logger.error(f"Failed to load documents: {e}")
        return []


def split_docs(documents, chunk_size=500, chunk_overlap=20):
    try:
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        docs = splitter.split_documents(documents)
        logger.info(f"Split into {len(docs)} chunks")
        return docs
    except Exception as e:
        logger.error(f"Failed to split documents: {e}")
        return []


def store_embeddings(docs):
    try:
        embedding_model = BedrockNovaEmbeddings(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=aws_region,
        )
        db = FAISS.from_documents(docs, embedding_model)
        db.save_local(faiss_index_path)
        logger.info(f"Saved FAISS index to {faiss_index_path}")
    except Exception as e:
        logger.error(f"Failed to store embeddings: {e}")


def main():
    documents = load_docs("data/")
    if not documents:
        logger.error("No documents loaded.")
        exit(1)
    docs = split_docs(documents)
    if not docs:
        logger.error("No document chunks created.")
        exit(1)
    store_embeddings(docs)


if __name__ == "__main__":
    main()
