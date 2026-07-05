from typing import Any


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

    store = get_vector_store()

    # Normalize metadata keys for the search filter
    filter_metadata = {}
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
        if "year" in vin_meta and vin_meta["year"] is not None:
            filter_metadata["year"] = vin_meta["year"]

    return store.search(query=query, filter_metadata=filter_metadata, k=k)
