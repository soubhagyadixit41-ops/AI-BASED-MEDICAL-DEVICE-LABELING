# LabelAI — End-to-End Validation Report

**Validation date:** 2026-10-13  
**Python:** 3.11.0rc2  
**Streamlit:** 1.65.0  
**pytest:** 9.1.1

---

## 1. Backend Validation

### 1.1 Test Suite

Command run:
```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests/ -v
```

Result:
```
============================= test session starts =============================
platform win32 -- Python 3.11.0rc2, pytest-9.1.1, pluggy-1.6.0
collected 26 items

tests/test_change_impact.py::test_change_with_relevant_evidence_in_corpus PASSED
tests/test_change_impact.py::test_change_with_incomplete_evidence_marks_missing_information PASSED
tests/test_change_impact.py::test_unsupported_market_or_regulatory_question_is_limited PASSED
tests/test_change_impact.py::test_address_change_does_not_trigger_unrelated_label_elements PASSED
tests/test_change_impact.py::test_missing_product_context_fails_safely PASSED
tests/test_change_impact.py::test_invalid_input_fails_safely PASSED
tests/test_change_impact.py::test_evidence_and_citation_provenance PASSED
tests/test_change_impact.py::test_human_review_flags_are_preserved PASSED
tests/test_pipeline.py::test_manifest_records_official_sources_and_iso_limitations PASSED
tests/test_pipeline.py::test_chunks_have_real_provenance PASSED
tests/test_pipeline.py::test_expected_sources_retrieved_for_answerable_questions PASSED
tests/test_pipeline.py::test_retrieved_passages_contain_expected_evidence PASSED
tests/test_pipeline.py::test_citations_point_to_real_metadata PASSED
tests/test_pipeline.py::test_unanswerable_questions_trigger_abstention PASSED
tests/test_pipeline.py::test_empty_question_fails_safely PASSED
tests/test_pipeline.py::test_index_exists PASSED
tests/test_streamlit_service.py::test_runtime_summary_uses_current_artifacts PASSED
tests/test_streamlit_service.py::test_successful_change_impact_invocation_from_service PASSED
tests/test_streamlit_service.py::test_service_missing_or_invalid_change_fields PASSED
tests/test_streamlit_service.py::test_empty_evidence_result_for_unmatched_change PASSED
tests/test_streamlit_service.py::test_unsupported_target_market_disclosure PASSED
tests/test_streamlit_service.py::test_source_references_are_preserved PASSED
tests/test_streamlit_service.py::test_json_serialization_of_assessment_results PASSED
tests/test_streamlit_service.py::test_insufficient_evidence_behavior_in_qa PASSED
tests/test_streamlit_service.py::test_live_assessment_is_not_sample_fixture PASSED
tests/test_streamlit_service.py::test_missing_optional_api_credentials_do_not_block_deterministic_paths PASSED

26 passed in 3.67s
```

**Result: 26/26 PASS**

---

### 1.2 CLI Change-Impact Demo

Command run:
```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli impact data/change_impact/sample_change_request.json --output data/change_impact/demo_output_live.json
```

Input: Fictional cardiac stent with manufacturer address change, US market.

Key output fields verified:
- `change_id`: DEMO-CHANGE-001
- `affected_label_elements`: manufacturer name/address (review_required)
- `evidence_state`: potentially_relevant (correct — IMDRF evidence found but FDA sources missing)
- `evidence_refs`: [EV001, EV002]
- `supporting_evidence[0].source_id`: imdrf_grrp_wg_n52_2024
- `supporting_evidence[0].url`: https://www.imdrf.org/... (starts with https)
- `supporting_evidence[0].page`: 19 (real page number from PDF)
- `human_review_required`: true
- `missing_information` includes: "new manufacturer address", "effective date of address change", "US market requested, but FDA sources are not currently indexed"
- `source_coverage_limitations` includes US market limitation disclosure

**Result: PASS — assessment produced, serializable to JSON, provenance resolves to real indexed sources**

---

### 1.3 Scenario Coverage

| Scenario | Test Method | Result |
|----------|-------------|--------|
| Fictional cardiac-stent manufacturer address change | CLI + service test | PASS |
| Unsupported market (India) | test_unsupported_target_market_disclosure | PASS — India disclosed in limitations |
| US market with no FDA source | Live demo + test_unsupported_market_or_regulatory_question_is_limited | PASS — potentially_relevant state |
| Change with no matched rule (no impact) | test_empty_evidence_result_for_unmatched_change | PASS — manual triage message |
| Incomplete/invalid input | test_invalid_input_fails_safely + test_missing_product_context_fails_safely | PASS — ValueError raised |
| Address change does not affect unrelated elements | test_address_change_does_not_trigger_unrelated_label_elements | PASS — only manufacturer name/address affected |
| FDA question triggers abstention | test_insufficient_evidence_behavior_in_qa | PASS — ABSTAIN returned |
| JSON serialization | test_json_serialization_of_assessment_results | PASS |
| Provenance preservation | test_evidence_and_citation_provenance | PASS — EV-prefixed IDs, real URLs |
| No LLM API key | test_missing_optional_api_credentials_do_not_block_deterministic_paths | PASS |

---

### 1.4 RAG Evaluation

Saved evaluation report metrics (from reports/evaluation_report.json):

| Metric | Value |
|--------|-------|
| Evaluation set size | 34 (27 answerable, 7 unanswerable) |
| Recall@5 | 1.000 |
| MRR | 0.963 |
| Key-fact hit rate | 1.000 |
| Citation metadata correctness | 1.000 |
| Abstention accuracy | 1.000 |

Limitations acknowledged:
- Metrics use substring and metadata presence checks only
- Corpus covers only 2 sources; scores reflect closed-set design
- No semantic or LLM answer quality claimed

---

## 2. Streamlit Application

### 2.1 Startup

Command:
```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run app.py --server.headless true --server.port 8506
```

Startup log (confirmed):
```
Uvicorn server started on :::8506
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8506
```

No import errors observed.

### 2.2 HTTP Smoke Test

| Endpoint | Status | Result |
|----------|--------|--------|
| http://localhost:8506 | 200 OK | PASS |
| http://localhost:8506/healthz | 200 OK | PASS |

### 2.3 Browser-Level Verification

Browser automation is not available in this environment. HTTP 200 status confirms the server started without errors and responds to requests. Tab-level and interactive verification requires a browser.

### 2.4 Tabs Implemented

| Tab | Status |
|-----|--------|
| Overview — runtime metrics, workflow, source gaps | Implemented |
| Change Impact Analysis — form, live backend call, evidence display | Implemented |
| Regulatory Q&A — question input, live RAG retrieval, evidence excerpts | Implemented |
| Evidence & Evaluation — manifest, eval metrics with definitions | Implemented |

---

## 3. CLI Compatibility

| Subcommand | Status |
|------------|--------|
| discover | Works (downloads available sources) |
| ingest | Works (chunks ingested from downloaded sources) |
| build-index | Works (TF-IDF index built and saved) |
| make-eval | Works (eval dataset generated) |
| evaluate | Works (report written to reports/) |
| ask | Works (deterministic answer returned) |
| impact | Works (JSON assessment written to file) |
| all | Works (runs entire pipeline) |

---

## 4. Backend Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Existing tests pass | PASS (26/26) |
| Sample request runs through change-impact | PASS |
| Assessment serializable to JSON | PASS |
| Provenance fields resolve to real indexed sources | PASS |
| Missing source coverage disclosed | PASS |
| Human review required | PASS |
| CLI continues to work | PASS |
| No tests weakened or removed | CONFIRMED |

---

## 5. Checks That Could Not Be Completed

1. **Browser-level UI verification** — No browser automation available. HTTP 200 confirmed only.
2. **Real regulatory accuracy** — This tool is informational only; no ground-truth regulatory correctness claimed or verifiable without regulatory expert review.
3. **FDA/EUR-Lex source indexing** — Downloads fail due to server-side restrictions outside our control.
