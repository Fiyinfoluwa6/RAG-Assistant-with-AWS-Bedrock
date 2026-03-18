"""
Custom LangChain-compatible embeddings class for Amazon Nova Multimodal Embeddings
Model: amazon.nova-2-multimodal-embeddings-v1:0
Docs: https://docs.aws.amazon.com/nova/latest/userguide/embeddings-schema.html
"""

import json
import boto3
import logging
from typing import List
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)


class BedrockNovaEmbeddings(Embeddings):

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region_name: str = "us-east-1",
        model_id: str = "amazon.nova-2-multimodal-embeddings-v1:0",
        dimension: int = 1024,
    ):
        self.model_id = model_id
        self.dimension = dimension
        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        logger.info(f"BedrockNovaEmbeddings initialized with model: {model_id}")

    def _embed_text(self, text: str, purpose: str = "GENERIC_INDEX") -> List[float]:
        """Call Bedrock Nova embeddings using the correct schema."""
        body = {
            "schemaVersion": "nova-multimodal-embed-v1",
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": purpose,
                "embeddingDimension": self.dimension,
                "text": {
                    "value": text,
                    "truncationMode": "END"
                }
            }
        }
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            result = json.loads(response["body"].read())
            return result["embeddings"][0]["embedding"]
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents using GENERIC_INDEX purpose."""
        embeddings = []
        for i, text in enumerate(texts):
            logger.info(f"Embedding document {i + 1}/{len(texts)}")
            embeddings.append(self._embed_text(text, purpose="GENERIC_INDEX"))
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Embed a query using TEXT_RETRIEVAL purpose for better search results."""
        return self._embed_text(text, purpose="TEXT_RETRIEVAL")
