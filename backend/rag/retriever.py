from typing import Any

import structlog

logger = structlog.get_logger()


def retrieve(query: str, vin_meta: dict[str, Any], k: int = 5) -> list[dict[str, Any]]:
    """
    Retrieves vehicle-specific repair instruction snippets.

    Parameters:
    -----------
    query : str
        The user symptom or diagnostic search query.
    vin_meta : Dict[str, Any]
        Vehicle metadata parsed from VIN. Example keys: 'make', 'model'.
    k : int
        Number of items to retrieve.

    Returns:
    --------
    List[Dict[str, Any]]
        List of relevant manual paragraphs and their citations.
    """
    from backend.rag import get_vector_store  # Local import prevents circular deps

    # Normalize metadata keys for the search filter
    filter_metadata: dict[str, Any] = {}
    if vin_meta:
        if "make" in vin_meta and vin_meta["make"]:
            if isinstance(vin_meta["make"], list):
                filter_metadata["make"] = [str(x).upper() for x in vin_meta["make"]]
            else:
                filter_metadata["make"] = [str(vin_meta["make"]).upper()]
        if "model" in vin_meta and vin_meta["model"]:
            if isinstance(vin_meta["model"], list):
                filter_metadata["model"] = [str(x).upper() for x in vin_meta["model"]]
            else:
                filter_metadata["model"] = [str(vin_meta["model"]).upper()]
        if "engine" in vin_meta and vin_meta["engine"]:
            if isinstance(vin_meta["engine"], list):
                filter_metadata["engine"] = [str(x).upper() for x in vin_meta["engine"]]
            else:
                filter_metadata["engine"] = [str(vin_meta["engine"]).upper()]
        if "drive_type" in vin_meta and vin_meta["drive_type"]:
            if isinstance(vin_meta["drive_type"], list):
                filter_metadata["drive_type"] = [
                    str(x).upper() for x in vin_meta["drive_type"]
                ]
            else:
                filter_metadata["drive_type"] = [str(vin_meta["drive_type"]).upper()]
        if "year" in vin_meta and vin_meta["year"] not in (None, ""):
            # Stored metadata is always an int (see VehicleKey.metadata_tag),
            # but callers pass whatever type they have (e.g. the vehicle-object
            # request path stringifies it) -- coerce so the equality filter
            # in the vector store actually matches instead of silently
            # returning zero results on a type mismatch.
            try:
                filter_metadata["year"] = int(vin_meta["year"])
            except (TypeError, ValueError):
                pass

    # Fail open: if the vector store is unavailable (e.g. the knowledge-base SSD is
    # unplugged) or the query errors, return no snippets so callers fall back to
    # Gemini/templates instead of surfacing a 500.
    try:
        store = get_vector_store()
        return store.search(query=query, filter_metadata=filter_metadata, k=k)
    except Exception as exc:  # noqa: BLE001 - RAG is a best-effort augmentation
        logger.warning(
            "RAG retrieval unavailable; returning no snippets", error=str(exc)
        )
        return []
