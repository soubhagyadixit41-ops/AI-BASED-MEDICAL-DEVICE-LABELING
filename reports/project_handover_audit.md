# LabelAI — Project Handover Audit

**Audit performed:** 2026-10-13  
**Auditor:** Handover agent (continuation)

---

## 1. Project Structure Discovered

```
lable AI/
├── .env.example                    # Optional LLM / retrieval config
├── .venv/                          # Python 3.11.0rc2 virtual environment (PRESENT)
├── app.py                          # Streamlit frontend (314 lines)
├── data/
│   ├── change_impact/
│   │   ├── demo_output.json        # Pre-generated demo output
│   │   ├── demo_output_live.json   # Live-generated output (created this session)
│   │   └── sample_change_request.json
│   ├── evaluation/
│   │   └── rag_eval.jsonl          # 34-record evaluation dataset
│   ├── processed/
│   │   ├── regulatory_chunks.jsonl # Indexed corpus (107 KB)
│   │   └── tfidf_index.joblib      # Serialized TF-IDF index (489 KB)
│   └── sources/
│       ├── raw/                    # Downloaded source files
│       └── source_manifest.json   # 7-record source manifest
├── labelai_rag/
│   ├── __init__.py
│   ├── answer.py                   # Deterministic answer + abstention logic
│   ├── change_impact.py            # Change-impact rules + assessment engine
│   ├── cli.py                      # CLI entrypoint (discover/ingest/build-index/...)
│   ├── eval_dataset.py             # Eval dataset builder
│   ├── evaluation.py               # Evaluation runner
│   ├── ingest.py                   # PDF/HTML ingestion and chunking
│   ├── io.py                       # JSON / JSONL read-write helpers
│   ├── models.py                   # Dataclasses: SourceRecord, Chunk, RetrievalResult, EvaluationRecord
│   ├── paths.py                    # Centralised path constants
│   ├── retrieval.py                # LocalTfidfRetriever (load/save/search)
│   ├── sources.py                  # Source discovery and download
│   └── streamlit_service.py        # Service adapter between backend and frontend
├── reports/
│   ├── change_impact_demo.md
│   ├── evaluation_report.json
│   ├── project_handover_audit.md   # This file
│   ├── rag_audit.md
│   └── test_results_summary.md
├── requirements.txt                # 6 dependencies
└── tests/
    ├── test_change_impact.py       # 8 tests
    ├── test_pipeline.py            # 8 tests
    └── test_streamlit_service.py   # 10 tests
```

---

## 2. Current Architecture

```
[User / CLI]
     |
     +-- CLI (labelai_rag/cli.py)
     |     +-- discover   --> sources.py        --> source_manifest.json
     |     +-- ingest     --> ingest.py         --> regulatory_chunks.jsonl
     |     +-- build-index--> retrieval.py      --> tfidf_index.joblib
     |     +-- make-eval  --> eval_dataset.py   --> rag_eval.jsonl
     |     +-- evaluate   --> evaluation.py     --> evaluation_report.json
     |     +-- ask        --> answer.py         --> deterministic answer
     |     +-- impact     --> change_impact.py  --> JSON assessment
     |
     +-- Streamlit UI (app.py)
           +-- streamlit_service.py (adapter)
                 +-- runtime_summary()
                 +-- build_change_request()
                 +-- run_change_impact()  --> change_impact.py
                 +-- ask_regulatory_question() --> answer.py + retrieval.py
                 +-- load_manifest() / load_chunks() / load_eval_records()
```

Retrieval: Local TF-IDF (scikit-learn), no external API calls required.
LLM: Optional via OPENAI_API_KEY; all paths tested without it (deterministic mode).

---

## 3. What Is Implemented

| Component | Status |
|-----------|--------|
| Source discovery + manifest | COMPLETE |
| PDF/HTML ingestion and chunking | COMPLETE |
| TF-IDF index build and load | COMPLETE |
| Eval dataset (34 records) | COMPLETE |
| Evaluation runner | COMPLETE |
| Deterministic answer + abstention | COMPLETE |
| Change-impact engine with evidence_state | COMPLETE |
| CLI (all subcommands) | COMPLETE |
| Streamlit service adapter | COMPLETE |
| Streamlit frontend (4 tabs) | COMPLETE |
| All tests (26 tests) | ALL PASS |

### Change-impact evidence states (verified)
The assess_change_impact function correctly produces:
- evidence_supported: matched rule + retrieved evidence + no market limitations
- potentially_relevant: matched rule + retrieved evidence + market limitations (e.g., US with no FDA source)
- evidence_gap: matched rule + no retrieved evidence above threshold

---

## 4. What Is Missing / Known Gaps

| Item | Status |
|------|--------|
| FDA sources (general labeling, UDI PDF) | FAILED - 404 from FDA bot-protection redirect |
| EUR-Lex EU MDR PDF | FAILED - empty response (0 bytes) |
| ISO 20417:2026 full text | METADATA ONLY - copyrighted/paywalled |
| ISO 15223-1:2021 full text | METADATA ONLY - copyrighted/paywalled |
| LLM-powered answer quality | OPTIONAL - not claimed |
| Browser-level UI verification | NOT PERFORMED - browser automation unavailable |

---

## 5. Verified Source Manifest (7 records)

| source_id | access_status | indexed |
|-----------|--------------|---------|
| fda_general_device_labeling | download_failed | NO |
| eu_mdr_2017_745_consolidated_2023_03_20 | download_failed | NO |
| imdrf_grrp_wg_n52_2024 | downloaded_public_pdf | YES |
| ec_udi_device_registration | downloaded_public_html | YES |
| fda_udi_form_content_guidance_2021 | download_failed | NO |
| iso_20417_2026 | metadata_only_full_standard_not_publicly_downloaded | NO |
| iso_15223_1_2021 | metadata_only_full_standard_not_publicly_downloaded | NO |

Indexed source IDs: ec_udi_device_registration, imdrf_grrp_wg_n52_2024

---

## 6. Existing Test Status (Baseline confirmed this session)

```
26 passed in 3.67s   [Python 3.11.0rc2, pytest 9.1.1]
```

All 26 tests pass without modification. No tests were weakened.

| Test file | Tests | Status |
|-----------|-------|--------|
| test_change_impact.py | 8 | All pass |
| test_pipeline.py | 8 | All pass |
| test_streamlit_service.py | 10 | All pass |

---

## 7. RAG Evaluation Metrics (from saved report)

| Metric | Value | Definition |
|--------|-------|------------|
| Evaluation set size | 34 | 27 answerable, 7 unanswerable |
| Recall@5 | 1.000 | Expected source ID appears in top-5 retrieved chunks |
| MRR | 0.963 | Mean reciprocal rank |
| Key-fact hit rate | 1.000 | Expected key-fact substring in retrieved text |
| Citation metadata correctness | 1.000 | Retrieved chunks have title and URL |
| Abstention accuracy | 1.000 | Unanswerable questions produce ABSTAIN response |

Known limitations:
- Metrics use substring matching and metadata presence, not semantic correctness
- Corpus limited to 2 indexed sources; scores reflect closed-set retrieval
- No LLM evaluation; deterministic only
- Perfect scores reflect corpus design alignment with questions, not regulatory completeness

---

## 8. Streamlit Application Status

- Version: Streamlit 1.65.0
- Smoke test: HTTP GET http://localhost:8506 - 200 OK (PASS)
- Healthz: HTTP GET http://localhost:8506/healthz - 200 OK (PASS)
- Browser-level verification: Not performed (browser automation unavailable)
- Import errors on startup: None
- 4 tabs implemented: Overview, Change Impact Analysis, Regulatory Q&A, Evidence & Evaluation

---

## 9. Remaining Work / Outstanding Items

1. FDA/EUR-Lex source access: FDA uses bot-protection; EU MDR PDF returns empty. No programmatic workaround available within public access constraints.
2. Browser-level UI testing: Not automatable in this environment; manual verification recommended.
3. LLM integration: Placeholder architecture exists but requires a paid API key to activate.
4. ISO standards: Full text cannot be indexed without a paid licence.

---

## 10. Integrity Statement

This audit was performed by directly inspecting all files, running all tests, executing the CLI, and starting the Streamlit server. No claimed results were accepted without verification. No tests were removed or weakened.
