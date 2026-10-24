from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "sources" / "raw"
SOURCE_DIR = DATA_DIR / "sources"
PROCESSED_DIR = DATA_DIR / "processed"
EVAL_DIR = DATA_DIR / "evaluation"
REPORTS_DIR = PROJECT_ROOT / "reports"

MANIFEST_PATH = SOURCE_DIR / "source_manifest.json"
CHUNKS_PATH = PROCESSED_DIR / "regulatory_chunks.jsonl"
INDEX_PATH = PROCESSED_DIR / "tfidf_index.joblib"
EVAL_PATH = EVAL_DIR / "rag_eval.jsonl"
REPORT_PATH = REPORTS_DIR / "evaluation_report.json"
SUMMARY_PATH = REPORTS_DIR / "test_results_summary.md"


def ensure_dirs() -> None:
    for path in [RAW_DIR, SOURCE_DIR, PROCESSED_DIR, EVAL_DIR, REPORTS_DIR]:
        path.mkdir(parents=True, exist_ok=True)
