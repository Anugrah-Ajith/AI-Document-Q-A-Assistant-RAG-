import hashlib
import logging
import math
from typing import List
import numpy as np
from openai import OpenAI
from app.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Generates dense vector embeddings using OpenAI's embedding API,
    with an automatic deterministic fallback for offline/test environments.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.model = model if model is not None else settings.EMBEDDING_MODEL
        self.base_url = base_url if base_url is not None else settings.OPENAI_BASE_URL
        self.dimension = 1536  # Standard for text-embedding-3-small

        self.client: OpenAI | None = None
        if self.api_key and self.api_key.strip() and not self.api_key.startswith("your_openai"):
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI client: {e}. Fallback enabled.")
                self.client = None

    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Generates a deterministic 1536-dimensional normalized embedding based on
        n-gram hashing and character features. Ensures cosine similarity reflects
        lexical and semantic term overlap for offline testing and development.
        """
        vec = np.zeros(self.dimension, dtype=np.float32)
        words = text.lower().split()
        if not words:
            return vec.tolist()

        # Word-level hashed features
        for w in words:
            h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
            vec[idx] += sign * 1.5

        # Character 3-gram features for subword similarity
        cleaned = "".join(filter(str.isalnum, text.lower()))
        for i in range(max(0, len(cleaned) - 2)):
            gram = cleaned[i:i + 3]
            h = int(hashlib.sha256(gram.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vec[idx] += sign * 0.5

        # L2 normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List[List[float]]: List of 1536-dim normalized vector embeddings.
        """
        if not texts:
            return []

        # If live OpenAI client is available, call the API in batches
        if self.client is not None:
            try:
                batch_size = 64
                all_embeddings: List[List[float]] = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.model
                    )
                    sorted_data = sorted(response.data, key=lambda x: x.index)
                    all_embeddings.extend([item.embedding for item in sorted_data])
                return all_embeddings
            except Exception as e:
                logger.error(f"OpenAI embedding API call failed: {e}. Falling back to deterministic embedding.")

        # Fallback path for offline/development/test mode
        return [self._fallback_embedding(t) for t in texts]

    def get_single_embedding(self, text: str) -> List[float]:
        """Generates embedding for a single query or text chunk."""
        results = self.get_embeddings([text])
        return results[0] if results else [0.0] * self.dimension
