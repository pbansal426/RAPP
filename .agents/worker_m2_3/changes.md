# Changes Report

This document records the modifications made to fix the case-sensitivity filtering mismatch in `ChromaVectorStore.search()`.

## Files Modified

- `backend/rag/vector_store.py`

## Modifications Details

### `backend/rag/vector_store.py`

Refactored `ChromaVectorStore.search()` to handle case normalization on incoming query filters.

**Rationale:**
During document ingestion, metadata fields `make`, `model`, `engine`, and `drive_type` are normalized to uppercase (converting single strings or lists of strings before converting lists to comma-separated strings). When querying ChromaDB, the incoming filters were previously constructed using the original raw mixed-case filter metadata. Because ChromaDB is case-sensitive, this caused matches to fail (e.g. searching for `Honda` failed to match the stored `HONDA`).

**Implementation:**
We added a normalization step prior to constructing the `where` clause filters inside `ChromaVectorStore.search`. If the key is one of `make`, `model`, `engine`, or `drive_type`, the filter value is converted to uppercase.
- For string values: converted using `.upper()`.
- For list values: each item in the list is converted using `.upper()` if it is a string.

```python
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
```

## Verification

The unit tests were run using:
```bash
PYTHONPATH=. .venv/bin/pytest tests/unit/test_rag.py
```
All 10 tests passed successfully, including `test_list_type_metadata_filtering` (which previously failed on the ChromaDB integration part).
