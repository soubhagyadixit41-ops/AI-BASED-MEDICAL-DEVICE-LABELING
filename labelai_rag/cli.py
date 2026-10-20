from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .answer import answer_question
from .change_impact import assess_change_impact_file
from .eval_dataset import build_eval_dataset
from .evaluation import evaluate, print_report
from .ingest import ingest_sources
from .paths import CHUNKS_PATH, EVAL_PATH, INDEX_PATH, MANIFEST_PATH, REPORT_PATH, ensure_dirs
from .retrieval import build_index
from .sources import discover_sources


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LabelAI regulatory RAG engine")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("discover", help="Discover/download official sources and write the manifest")
    sub.add_parser("ingest", help="Extract and chunk downloaded official sources")
    sub.add_parser("build-index", help="Build the local TF-IDF vector index")
    sub.add_parser("make-eval", help="Create verified evaluation dataset")
    eval_parser = sub.add_parser("evaluate", help="Evaluate retrieval, citation metadata, and abstention")
    eval_parser.add_argument("--top-k", type=int, default=5)
    ask_parser = sub.add_parser("ask", help="Ask a retrieval-grounded question")
    ask_parser.add_argument("question")
    ask_parser.add_argument("--top-k", type=int, default=5)
    impact_parser = sub.add_parser("impact", help="Run change-impact analysis for a JSON change request")
    impact_parser.add_argument("input_json")
    impact_parser.add_argument("--output", default=None)
    sub.add_parser("all", help="Run discovery, ingestion, indexing, eval generation, and evaluation")
    return parser


def main(argv: list[str] | None = None) -> int:
    ensure_dirs()
    args = build_parser().parse_args(argv)
    if args.command == "discover":
        records = discover_sources()
        print(f"Wrote {len(records)} source records to {MANIFEST_PATH}")
    elif args.command == "ingest":
        chunks = ingest_sources()
        print(f"Wrote {len(chunks)} chunks to {CHUNKS_PATH}")
    elif args.command == "build-index":
        retriever = build_index()
        print(f"Wrote index with {len(retriever.chunks)} chunks to {INDEX_PATH}")
    elif args.command == "make-eval":
        records = build_eval_dataset()
        print(f"Wrote {len(records)} eval records to {EVAL_PATH}")
    elif args.command == "evaluate":
        print_report(evaluate(top_k=args.top_k))
    elif args.command == "ask":
        print(answer_question(args.question, top_k=args.top_k))
    elif args.command == "impact":
        input_path = Path(args.input_json)
        output_path = Path(args.output) if args.output else input_path.with_name(input_path.stem + "_impact_assessment.json")
        assessment = assess_change_impact_file(input_path, output_path)
        print(json.dumps(assessment, indent=2, ensure_ascii=False))
        print(f"Wrote impact assessment to {output_path}")
    elif args.command == "all":
        discover_sources()
        chunks = ingest_sources()
        build_index()
        build_eval_dataset()
        report = evaluate()
        print(f"Built {len(chunks)} chunks and wrote report to {REPORT_PATH}")
        print_report(report)
    else:
        raise AssertionError(args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
