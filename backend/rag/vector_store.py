import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import structlog
from google import genai
from google.genai import types as genai_types

logger = structlog.get_logger()

GEMINI_EMBEDDING_MODEL = "text-embedding-004"

class VectorStore(ABC):
    """
    Abstract Base Class defining the interface for RAG vector stores.
    """

    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add a list of documents to the vector store.

        Parameters:
        -----------
        documents : List[Dict[str, Any]]
            A list of document dictionaries, where each document has the format:
            {
                "id": str,
                "text": str,
                "metadata": Dict[str, Any]
            }
        """
        pass

    @abstractmethod
    def search(
        self, 
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for the top k documents matching the query, optionally filtered by metadata.

        Parameters:
        -----------
        query : str
            The search query.
        filter_metadata : Optional[Dict[str, Any]]
            A dictionary containing key-value metadata pairs to filter by.
        k : int
            The number of results to return.

        Returns:
        --------
        List[Dict[str, Any]]
            A list of matching documents, each structured as:
            {
                "id": str,
                "text": str,
                "metadata": Dict[str, Any],
                "distance": float
            }
        """
        pass


class ChromaVectorStore(VectorStore):
    """
    ChromaDB implementation of the VectorStore interface with Gemini embeddings.
    Encapsulates all chromadb imports and client logic.
    """

    def __init__(
        self, 
        persistent_path: Optional[str] = None, 
        collection_name: str = "repair_manuals",
        use_gemini_embeddings: bool = True
    ):
        """
        Initialize the ChromaVectorStore client.
        
        Parameters:
        -----------
        persistent_path : Optional[str]
            Path to persistent directory. If None, runs an ephemeral client.
        collection_name : str
            Name of the collection to use.
        use_gemini_embeddings : bool
            Whether to use Gemini embeddings instead of default ChromaDB embeddings.
        """
        import chromadb  # Confined import

        self.collection_name = collection_name
        self.use_gemini_embeddings = use_gemini_embeddings
        
        if persistent_path:
            os.makedirs(persistent_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=persistent_path)
        else:
            self.client = chromadb.EphemeralClient()
            
        # Initialize Gemini client if using Gemini embeddings
        self.genai_client = None
        if self.use_gemini_embeddings:
            try:
                self.genai_client = genai.Client()
                logger.info("Gemini embeddings initialized for vector store")
            except Exception as e:
                logger.warning("Failed to initialize Gemini client, falling back to default embeddings", error=str(e))
                self.use_gemini_embeddings = False
        
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Adds flat documents and handles ChromaDB metadata serialization limits.
        Uses Gemini embeddings if configured.
        """
        if not documents:
            return

        ids = []
        texts = []
        metadatas = []
        embeddings = []

        for doc in documents:
            ids.append(doc["id"])
            texts.append(doc["text"])
            
            # Generate embeddings using Gemini if configured
            if self.use_gemini_embeddings and self.genai_client:
                try:
                    embedding = self._generate_gemini_embedding(doc["text"])
                    embeddings.append(embedding)
                except Exception as e:
                    logger.warning(f"Failed to generate Gemini embedding for {doc['id']}, using default", error=str(e))
                    embeddings.append(None)
            
            # ChromaDB metadata must have flat types (str, int, float, bool)
            flat_metadata = {}
            for k, v in doc.get("metadata", {}).items():
                if k in ("make", "model", "engine", "drive_type"):
                    if isinstance(v, str):
                        v = v.upper()
                    elif isinstance(v, list):
                        v = [val.upper() if isinstance(val, str) else val for val in v]
                
                if isinstance(v, (str, int, float, bool)):
                    flat_metadata[k] = v
                elif isinstance(v, list):
                    flat_metadata[k] = ",".join(map(str, v))
                elif v is None:
                    continue
                else:
                    flat_metadata[k] = str(v)
            metadatas.append(flat_metadata)

        # Add documents with or without pre-computed embeddings
        if self.use_gemini_embeddings and all(e is not None for e in embeddings):
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas,
                embeddings=embeddings
            )
        else:
            self.collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )

    def search(
        self, 
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Queries ChromaDB collection, constructing filters dynamically.
        Uses Gemini embeddings for query if configured.
        """
        try:
            count = self.collection.count()
        except Exception:
            return []

        if count == 0:
            return []

        where_clause = None
        if filter_metadata:
            normalized_filters = {}
            for key, value in filter_metadata.items():
                if key in ("make", "model", "engine", "drive_type"):
                    if isinstance(value, str):
                        value = value.upper()
                    elif isinstance(value, list):
                        value = [v.upper() if isinstance(v, str) else v for v in value]
                normalized_filters[key] = value

            filter_conditions = []
            for key, value in normalized_filters.items():
                if value is not None:
                    if isinstance(value, list):
                        value = ",".join(map(str, value))
                    if isinstance(value, (str, int, float, bool)):
                        filter_conditions.append({key: {"$eq": value}})
                    else:
                        filter_conditions.append({key: {"$eq": str(value)}})
            
            if len(filter_conditions) == 1:
                where_clause = filter_conditions[0]
            elif len(filter_conditions) > 1:
                where_clause = {"$and": filter_conditions}

        try:
            n_results = min(k, count)
            
            # Use Gemini embeddings for query if configured
            if self.use_gemini_embeddings and self.genai_client:
                try:
                    query_embedding = self._generate_gemini_embedding(query)
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=n_results,
                        where=where_clause
                    )
                except Exception as e:
                    logger.warning("Gemini query embedding failed, falling back to default", error=str(e))
                    results = self.collection.query(
                        query_texts=[query],
                        n_results=n_results,
                        where=where_clause
                    )
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_clause
                )
        except Exception as e:
            logger.warning("ChromaDB query failed", error=str(e))
            return []

        formatted_results = []
        if results and results.get("documents"):
            ids = results.get("ids", [[]])[0] or []
            docs = results.get("documents", [[]])[0] or []
            metadatas = results.get("metadatas", [[]])[0] or []
            distances = results.get("distances", [[]])[0] or []

            for idx in range(len(docs)):
                doc_id = ids[idx] if idx < len(ids) else f"unknown_{idx}"
                doc_text = docs[idx]
                doc_meta = metadatas[idx] if idx < len(metadatas) and metadatas[idx] is not None else {}
                doc_dist = distances[idx] if idx < len(distances) else 0.0
                formatted_results.append({
                    "id": doc_id,
                    "text": doc_text,
                    "metadata": doc_meta,
                    "distance": doc_dist
                })

        return formatted_results
    
    def _generate_gemini_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini text-embedding-004."""
        try:
            response = self.genai_client.models.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                content=text,
                config=genai_types.EmbedContentConfig(
                    task_type="retrieval_document",
                )
            )
            return response.embedding.values
        except Exception as e:
            logger.error("Failed to generate Gemini embedding", error=str(e))
            raise


class MockVectorStore(VectorStore):
    """
    A lightweight, in-memory Mock Vector Store designed for unit tests 
    and offline development without chromadb dependencies.
    """

    def __init__(self):
        self.documents: List[Dict[str, Any]] = []

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        for doc in documents:
            flat_metadata = {}
            for k, v in doc.get("metadata", {}).items():
                if k in ("make", "model", "engine", "drive_type"):
                    if isinstance(v, str):
                        v = v.upper()
                    elif isinstance(v, list):
                        v = [val.upper() if isinstance(val, str) else val for val in v]
                
                if isinstance(v, (str, int, float, bool)):
                    flat_metadata[k] = v
                elif isinstance(v, list):
                    flat_metadata[k] = ",".join(map(str, v))
                elif v is None:
                    continue
                else:
                    flat_metadata[k] = str(v)
            self.documents.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": flat_metadata
            })

    def search(
        self, 
        query: str, 
        filter_metadata: Optional[Dict[str, Any]] = None, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        filtered_docs = []

        # 1. Filter by metadata values
        for doc in self.documents:
            match = True
            doc_meta = doc.get("metadata", {})
            if filter_metadata:
                for key, val in filter_metadata.items():
                    if val is not None:
                        if isinstance(val, list):
                            val = ",".join(map(str, val))
                        doc_val = doc_meta.get(key)
                        if str(doc_val).lower() != str(val).lower():
                            match = False
                            break
            if match:
                filtered_docs.append(doc)

        # 2. Score text matching by word overlap
        def clean_word(w: str) -> str:
            return w.strip(".,!?;;:")
            
        query_words = {clean_word(w) for w in query.lower().split() if clean_word(w)}
        scored_docs = []
        for doc in filtered_docs:
            doc_words = {clean_word(w) for w in doc["text"].lower().split() if clean_word(w)}
            overlap = len(query_words.intersection(doc_words))
            # Distance mapping: higher overlap = lower distance
            distance = 1.0 / (1.0 + overlap)
            scored_docs.append((distance, doc))

        scored_docs.sort(key=lambda x: x[0])
        
        results = []
        for dist, doc in scored_docs[:k]:
            results.append({
                "id": doc["id"],
                "text": doc["text"],
                "metadata": doc["metadata"],
                "distance": dist
            })
        return results
