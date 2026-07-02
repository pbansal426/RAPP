# Handoff Report — Challenger 2 (Milestone 2)

## 1. Observation

I executed the unit test suite inside the Python virtual environment using the command:
```bash
PATH="/Users/prathambansal/Dev/RAPP/.venv/bin:$PATH" PYTHONPATH=. pytest tests/unit/test_rag.py
```

### Run 1: ChromaDB Installed (ChromaDB Mode)
When `chromadb` is installed, 1 out of 10 tests fails:
```
tests/unit/test_rag.py .......F..                                        [100%]

=================================== FAILURES ===================================
______________________ test_list_type_metadata_filtering _______________________

    def test_list_type_metadata_filtering():
...
        # Test Chroma if installed
        try:
            import chromadb
        except ImportError:
            return
    
        import tempfile
        import shutil
        tmpdir = tempfile.mkdtemp()
        try:
            chroma_store = ChromaVectorStore(persistent_path=tmpdir, collection_name="list_test")
            chroma_store.add_documents(docs)
            results = chroma_store.search("brake", filter_metadata={"make": ["Honda", "Ford"], "model": "Accord"})
>           assert len(results) == 1
E           assert 0 == 1
E            +  where 0 = len([])

tests/unit/test_rag.py:272: AssertionError
```

### Run 2: ChromaDB Uninstalled (Mock Mode Only)
When `chromadb` is uninstalled from the environment, all active tests pass (with 1 skipped):
```
tests/unit/test_rag.py ..s.......                                        [100%]
========================= 9 passed, 1 skipped in 0.01s =========================
```

### Ingestion and Search Speeds (Stress Test: 1000 docs, 100 searches)
I ran a custom stress-test to profile execution speeds:
*   **MockVectorStore Ingestion**: `0.0013 seconds`
*   **ChromaVectorStore Ingestion**: `23.7743 seconds`
*   **MockVectorStore Search (100 runs)**: `0.0335 seconds` (avg `0.34 ms/search`)
*   **ChromaVectorStore Search (100 runs)**: `10.2090 seconds` (avg `102.09 ms/search`)

---

## 2. Logic Chain

1.  **Observation 1**: During `ChromaVectorStore.add_documents()`, metadata values under keys `make`, `model`, `engine`, and `drive_type` are case-normalized to uppercase. E.g., `make: ["Honda", "Ford"]` is saved as `"HONDA,FORD"`.
2.  **Observation 2**: In `tests/unit/test_rag.py` line 271, the test queries the Chroma store directly using:
    `chroma_store.search("brake", filter_metadata={"make": ["Honda", "Ford"], "model": "Accord"})`
3.  **Observation 3**: In `backend/rag/vector_store.py` lines 152–159, `ChromaVectorStore.search` converts lists into comma-separated strings but **does not perform case-normalization (uppercasing)**. Thus, `["Honda", "Ford"]` is converted to `"Honda,Ford"`.
4.  **Observation 4**: ChromaDB uses case-sensitive matching for `$eq` filters. Since the query filter is `"Honda,Ford"` and the stored document metadata value is `"HONDA,FORD"`, they do not match, returning 0 results.
5.  **Observation 5**: In contrast, `MockVectorStore.search` uses a case-insensitive check (`str(doc_val).lower() != str(val).lower()`), which is why the Mock store portion of `test_list_type_metadata_filtering` passes.
6.  **Conclusion**: The failing test is caused by an inconsistency between the case-insensitive/case-normalized storage logic and the case-sensitive search logic in `ChromaVectorStore.search` when invoked directly with mixed-case filter metadata.

---

## 3. Caveats

*   This failure only occurs when `chromadb` is installed and the test suite executes the Chroma-specific path of `test_list_type_metadata_filtering`.
*   If queries are executed via `retrieve(...)`, the `retrieve` wrapper performs uppercase normalization of metadata before passing it to `search(...)`, which masks this issue during normal application flows.
*   No write concurrency stress-testing was done (e.g. concurrent additions to the store).

---

## 4. Conclusion

The test suite does **not** pass fully when `chromadb` is installed. Out of 10 tests, 9 pass and 1 fails (`test_list_type_metadata_filtering`).
The root cause is that `ChromaVectorStore.search()` lacks case-normalization on vehicle metadata filtering keys, making direct queries case-sensitive and mismatched against uppercase-normalized stored metadata.

Recommended Action: Modify `ChromaVectorStore.search()` to uppercase the query filter values for metadata keys in `("make", "model", "engine", "drive_type")` prior to constructing the Chroma `$eq` where clause.

---

## 5. Verification Method

To reproduce the failure:
1.  Ensure `chromadb` is installed in the active environment:
    ```bash
    .venv/bin/pip install chromadb
    ```
2.  Run the unit test suite:
    ```bash
    PATH="/Users/prathambansal/Dev/RAPP/.venv/bin:$PATH" PYTHONPATH=. pytest tests/unit/test_rag.py
    ```
3.  Observe that `test_list_type_metadata_filtering` fails on line 272.
