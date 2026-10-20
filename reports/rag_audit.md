# LabelAI RAG Engine Audit

Audit date: 2026-10-13

## Scope

Reviewed:

- `data/sources/source_manifest.json`
- `data/processed/regulatory_chunks.jsonl`
- `data/evaluation/rag_eval.jsonl`
- all files under `labelai_rag/`
- all tests under `tests/`
- `reports/evaluation_report.json`
- `reports/test_results_summary.md`

Commands rerun with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m labelai_rag.cli evaluate
.\.venv\Scripts\python.exe -m pytest -q
```

Observed result:

- Evaluation command completed after write permission was restored.
- Tests: `8 passed in 3.01s` on the first rerun, and later `8 passed in 2.85s` before this audit.
- Indexed chunks: 64.
- Indexed source IDs: `imdrf_grrp_wg_n52_2024`, `ec_udi_device_registration`.
- Evaluation records: 34 total, 27 answerable, 7 unanswerable.

## Confirmed Defects

### 1. Citation correctness metric does not verify citations against cited evidence

`citation_metadata_correctness` is counted as correct when the top retrieved chunks have a non-empty `title` and `url`. It does not verify that the generated answer cites the specific chunk used, that the cited page/section is correct, or that the cited passage supports the answer.

Impact: the reported `1.000` citation correctness score is a metadata-presence score, not citation correctness in the regulatory sense.

### 2. Answer generation can cite weakly related passages

The deterministic answer generator selects sentences from the top retrieved chunks by term overlap. It does not require that the selected sentence entails the answer or that all answer claims are grounded in the cited passage.

Impact: source-supported answer quality is not measured by the current evaluation.

### 3. Abstention accuracy is partly hard-coded to known unavailable terms

`answer.py` abstains when a question contains terms such as `fda`, `iso 15223`, `iso 20417`, `india`, `certify`, or `compliant`. This correctly prevents unsupported answers for the current known gaps, but the metric primarily verifies this guardrail rather than a general evidence sufficiency detector.

Impact: `1.000` abstention accuracy should not be interpreted as robust abstention for arbitrary unsupported questions.

### 4. Key-fact hit rate uses substring matching over all top-k retrieved text

`retrieved_evidence_key_fact_hit_rate` succeeds if any expected key-fact substring appears anywhere in the concatenated top-k passages. It does not require the top-ranked passage to contain the evidence, does not verify complete expected answers, and does not evaluate generated answer content.

Impact: the metric is useful as a retrieval smoke test, but it overstates answer-level accuracy.

### 5. Evaluation dataset is generated from code, not independently maintained

`labelai_rag/eval_dataset.py` programmatically creates `rag_eval.jsonl`. The expected answers and key facts are curated in source code and then evaluated by the same repository. There is no separate reviewer sign-off, source excerpt snapshot, or independent evidence annotation file.

Impact: the evaluation questions are traceable to corpus passages, but they are not independently verified in a strict audit sense.

### 6. Stale failed raw artifact remains in `data/sources/raw/`

`data/sources/raw/eu_mdr_2017_745_consolidated_2023_03_20_6e7646ff_PDF.pdf` exists with size `0`, while the manifest correctly records the EUR-Lex source as `download_failed` with `local_path: null`.

Impact: ingestion correctly skips it, but the raw directory contains a misleading failed artifact.

## Limitations

### Source coverage is narrow

Only two sources are indexed:

- IMDRF GRRP WG/N52 FINAL:2024, Edition 2.
- European Commission UDI/Device registration page.

FDA sources were not indexed because local discovery was redirected to FDA abuse-detection pages. EUR-Lex MDR was not indexed because the local request returned an empty body. ISO standards are correctly marked metadata-only because full standards are copyrighted/paywalled.

### Page and section metadata is approximate

PDF page numbers are real PyMuPDF page indices. Section labels are heuristically inferred from early page lines. This works for many IMDRF chunks but can produce broad or imperfect section labels such as `Page 4` or headings that begin mid-clause.

HTML chunks do not have page numbers. The European Commission page uses headings such as `Page content`, `UDI Helpdesk`, and `European Medical Device Nomenclature (EMDN)`.

### The system mostly retrieves regulatory text; interpretation is minimal

The current answer generator labels output as `Source-supported evidence` and includes a compliance disclaimer. It does not produce much explicit interpretation, which lowers hallucination risk. However, when it does select sentences, it does not explicitly separate source fact, inference, and recommendation.

### Missing sources are disclosed

The manifest clearly records FDA, EUR-Lex, and ISO limitations. The README also states that ISO standards are not indexed. The evaluation report mentions ISO and EUR-Lex limitations but does not explicitly mention FDA discovery failure in the limitations list.

### Unanswerable records are genuinely unanswerable from the indexed corpus, with caveats

The 7 unanswerable questions ask about ISO full-text clauses/symbols, FDA-only guidance, EUR-Lex MDR text, India-specific requirements, or compliance certification. Those are not present in the indexed IMDRF/EC corpus. The caveat is that the abstention test depends on known keywords, so similar unsupported questions without those keywords may not abstain.

## Recommendations

1. Rename `citation_metadata_correctness` or replace it with a stricter check that validates cited chunk IDs, page/section metadata, and quoted evidence.
2. Add an evidence annotation file with source excerpt IDs for each eval record, separate from the code that generates the dataset.
3. Add answer-level evaluation only when generated answers are compared against expected facts and citations, not just retrieval text.
4. Remove or quarantine zero-byte failed downloads from `data/sources/raw/` during discovery.
5. Add a general retrieval confidence policy for abstention instead of relying mostly on unavailable-source keywords.
6. Improve PDF section extraction by tracking headings across pages and preserving hierarchy.
7. Add explicit report language that FDA sources are currently not indexed due to local access failure.
8. Keep the current metrics, but describe them as retrieval smoke-test metrics rather than full RAG quality metrics.
