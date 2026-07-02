## Challenge Summary

**Overall risk assessment**: HIGH

Through empirical stress-testing of the backend server endpoints, we discovered four distinct issues (two Critical crashes, one Medium crash, and one Medium parameter drop). Specifically, if a client requests diagnosis or repair without specifying the `obd_codes` field, or if the RAG retriever returns documents with null metadata, the server crashes with HTTP 500. Additionally, Stripe checkout redirect drops query parameters that are not explicitly captured as route params.

---

## Challenges

### [Critical] Challenge 1: Missing `obd_codes` in `/api/repair` payload crashes the server

- **Assumption challenged**: Pydantic v2 field validators run on missing payload keys that default to `None`.
- **Attack scenario**: A client POSTs to `/api/repair` without including `"obd_codes"` in the JSON payload.
- **Blast radius**: The validator is bypassed, leaving `request.obd_codes = None`. When the route handler attempts `" ".join(request.obd_codes)`, it crashes with `TypeError: can only join an iterable`, leaking a 500 Internal Server Error to the client.
- **Mitigation**: Update the field validator in `RepairRequest` to use `validate_default=True`, or change the default value of the field to `Field(default_factory=list)`. Alternatively, use `request.obd_codes or []` in the query construction.

### [Critical] Challenge 2: Missing `obd_codes` in `/api/diagnose` payload crashes the server

- **Assumption challenged**: Same as Challenge 1.
- **Attack scenario**: A client POSTs to `/api/diagnose` without including `"obd_codes"` in the JSON payload.
- **Blast radius**: The validator is bypassed, leaving `request.obd_codes = None`. When `check_high_risk` attempts `" ".join(obd_codes)`, it crashes with `TypeError: can only join an iterable`, leaking a 500 Internal Server Error to the client.
- **Mitigation**: Add `validate_default=True` to the validator, use `Field(default_factory=list)`, or safe-guard `check_high_risk` to handle `None` inputs.

### [High] Challenge 3: Explicitly `None` metadata key in RAG output crashes the server

- **Assumption challenged**: Assumed `doc.get("metadata", {})` always returns a dictionary.
- **Attack scenario**: The vector store returns a document where the key `"metadata"` is explicitly mapped to `None` (a common behavior in database libraries when metadata is null).
- **Blast radius**: `doc.get("metadata", {})` evaluates to `None` because the key exists. When the route handler later executes `meta.get("citation")`, it throws `AttributeError: 'NoneType' object has no attribute 'get'`.
- **Mitigation**: Use `meta = doc.get("metadata") or {}` instead of `doc.get("metadata", {})`.

### [Medium] Challenge 4: success-stub redirect drops all non-standard query parameters

- **Assumption challenged**: Only `session_id` and `vin` need to be preserved in the redirect URL.
- **Attack scenario**: The frontend or Stripe session adds promotional codes, referral tracking parameters, or callback parameters to `/api/payments/success-stub`.
- **Blast radius**: All query parameters other than `session_id` and `vin` are dropped, which breaks tracking or extra features on the success landing page.
- **Mitigation**: Inject the FastAPI `Request` object into the endpoint and dynamically forward all request query parameters.

---

## Stress Test Results

Our custom adversarial test suite `tests/unit/test_challenge.py` generated the following outcomes:

| Test Case | Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| `test_repair_symptom_only_no_obd_codes` | Missing `obd_codes` in `/api/repair` | Graceful default step fallback (HTTP 200) | `TypeError: can only join an iterable` (HTTP 500) | **FAIL (Bug Confirmed)** |
| `test_diagnose_no_obd_codes` | Missing `obd_codes` in `/api/diagnose` | Free diagnosis summary (HTTP 200) | `TypeError: can only join an iterable` (HTTP 500) | **FAIL (Bug Confirmed)** |
| `test_repair_rag_metadata_none` | Document `"metadata"` key is `None` | Custom citation fallback (HTTP 200) | `AttributeError: 'NoneType' object has no attribute 'get'` (HTTP 500) | **FAIL (Bug Confirmed)** |
| `test_success_stub_redirect_retains_all_query_params` | Extra query params on success-stub | All query parameters preserved | Only `session_id` and `vin` preserved | **FAIL (Bug Confirmed)** |
| `test_repair_rag_returns_none` | RAG returns `None` | Falls back to default steps (HTTP 200) | Falls back to default steps (HTTP 200) | **PASS** |
| `test_repair_rag_returns_empty_list` | RAG returns `[]` | Falls back to default steps (HTTP 200) | Falls back to default steps (HTTP 200) | **PASS** |
| `test_repair_rag_missing_metadata_key` | `"metadata"` key omitted | Default VIN citation (HTTP 200) | Default VIN citation (HTTP 200) | **PASS** |
| `test_success_stub_redirect_status_code` | Redirect status check | Redirects using 303 or 307 | Redirects using 303 | **PASS** |
| `test_webhook_valid_payload` | Valid webhook JSON body | Returns 200 OK | Returns 200 OK | **PASS** |
| `test_webhook_empty_payload` | Empty webhook body | Returns 200 OK | Returns 200 OK | **PASS** |
| `test_webhook_malformed_json` | Malformed webhook JSON body | Returns 200/400 (no crash) | Returns 200 OK (no crash) | **PASS** |

---

## Unchallenged Areas

- **Stripe Session Verification/Checkout Creation** — Not challenged beyond mock endpoint because Stripe API calls are stubbed in the local settings and live sandbox accounts are out of scope.
- **NHTSA API Communication Failures** — Partially covered by standard unit tests, but real rate limiting/throttling not challenged as external communication is disabled in CODE_ONLY mode.
