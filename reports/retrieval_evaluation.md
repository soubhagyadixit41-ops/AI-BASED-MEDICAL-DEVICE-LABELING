# LabelAI — Retrieval & Evaluation Report (Phase 2)

**Evaluation Date:** 2026-10-13  
**Evaluation Set:** 50 records (42 answerable, 8 unanswerable)  
**Corpus Size:** 92 chunks across 6 indexed sources  

---

## 1. Metric Comparison: Baseline vs. Phase 2 Expanded

| Metric | Phase 1 Baseline | Phase 2 (Expanded Corpus) | Change / Notes |
|---|---|---|---|
| Evaluation Dataset Size | 34 questions | **50 questions** | +16 questions (+47%) covering FDA, paraphrases, and cross-jurisdiction |
| Answerable Questions | 27 | **42** | +15 answerable questions |
| Unanswerable Questions | 7 | **8** | Preserved unanswerable set with verified corpus grounding |
| Indexed Sources | 2 | **6** | +4 FDA official sources recovered |
| Total Corpus Chunks | 64 | **92** | +28 chunks |
| Retrieval Recall@5 | 1.000 | **1.000 (42/42)** | 100% of answerable questions retrieve expected source in top 5 |
| Retrieval MRR | 0.963 | **0.976** | Increased due to exact regulatory clause and section boosting |
| Key-Fact Hit Rate | 1.000 | **1.000 (42/42)** | 100% of top-5 passages contain expected factual substrings |
| Citation Metadata Correctness | 1.000 | **1.000 (42/42)** | 100% of retrieved chunks carry valid URLs and official titles |
| Abstention Accuracy | 1.000 | **1.000 (8/8)** | All 8 unanswerable questions trigger clean insufficient-evidence responses |
| Total Passing Tests | 26 | **37** | +11 regression & pipeline tests |

---

## 2. Retrieval Engineering Improvements

### 2.1 Exact Regulatory Clause and Section Boosting
Generic TF-IDF tokenizers split numbers with periods (e.g., `801.1` becomes tokens `801` and `1`), causing specific clause references like `21 CFR 801.1` to be overshadowed by generic chunks containing `21 CFR 801.405`.
- **Implementation:** Added regex detection for regulatory clause patterns (`[0-9]+\.[0-9]+(?:\.[0-9]+)?`, `21 cfr [0-9]+(?:\.[0-9]+)?`). Chunks containing exact clause matches receive a +0.35 score boost.
- **Result:** Queries such as `"What does 21 CFR 801.1 require?"` and `"What does IMDRF Section 5.2.9 say?"` rank their exact regulatory sections at Rank 1.

### 2.2 Jurisdiction Alignment and Cross-Jurisdiction Non-Conflation
To enforce the principle *"Do not use one jurisdiction's evidence as proof of another jurisdiction's requirement"*:
- When questions explicitly target a specific jurisdiction (e.g., FDA/US or IMDRF/International), chunks from matching jurisdictions receive an alignment boost, while mismatched chunks are down-weighted.
- In `deterministic_answer`, questions specifically asking about FDA requirements require at least one United States source in the evidence set; foreign or international requirements are never presented as US regulations.

### 2.3 Distinctive Term Topic Validation
Prevents false-positive evidence output when a query contains specific domain entities unsupported by the corpus (e.g., asking FDA about EUDAMED, or asking about cardiac stent clinical protocols):
- Substantive query terms (nouns and distinctive terminology minus domain stopwords) are checked against the retrieved chunks.
- If zero distinctive query terms exist in the retrieved text, the answer pipeline abstains (`Insufficient evidence in the indexed sources.`) rather than returning misleading generic labeling text.

---

## 3. Evaluation Breakdown by Question Category

| Category | Questions | Recall@5 | Key-Fact Hit | Notes |
|---|---|---|---|---|
| **IMDRF General Principles** | Q001–Q021 | 100% | 100% | International labeling principles, definitions, format, symbols |
| **EC EUDAMED / UDI** | Q022–Q026 | 100% | 100% | European Commission UDI timelines, EMDN, legacy device rules |
| **Cross-Jurisdiction Comparison** | Q027, Q047, Q049 | 100% | 100% | UDI concept alignment, IMDRF vs FDA scope separation |
| **FDA General Labeling (21 CFR 801)** | Q030, Q035–Q038, Q045 | 100% | 100% | General provisions, name & address (801.1), directions (801.5), prominence (801.15), Puerto Rico exemptions |
| **FDA QSR Labeling (21 CFR 820)** | Q039–Q042 | 100% | 100% | Quality system labeling controls, integrity, changes, sterile labeling |
| **FDA UDI Guidance** | Q043 | 100% | 100% | 21 CFR 801.40 UDI scope and issuing agencies |
| **Paraphrased / Synonym Queries** | Q044, Q045, Q046 | 100% | 100% | Tested robustness against non-canonical query phrasing |
| **Unanswerable / Out of Corpus** | Q028, Q029, Q031, Q032, Q033, Q034, Q048, Q050 | N/A (Abstain) | N/A (Abstain) | 100% abstention: ISO standards, missing EUR-Lex, India, compliance certification, cardiac stent clinical trials |

---

## 4. Integrity and Metric Limitations Notice

- **Closed-Corpus Evaluation:** High metrics reflect targeted evaluation queries checked against a deterministic index. They do not constitute an autonomous regulatory compliance certificate.
- **No LLM Hallucinations:** The deterministic answer pipeline only outputs quotes from indexed chunks with traceable URLs and section numbers.
- **Qualified Human Review Required:** As stated in the application banner and output headers, all retrieved evidence must be evaluated by qualified regulatory affairs professionals.
