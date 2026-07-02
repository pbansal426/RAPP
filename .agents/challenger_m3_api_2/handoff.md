# Handoff Report — Challenger M3 API 2

## 1. Observation
We created a custom test file `/Users/prathambansal/Dev/RAPP/tests/unit/test_challenge.py` and ran it using:
```bash
PYTHONPATH=tests/unit:. .venv/bin/pytest tests/unit/test_challenge.py
```
This command produced the following failures:

### Failure A: Missing `obd_codes` field in `/api/repair` JSON payload
Verbatim trace:
```
request = RepairRequest(vin='1HGBH41JXMN109186', symptoms='spark plug replacement', obd_codes=[], tools=None, stripe_session_id='cs_test_123')
...
    query = f"{request.symptoms} " + " ".join(request.obd_codes)
E   TypeError: can only join an iterable
```
(Note: in this case, `obd_codes` defaulted to `None` in the Pydantic model representation due to lack of `validate_default=True`).

### Failure B: Missing `obd_codes` field in `/api/diagnose` JSON payload
Verbatim trace:
```
    is_high_risk, high_risk_system, warning_message = check_high_risk(
        request.symptoms, request.obd_codes
    )
...
    combined = (symptoms + " " + " ".join(obd_codes)).lower()
E   TypeError: can only join an iterable
```

### Failure C: Explicitly `None` metadata key returned by RAG store
Verbatim trace:
```
            for doc in results:
                meta = doc.get("metadata", {})
>               citation = meta.get("citation") or meta.get("source")
E               AttributeError: 'NoneType' object has no attribute 'get'
```

### Failure D: success-stub drops query parameters
Verbatim trace:
```
    def test_success_stub_redirect_retains_all_query_params(client):
        response = client.get("/api/payments/success-stub?session_id=cs_test_123&vin=1HGBH41JXMN109186&promo=SAVE10&referrer=google", follow_redirects=False)
        location = response.headers.get("location", "")
>       assert "promo=SAVE10" in location
E       AssertionError: assert 'promo=SAVE10' in 'http://localhost:3000/repair/success?session_id=cs_test_123&vin=1HGBH41JXMN109186'
```

---

## 2. Logic Chain
1. In `backend/main.py`, both `DiagnoseRequest` and `RepairRequest` define `obd_codes` with a default value: `obd_codes: Union[List[str], str, None] = None`.
2. A field validator `normalize_obd_codes` is defined, but Pydantic V2 does not run validators for omitted fields falling back to their defaults unless `validate_default=True` is specified.
3. Therefore, if a client issues a request without the `obd_codes` field, `request.obd_codes` remains `None`.
4. At line 228 (`combined = (symptoms + " " + " ".join(obd_codes)).lower()`) and line 373 (`query = f"{request.symptoms} " + " ".join(request.obd_codes)`), the code calls `" ".join(request.obd_codes)` on `None`, which triggers a `TypeError`. This logic directly leads from the validator omission to the crash.
5. In `backend/main.py:380`, `meta = doc.get("metadata", {})` returns `None` if the `"metadata"` key exists but is mapped to `None`.
6. At line 381, the code calls `meta.get("citation")`. Because `meta` is `None`, this crashes with `AttributeError`. This links null metadata returned from database queries to the repair endpoint crash.
7. In `backend/main.py:412-414`, `success_stub(session_id: str, vin: str)` only expects two query parameters. FastAPI parses these two and ignores all other query strings. The redirect URL is hardcoded as `f"{settings.frontend_url}/repair/success?session_id={session_id}&vin={vin}"`.
8. Any additional query parameters passed by Stripe checkout or marketing tracking are thus silently dropped during redirection.

---

## 3. Caveats
- Since external Stripe checkout API calls and live webhook verification are out of scope (stubbed in local settings), we used mock objects and raw HTTP payloads in the local test client to simulate success responses and malformed payloads.
- We bypassed python virtualenv dependency mismatches (specifically, missing `structlog` packages) by writing a local, non-intrusive mock logging module to `tests/unit/structlog.py` rather than altering dependencies or execution environments.

---

## 4. Conclusion
1. The backend application in `backend/main.py` is vulnerable to server crashes (HTTP 500) under standard edge inputs, specifically when the optional `obd_codes` field is omitted from `/api/repair` or `/api/diagnose` JSON payloads.
2. The `/api/repair` endpoint will crash if the underlying vector store database contains documents with empty/null metadata fields.
3. The Stripe success stub endpoint `/api/payments/success-stub` drops all query parameters except `session_id` and `vin`.
4. The webhook endpoint `/api/payments/webhook` behaves correctly and does not crash when parsing malformed JSON payloads since it does not read the request body.

---

## 5. Verification Method
To independently verify the bugs, run the following command from the root of the project repository:
```bash
PYTHONPATH=tests/unit:. .venv/bin/pytest tests/unit/test_challenge.py
```
This runs the adversarial test suite and will fail on four specific test cases (`test_repair_symptom_only_no_obd_codes`, `test_diagnose_no_obd_codes`, `test_repair_rag_metadata_none`, and `test_success_stub_redirect_retains_all_query_params`), confirming all findings.
