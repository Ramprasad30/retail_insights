"""
RAG (Retrieval-Augmented Generation) & Vector Store Integration
Enables semantic search and context retrieval for better LLM responses
"""

import os
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import logging
import hashlib

logger = logging.getLogger(__name__)


# ============================================================================
# VECTOR STORE ABSTRACTION
# ============================================================================

class VectorStore(ABC):
    """Abstract vector store interface"""
    
    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents with embeddings to store"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        pass
    
    @abstractmethod
    def delete_all(self):
        """Clear all documents"""
        pass


class FAISSVectorStore(VectorStore):
    """FAISS-based vector store (included in requirements)"""
    
    def __init__(self, dimension: int = 384, index_path: Optional[str] = None):
        try:
            import faiss
            import numpy as np
            
            self.dimension = dimension
            self.index_path = index_path
            self.documents = []
            
            # Create or load FAISS index
            if index_path and os.path.exists(index_path):
                self.index = faiss.read_index(index_path)
                logger.info(f"Loaded FAISS index from {index_path}")
            else:
                # Create flat index (exact search, good for <1M vectors)
                self.index = faiss.IndexFlatL2(dimension)
                logger.info(f"Created new FAISS index (dim={dimension})")
                
        except ImportError:
            logger.error("FAISS not installed. Install with: pip install faiss-cpu")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents with embeddings"""
        import numpy as np
        
        embeddings = []
        for doc in documents:
            if "embedding" in doc:
                embeddings.append(doc["embedding"])
                self.documents.append(doc)
        
        if embeddings:
            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)
            logger.info(f"Added {len(embeddings)} documents to FAISS")
            
            # Save index if path specified
            if self.index_path:
                import faiss
                faiss.write_index(self.index, self.index_path)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        import numpy as np
        
        # Get query embedding
        query_embedding = self._get_embedding(query)
        query_array = np.array([query_embedding]).astype('float32')
        
        # Search
        distances, indices = self.index.search(query_array, min(top_k, len(self.documents)))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc["score"] = float(1 / (1 + dist))  # Convert distance to similarity score
                results.append(doc)
        
        return results
    
    def delete_all(self):
        """Clear all documents"""
        import faiss
        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []
        logger.info("Cleared FAISS index")
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text - placeholder, override with actual embedder"""
        # This should be replaced with actual embedding model
        import numpy as np
        # Simple hash-based embedding for demo (replace with sentence-transformers)
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        return np.random.rand(self.dimension).tolist()


class ChromaVectorStore(VectorStore):
    """ChromaDB vector store (included in requirements)"""
    
    def __init__(self, collection_name: str = "retail_insights", persist_directory: Optional[str] = None):
        try:
            import chromadb
            from chromadb.config import Settings
            
            if persist_directory:
                self.client = chromadb.Client(Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=persist_directory
                ))
            else:
                self.client = chromadb.Client()
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                metadata={"description": "Retail insights knowledge base"}
            )
            logger.info(f"Initialized ChromaDB collection: {collection_name}")
            
        except ImportError:
            logger.error("ChromaDB not installed. Install with: pip install chromadb")
            raise
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """Add documents to ChromaDB"""
        ids = []
        texts = []
        metadatas = []
        embeddings = []
        
        for i, doc in enumerate(documents):
            doc_id = doc.get("id", f"doc_{i}")
            ids.append(doc_id)
            texts.append(doc.get("text", ""))
            metadatas.append(doc.get("metadata", {}))
            
            if "embedding" in doc:
                embeddings.append(doc["embedding"])
        
        # Add to collection
        if embeddings:
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings
            )
        else:
            # ChromaDB will generate embeddings automatically
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
        
        logger.info(f"Added {len(documents)} documents to ChromaDB")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search ChromaDB"""
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        formatted_results = []
        if results['documents']:
            for i, doc in enumerate(results['documents'][0]):
                formatted_results.append({
                    "text": doc,
                    "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                    "score": 1 - results['distances'][0][i] if results['distances'] else 1.0,
                    "id": results['ids'][0][i] if results['ids'] else f"doc_{i}"
                })
        
        return formatted_results
    
    def delete_all(self):
        """Clear all documents"""
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.create_collection(self.collection.name)
        logger.info("Cleared ChromaDB collection")


# ============================================================================
# EMBEDDING GENERATOR
# ============================================================================

class EmbeddingGenerator:
    """Generate embeddings for text using various models"""
    
    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        self.model_name = model
        self.model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize embedding model"""
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            logger.info(f"Loaded embedding model: {self.model_name}")
        except ImportError:
            logger.warning("sentence-transformers not installed. Install: pip install sentence-transformers")
            self.model = None
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        if self.model:
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        else:
            # Fallback: use simple hash-based embeddings
            logger.warning("Using fallback hash-based embeddings")
            return [self._hash_embedding(text) for text in texts]
    
    def _hash_embedding(self, text: str, dim: int = 384) -> List[float]:
        """Simple hash-based embedding (fallback)"""
        import numpy as np
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        np.random.seed(hash_val % (2**32))
        return np.random.rand(dim).tolist()


# ============================================================================
# RAG RETRIEVER
# ============================================================================

class RAGRetriever:
    """Retrieval-Augmented Generation retriever"""
    
    def __init__(self, vector_store: VectorStore, embedding_generator: Optional[EmbeddingGenerator] = None):
        self.vector_store = vector_store
        self.embedder = embedding_generator or EmbeddingGenerator()
    
    def index_knowledge_base(self, knowledge_items: List[Dict[str, str]]):
        """Index knowledge base items"""
        documents = []
        texts = [item["text"] for item in knowledge_items]
        
        # Generate embeddings
        embeddings = self.embedder.embed(texts)
        
        # Create documents
        for i, item in enumerate(knowledge_items):
            documents.append({
                "id": item.get("id", f"kb_{i}"),
                "text": item["text"],
                "embedding": embeddings[i],
                "metadata": item.get("metadata", {})
            })
        
        # Add to vector store
        self.vector_store.add_documents(documents)
        logger.info(f"Indexed {len(documents)} knowledge base items")
    
    def retrieve_context(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve relevant context for query"""
        results = self.vector_store.search(query, top_k)
        logger.info(f"Retrieved {len(results)} context items for query: {query[:50]}...")
        return results
    
    def augment_prompt(self, query: str, base_prompt: str, top_k: int = 3) -> str:
        """Augment prompt with retrieved context"""
        context_items = self.retrieve_context(query, top_k)
        
        if not context_items:
            return base_prompt
        
        # Build context section
        context_text = "\n\n**Relevant Context:**\n"
        for i, item in enumerate(context_items, 1):
            context_text += f"{i}. {item['text']}\n"
        
        # Augment prompt
        augmented_prompt = f"{base_prompt}\n{context_text}\n\nUser Query: {query}"
        return augmented_prompt


# ============================================================================
# KNOWLEDGE BASE BUILDER
# ============================================================================

class RetailKnowledgeBaseBuilder:
    """Build knowledge base from retail data summaries"""
    
    @staticmethod
    def build_from_summary_stats(summary_stats: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create knowledge base items from summary statistics"""
        knowledge_items = []
        
        # Amazon Sales insights
        if "amazon_sales" in summary_stats:
            amazon = summary_stats["amazon_sales"]
            knowledge_items.append({
                "id": "amazon_overview",
                "text": f"Amazon sales overview: Total revenue is ₹{amazon.get('total_revenue', 0):,.0f} from {amazon.get('total_orders', 0):,} orders with an average order value of ₹{amazon.get('avg_order_value', 0):.2f}. There are {amazon.get('unique_categories', 0)} unique product categories and {amazon.get('unique_states', 0)} states served.",
                "metadata": {"source": "summary_stats", "category": "overview"}
            })
        
        # Top categories
        if "top_categories" in summary_stats:
            for cat in summary_stats["top_categories"][:5]:
                knowledge_items.append({
                    "id": f"category_{cat.get('Category', '').lower().replace(' ', '_')}",
                    "text": f"{cat.get('Category')} category generated ₹{cat.get('revenue', 0):,.0f} in revenue from {cat.get('order_count', 0):,} orders.",
                    "metadata": {"source": "top_categories", "category": cat.get('Category')}
                })
        
        # Top states
        if "top_states" in summary_stats:
            for state in summary_stats["top_states"][:10]:
                knowledge_items.append({
                    "id": f"state_{state.get('state', '').lower().replace(' ', '_')}",
                    "text": f"{state.get('state')} state has ₹{state.get('revenue', 0):,.0f} in revenue from {state.get('order_count', 0):,} orders.",
                    "metadata": {"source": "top_states", "state": state.get('state')}
                })
        
        # Status distribution
        if "status_distribution" in summary_stats:
            for status in summary_stats["status_distribution"]:
                knowledge_items.append({
                    "id": f"status_{status.get('Status', '').lower().replace(' ', '_')}",
                    "text": f"Order status '{status.get('Status')}': {status.get('count', 0):,} orders ({status.get('percentage', 0)}% of total).",
                    "metadata": {"source": "status_distribution", "status": status.get('Status')}
                })
        
        # Inventory
        if "inventory" in summary_stats:
            inv = summary_stats["inventory"]
            knowledge_items.append({
                "id": "inventory_overview",
                "text": f"Inventory has {inv.get('total_skus', 0):,} SKUs with {inv.get('total_stock', 0):,} total units across {inv.get('unique_categories', 0)} categories and {inv.get('unique_colors', 0)} colors.",
                "metadata": {"source": "inventory", "category": "inventory"}
            })
        
        logger.info(f"Built knowledge base with {len(knowledge_items)} items")
        return knowledge_items


# ============================================================================
# FACTORY
# ============================================================================

class RAGFactory:
    """Factory for creating RAG components"""
    
    @staticmethod
    def create_retriever(
        store_type: str = "chroma",
        persist_dir: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2"
    ) -> RAGRetriever:
        """Create RAG retriever with specified components"""
        
        # Create embedder
        embedder = EmbeddingGenerator(model=embedding_model)
        
        # Create vector store
        if store_type == "faiss":
            vector_store = FAISSVectorStore(
                dimension=384,  # all-MiniLM-L6-v2 dimension
                index_path=persist_dir
            )
        elif store_type == "chroma":
            vector_store = ChromaVectorStore(
                collection_name="retail_insights",
                persist_directory=persist_dir
            )
        else:
            raise ValueError(f"Unknown store type: {store_type}")
        
        return RAGRetriever(vector_store, embedder)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example: Create RAG retriever
    retriever = RAGFactory.create_retriever(store_type="chroma")
    
    # Example: Build knowledge base from summary stats
    sample_stats = {
        "amazon_sales": {
            "total_revenue": 5000000,
            "total_orders": 10000,
            "avg_order_value": 500
        },
        "top_categories": [
            {"Category": "Electronics", "revenue": 2000000, "order_count": 4000}
        ]
    }
    
    kb_items = RetailKnowledgeBaseBuilder.build_from_summary_stats(sample_stats)
    retriever.index_knowledge_base(kb_items)
    
    # Example: Retrieve context
    context = retriever.retrieve_context("What are the top categories?", top_k=3)
    for item in context:
        print(f"- {item['text']} (score: {item['score']:.3f})")
