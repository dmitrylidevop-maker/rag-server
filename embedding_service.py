"""
Embedding service for converting text to vectors and vice versa.
Uses the all-MiniLM-L6-v2 model from sentence-transformers.
"""

from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class EmbeddingService:
    """Service for handling text-to-vector conversions"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedding service with a specific model.
        
        Args:
            model_name: Name of the sentence-transformers model to use
        """
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Loaded embedding model: {model_name} (dimension: {self.dimension})")
    
    def encode(self, text: str) -> List[float]:
        """
        Convert text to embedding vector.
        
        Args:
            text: Input text to encode
            
        Returns:
            List of floats representing the embedding vector
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Convert multiple texts to embedding vectors.
        
        Args:
            texts: List of input texts to encode
            
        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def get_dimension(self) -> int:
        """
        Get the dimensionality of the embeddings.
        
        Returns:
            Embedding dimension (384 for all-MiniLM-L6-v2)
        """
        return self.dimension


# Global instance - loaded once at startup
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global embedding service instance.
    
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
