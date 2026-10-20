# LabelAI — Regulatory Labeling Intelligence Prototype

> **Illustrative prototype only.** Outputs require qualified regulatory review and do not constitute a regulatory compliance determination.

LabelAI is an intelligent medical-device labeling automation platform developed for the Tata Elxsi TELIPORT Season 4 case study. It demonstrates **change-aware, evidence-linked labeling intelligence**: product changes are mapped to potentially affected label elements, linked to retrieved regulatory evidence, and routed for qualified human review.

---

## Setup

### 1. Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

Dependencies: `beautifulsoup4`, `PyMuPDF`, `pytest`, `requests`, `scikit-learn`, `streamlit`

### 3. Optional: LLM configuration

Copy `.env.example` to `.env` and set your keys. All retrieval and change-impact paths work without an LLM key (deterministic mode).

```powershell
Copy-Item .env.example .env
```

---

## Launch the Streamlit Application

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run app.py --server.port 8506
```

Open `http://localhost:8506` in your browser.

The application has four tabs:
- **Overview** — runtime metrics (92 chunks, 6 indexed sources), workflow, source coverage
- **Change Impact Analysis** — submit a change request and inspect evidence-linked assessment
- **Regulatory Q&A** — ask a question and inspect retrieved source passages
- **Evidence & Evaluation** — source manifest, evaluation metrics (50 questions), and definitions

---

## Run Tests

```powershell
& ".\.venv\Scripts\python.exe" -m pytest -q
```

Expected: `47 passed in ~7s`

Run verbose:
```powershell
& ".\.venv\Scripts\python.exe" -m pytest -v
```

The test suite covers:
- Ingestion, chunking, and source provenance (19 tests)
- Local TF-IDF jurisdiction-aware retrieval and abstention (tests in pipeline)
- Streamlit service layer, runtime summaries, and serialization (10 tests)
- Generalized change-impact analysis across 10 novel change categories, input validation, and element isolation (18 tests)


---

## Rebuild the Corpus

Run all pipeline steps:

```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli all
```

Or individually:

```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli discover
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli ingest
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli build-index
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli make-eval
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli evaluate
```

---

## Run RAG Evaluation

```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli evaluate
```

Output is written to `reports/evaluation_report.json` and `reports/test_results_summary.md`.

Current results across 50 evaluation questions:
- Recall@5: 1.000 (42/42 answerable)
- MRR: 0.976
- Key-Fact Hit Rate: 1.000 (42/42)
- Citation Metadata Correctness: 1.000
- Abstention Accuracy: 1.000 (8/8 unanswerable)

---

## Ask a Retrieval-Grounded Question (CLI)

```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli ask "What does IMDRF say about manufacturer address on the label?"
```

Ask an FDA-specific question:
```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli ask "What does 21 CFR 801.1 require for manufacturer name and address?"
```

Without an LLM key, answers are deterministic retrieval-only summaries with citations. If no retrieved passage supports the question, the answer is:

```
Insufficient evidence in the indexed sources.
```

---

## Generalized Change-Impact Analysis (CLI & Backend)

LabelAI supports 10 standardized regulatory change categories (Manufacturer info, Intended purpose, Device specs, Materials/composition, Warning/precaution, Sterilization/shelf life, UDI/identifier, Packaging, Translation, Other/unknown) and evaluates novel free-text changes using a multi-stage, jurisdiction-aware evidence pipeline.

Run the illustrative demo scenarios:

1. **Manufacturer Address Relocation:**
```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli impact data/change_impact/sample_change_request.json
```
Triggers `manufacturer name/address` under 21 CFR 801.1 and isolates unrelated elements.

2. **UDI & Device Identifier Change:**
```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli impact data/change_impact/change_request_udi.json
```
Triggers `UDI` and `device identifier` under FDA UDI guidance and 21 CFR 801.40.

3. **Clinical Warning & Sterilization Precaution Change:**
```powershell
& ".\.venv\Scripts\python.exe" -m labelai_rag.cli impact data/change_impact/change_request_warning.json
```
Triggers `warnings` and `instructions for use` under 21 CFR 801.405–437 and flags `evidence_gap` for proprietary symbol standards.

Assessments are saved directly alongside inputs (e.g. `*_impact_assessment.json`).
To download assessments as JSON from the Streamlit UI, submit the form in the **Change Impact Analysis** tab and click **Download live assessment JSON**.

---

## Source Inventory & Coverage

**Indexed Sources (6 sources, 92 chunks):**
1. `fda_general_device_labeling` — 21 CFR Part 801 General Provisions, Name & Place of Business (801.1), Directions (801.5), Prominence (801.15), Puerto Rico exemptions
2. `fda_qsr_labeling` — 21 CFR Part 820 Quality System Regulation Labeling Requirements (Label control, integrity, change review, sterile labeling)
3. `fda_specific_device_labeling` — 21 CFR 801.405–437 Requirements for Specific Devices
4. `fda_udi_guidance` — FDA UDI guidance regarding 21 CFR 801.40
5. `imdrf_grrp_wg_n52_2024` — IMDRF GRRP WG/N52 FINAL:2024 (Edition 2) international labeling principles
6. `ec_udi_device_registration` — European Commission UDI/Device Registration & EMDN nomenclature

**Unindexed Sources & Gaps (4 sources):**
1. `eu_mdr_2017_745_consolidated_2023_03_20` — EUR-Lex endpoint returned HTTP 202 with 0 bytes (async render)
2. `fda_udi_form_content_guidance_2021` — Direct PDF media link redirected to abuse detection page (HTML guidance indexed instead)
3. `iso_20417_2026` — Copyrighted/paywalled ISO standard (metadata only)
4. `iso_15223_1_2021` — Copyrighted/paywalled ISO standard (metadata only)

All source access decisions are recorded in `data/sources/source_manifest.json`.

---

## Known Implementation Limitations

1. **Deterministic Retrieval:** Local TF-IDF with exact-clause pattern boosting and jurisdiction alignment. No paid vector database or LLM is mandatory.
2. **ISO 15223-1 Symbols:** Full standard text cannot be indexed without a commercial license. Symbol queries correctly trigger `evidence_gap`.
3. **No Autonomous Certification:** The system does not certify regulatory compliance; outputs require human review.

---

## Delivered Artefacts

- `data/sources/source_manifest.json` — 10 source records with verified access status
- `data/sources/raw/` — Downloaded official sources
- `data/processed/regulatory_chunks.jsonl` — 92 indexed chunks with provenance
- `data/processed/tfidf_index.joblib` — Serialized TF-IDF retrieval index
- `data/evaluation/rag_eval.jsonl` — 50 evaluation records
- `data/change_impact/` — Sample and novel change requests and impact assessments
- `reports/change_impact_evaluation.md` — Generalized change-impact architecture and evaluation report
- `reports/regulatory_data_coverage.md` — Source recovery and data coverage audit
- `reports/retrieval_evaluation.md` — Evaluation metrics and retrieval improvements
- `reports/streamlit_demo.md` — Streamlit demonstration and UI verification report
- `reports/evaluation_report.json` — Evaluation results (100% Recall@5, 100% key-fact hit rate, 100% abstention)
- `reports/test_results_summary.md` — Test results summary (47 passing automated tests)

