import abc
import os
import time
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = structlog.get_logger(__name__)

GEMINI_EMBEDDING_MODEL = "text-embedding-004"


class VectorStore(abc.ABC):
    """Abstract interface for our Vector Database layer."""

    @abc.abstractmethod
    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        """
        Ingest documents. Format:
        [
            {"id": "doc_id_1", "text": "Raw text content", "metadata": {"year": 2010...}},
            ...
        ]
        """
        pass

    @abc.abstractmethod
    def search(
        self, query: str, filter_metadata: dict[str, Any] | None = None, k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search documents returning k nearest neighbors based on semantic query.
        Returns:
        [
            {"id": "doc_1", "text": "...", "metadata": {}, "distance": 0.23},
            ...
        ]
        """
        pass


class ChromaVectorStore(VectorStore):
    """
    Implementation using ChromaDB with automatic local persistence and Gemini Embeddings.
    """

    def __init__(
        self,
        persistent_path: str | None = "./data/chroma_db",
        collection_name: str = "repair_manuals",
    ) -> None:
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as err:
            raise ImportError(
                "chromadb is not installed. Please install it using `pip install chromadb`"
            ) from err

        if persistent_path:
            self.client = chromadb.PersistentClient(
                path=persistent_path, settings=Settings(anonymized_telemetry=False)
            )
        else:
            self.client = chromadb.EphemeralClient(
                settings=Settings(anonymized_telemetry=False)
            )

        # Initialize Gemini Client if API key is present
        self.use_gemini_embeddings = (
            os.environ.get("USE_GEMINI_EMBEDDINGS", "true").lower() == "true"
        )
        self.genai_client: Any = None
        self.genai_types: Any = None

        if self.use_gemini_embeddings:
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if not gemini_api_key:
                logger.warning(
                    "USE_GEMINI_EMBEDDINGS is true but GEMINI_API_KEY is not set. Falling back to default embeddings."
                )
                self.use_gemini_embeddings = False
            else:
                try:
                    from google import genai
                    from google.genai import types as genai_types

                    self.genai_client = genai.Client(api_key=gemini_api_key)
                    self.genai_types = genai_types
                    logger.info("Gemini embeddings initialized for vector store")
                except Exception as e:
                    logger.warning(
                        "Failed to initialize Gemini client, falling back to default embeddings",
                        error=str(e),
                    )
                    self.use_gemini_embeddings = False

        self.collection: Any = self.client.get_or_create_collection(name=collection_name)

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def _embed_texts_with_retry(
        self, texts: list[str], task_type: str
    ) -> list[list[float]]:
        response = self.genai_client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=texts,
            config=self.genai_types.EmbedContentConfig(
                task_type=task_type,
            ),
        )
        return [e.values for e in response.embeddings]

    def _embed_texts(self, texts: list[str], task_type: str) -> list[list[float]]:
        """Generate embeddings using Gemini text-embedding-004 in batches."""
        if not self.use_gemini_embeddings or not self.genai_client:
            raise ValueError("Gemini embeddings are not configured.")

        batch_size = 100
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                embeddings = self._embed_texts_with_retry(batch, task_type)
                all_embeddings.extend(embeddings)
                time.sleep(0.5)  # Slight sleep to respect rate limits
            except Exception as e:
                logger.error(
                    f"Failed to generate Gemini embeddings for batch {i//batch_size}",
                    error=str(e),
                )
                raise
        return all_embeddings

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        """
        Adds or upserts flat documents and handles ChromaDB metadata serialization limits.
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

            # ChromaDB metadata must have flat types (str, int, float, bool)
            flat_metadata = {}
            for k, v in doc.get("metadata", {}).items():
                if k in ("make", "model", "engine", "drive_type"):
                    if isinstance(v, str):
                        v = v.upper()
                    elif isinstance(v, list):
                        v = [
                            val.upper() if isinstance(val, str) else val for val in v
                        ]

                if isinstance(v, str | int | float | bool):
                    flat_metadata[k] = v
                elif isinstance(v, list):
                    flat_metadata[k] = ",".join(map(str, v))
                elif v is None:
                    continue
                else:
                    flat_metadata[k] = str(v)
            metadatas.append(flat_metadata)

        # Generate embeddings using Gemini if configured
        if self.use_gemini_embeddings and self.genai_client:
            embeddings = self._embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

        # Upsert documents with or without pre-computed embeddings
        if self.use_gemini_embeddings and embeddings:
            self.collection.upsert(
                ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings
            )
        else:
            self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

    def search(
        self, query: str, filter_metadata: dict[str, Any] | None = None, k: int = 5
    ) -> list[dict[str, Any]]:
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

        where_clause: Any = None
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
                    if isinstance(value, str | int | float | bool):
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
                    query_embeddings = self._embed_texts(
                        [query], task_type="RETRIEVAL_QUERY"
                    )
                    results = self.collection.query(
                        query_embeddings=query_embeddings,
                        n_results=n_results,
                        where=where_clause,
                    )
                except Exception as e:
                    logger.error("Gemini query embedding failed.", error=str(e))
                    raise
            else:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where=where_clause,
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
                doc_meta = (
                    metadatas[idx]
                    if idx < len(metadatas) and metadatas[idx] is not None
                    else {}
                )
                doc_dist = distances[idx] if idx < len(distances) else 0.0
                formatted_results.append(
                    {
                        "id": doc_id,
                        "text": doc_text,
                        "metadata": doc_meta,
                        "distance": doc_dist,
                    }
                )

        return formatted_results


class MockVectorStore(VectorStore):
    """
    A lightweight, in-memory Mock Vector Store designed for unit tests
    and offline development without chromadb dependencies.
    """

    def __init__(self) -> None:
        self.documents: list[dict[str, Any]] = []

    def add_documents(self, documents: list[dict[str, Any]]) -> None:
        for doc in documents:
            flat_metadata = {}
            for k, v in doc.get("metadata", {}).items():
                if k in ("make", "model", "engine", "drive_type"):
                    if isinstance(v, str):
                        v = v.upper()
                    elif isinstance(v, list):
                        v = [
                            val.upper() if isinstance(val, str) else val for val in v
                        ]

                if isinstance(v, str | int | float | bool):
                    flat_metadata[k] = v
                elif isinstance(v, list):
                    flat_metadata[k] = ",".join(map(str, v))
                elif v is None:
                    continue
                else:
                    flat_metadata[k] = str(v)

            new_doc = {"id": doc["id"], "text": doc["text"], "metadata": flat_metadata}

            # Upsert behavior: replace if ID exists
            existing_idx = next(
                (i for i, d in enumerate(self.documents) if d["id"] == new_doc["id"]),
                None,
            )
            if existing_idx is not None:
                self.documents[existing_idx] = new_doc
            else:
                self.documents.append(new_doc)

    def search(
        self, query: str, filter_metadata: dict[str, Any] | None = None, k: int = 5
    ) -> list[dict[str, Any]]:
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
            return w.strip(".,!?;:")

        query_words = {clean_word(w) for w in query.lower().split() if clean_word(w)}
        scored_docs = []
        for doc in filtered_docs:
            doc_words = {
                clean_word(w) for w in doc["text"].lower().split() if clean_word(w)
            }
            overlap = len(query_words.intersection(doc_words))
            # Distance mapping: higher overlap = lower distance
            distance = 1.0 / (1.0 + overlap)
            scored_docs.append((distance, doc))

        scored_docs.sort(key=lambda x: x[0])

        results = []
        for dist, doc in scored_docs[:k]:
            results.append(
                {
                    "id": doc["id"],
                    "text": doc["text"],
                    "metadata": doc["metadata"],
                    "distance": dist,
                }
            )
        return results
