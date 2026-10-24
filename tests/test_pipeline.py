from __future__ import annotations

import pytest

from labelai_rag.answer import ABSTAIN, deterministic_answer
from labelai_rag.io import read_json, read_jsonl
from labelai_rag.paths import CHUNKS_PATH, EVAL_PATH, INDEX_PATH, MANIFEST_PATH
from labelai_rag.retrieval import LocalTfidfRetriever


def test_manifest_records_official_sources_and_iso_limitations() -> None:
    manifest = read_json(MANIFEST_PATH)
    # 10 sources: 4 FDA HTML + eu_mdr + imdrf + ec_udi + fda_udi_pdf + 2 ISO
    assert len(manifest) == 10
    by_id = {row["source_id"]: row for row in manifest}

    # Core indexed sources
    assert by_id["imdrf_grrp_wg_n52_2024"]["access_status"].startswith("downloaded")
    assert by_id["ec_udi_device_registration"]["access_status"].startswith("downloaded")

    # New FDA HTML sources now indexed
    assert by_id["fda_general_device_labeling"]["access_status"].startswith("downloaded")
    assert by_id["fda_qsr_labeling"]["access_status"].startswith("downloaded")
    assert by_id["fda_specific_device_labeling"]["access_status"].startswith("downloaded")
    assert by_id["fda_udi_guidance"]["access_status"].startswith("downloaded")

    # EUR-Lex still fails (HTTP 202 empty body from server-side rendering)
    assert by_id["eu_mdr_2017_745_consolidated_2023_03_20"]["access_status"] == "download_failed"

    # Legacy FDA PDF still blocked
    assert by_id["fda_udi_form_content_guidance_2021"]["access_status"] == "download_failed"

    # ISO records are metadata-only
    assert by_id["iso_20417_2026"]["access_status"] == "metadata_only_full_standard_not_publicly_downloaded"
    assert by_id["iso_15223_1_2021"]["local_path"] is None


def test_chunks_have_real_provenance() -> None:
    chunks = read_jsonl(CHUNKS_PATH)
    # At least 80 chunks now that FDA pages are indexed (was 64, now 92)
    assert len(chunks) >= 80
    for chunk in chunks:
        assert chunk["chunk_id"]
        assert chunk["source_id"]
        assert chunk["title"]
        assert chunk["url"].startswith("https://")
        assert chunk["text"]


def test_fda_sources_are_indexed() -> None:
    """FDA HTML pages are now indexed; verify chunks exist for each."""
    chunks = read_jsonl(CHUNKS_PATH)
    source_ids = {chunk["source_id"] for chunk in chunks}
    assert "fda_general_device_labeling" in source_ids
    assert "fda_qsr_labeling" in source_ids
    assert "fda_specific_device_labeling" in source_ids
    assert "fda_udi_guidance" in source_ids


def test_fda_chunks_contain_cfr_references() -> None:
    """FDA chunks should reference 21 CFR Part 801."""
    chunks = read_jsonl(CHUNKS_PATH)
    fda_texts = [c["text"] for c in chunks if c["source_id"].startswith("fda_")]
    all_text = "\n".join(fda_texts).lower()
    assert "21 cfr" in all_text or "801" in all_text, "FDA chunks should reference 21 CFR or Part 801"


def test_expected_sources_retrieved_for_answerable_questions() -> None:
    retriever = LocalTfidfRetriever.load()
    rows = [row for row in read_jsonl(EVAL_PATH) if row["answerable_from_corpus"]]
    misses: list[str] = []
    for row in rows:
        sources = [result.chunk.source_id for result in retriever.search(row["question"], top_k=5)]
        if not set(row["expected_source_ids"]) & set(sources):
            misses.append(row["question_id"])
    assert not misses, f"Expected source not retrieved for: {misses}"


def test_retrieved_passages_contain_expected_evidence() -> None:
    retriever = LocalTfidfRetriever.load()
    rows = [row for row in read_jsonl(EVAL_PATH) if row["answerable_from_corpus"]]
    misses: list[str] = []
    for row in rows:
        text = "\n".join(result.chunk.text for result in retriever.search(row["question"], top_k=5)).lower()
        facts = [fact.lower() for fact in row["expected_key_facts"]]
        if facts and not any(fact in text for fact in facts):
            misses.append(row["question_id"])
    assert not misses, f"Key fact not found in top-5 for: {misses}"


def test_citations_point_to_real_metadata() -> None:
    retriever = LocalTfidfRetriever.load()
    result = retriever.search("What is the purpose of the IMDRF labeling guidance?", top_k=1)[0]
    assert result.chunk.title
    assert result.chunk.url.startswith("https://")
    assert result.chunk.page is not None or result.chunk.section


def test_fda_question_retrieves_fda_source() -> None:
    """21 CFR Part 801 question should now retrieve an FDA chunk (not just IMDRF)."""
    retriever = LocalTfidfRetriever.load()
    results = retriever.search("What regulation contains general labeling requirements for medical devices?", top_k=5)
    source_ids = [r.chunk.source_id for r in results]
    fda_sources = [s for s in source_ids if s.startswith("fda_")]
    assert fda_sources, f"Expected at least one FDA source in top-5, got: {source_ids}"


def test_jurisdiction_filter_returns_only_matching() -> None:
    """Jurisdiction filter should only return chunks from that jurisdiction."""
    retriever = LocalTfidfRetriever.load()
    results = retriever.search("labeling manufacturer address", top_k=10, jurisdiction="United States")
    for result in results:
        assert "united states" in result.chunk.jurisdiction.lower(), (
            f"Got non-US chunk: {result.chunk.jurisdiction} ({result.chunk.source_id})"
        )


def test_unanswerable_questions_trigger_abstention() -> None:
    answer = deterministic_answer(
        "What exact symbol does ISO 15223-1 require for sterile medical devices?",
        [],
    )
    assert ABSTAIN in answer


def test_iso_unavailable_source_triggers_abstention() -> None:
    """ISO terms should still trigger abstention since standards are not indexed."""
    from labelai_rag.retrieval import LocalTfidfRetriever
    retriever = LocalTfidfRetriever.load()
    results = retriever.search("ISO 20417 residual risk disclosure", top_k=5)
    answer = deterministic_answer("ISO 20417 residual risk disclosure clause number", results)
    assert ABSTAIN in answer


def test_fda_question_no_longer_abstains() -> None:
    """FDA questions should now produce evidence since FDA sources are indexed."""
    retriever = LocalTfidfRetriever.load()
    results = retriever.search("What does 21 CFR Part 801 require on device labels?", top_k=5)
    answer = deterministic_answer("What does 21 CFR Part 801 require on device labels?", results)
    # Should NOT abstain — FDA is now indexed
    assert ABSTAIN not in answer, "FDA question should not abstain — FDA sources are now indexed"


def test_india_market_still_abstains() -> None:
    """India-specific questions should still abstain — no Indian sources indexed."""
    answer = deterministic_answer("What labeling applies in India for Class III implants?", [])
    assert ABSTAIN in answer


def test_empty_question_fails_safely() -> None:
    retriever = LocalTfidfRetriever.load()
    with pytest.raises(ValueError):
        retriever.search("   ")


def test_index_exists() -> None:
    assert INDEX_PATH.exists()


def test_no_duplicate_chunk_ids() -> None:
    """Ingestion must not produce duplicate chunk_ids."""
    chunks = read_jsonl(CHUNKS_PATH)
    ids = [c["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids)), "Duplicate chunk_ids found in corpus"


def test_ingestion_is_idempotent() -> None:
    """Running ingestion twice should not change the number of chunks."""
    from labelai_rag.ingest import ingest_sources
    first_run = len(read_jsonl(CHUNKS_PATH))
    ingest_sources()
    second_run = len(read_jsonl(CHUNKS_PATH))
    assert first_run == second_run, f"Ingestion not idempotent: {first_run} vs {second_run} chunks"


def test_download_failure_recorded_accurately() -> None:
    """Sources that could not be downloaded must be recorded as download_failed, not indexed."""
    manifest = read_json(MANIFEST_PATH)
    chunks = read_jsonl(CHUNKS_PATH)
    indexed_source_ids = {c["source_id"] for c in chunks}
    for row in manifest:
        if row["access_status"] == "download_failed":
            assert row["source_id"] not in indexed_source_ids, (
                f"{row['source_id']} is marked download_failed but found in corpus"
            )


def test_provenance_fields_resolve_to_indexed_sources() -> None:
    """Every chunk source_id must match a manifest source_id that is downloaded."""
    manifest = read_json(MANIFEST_PATH)
    chunks = read_jsonl(CHUNKS_PATH)
    valid_ids = {
        row["source_id"]
        for row in manifest
        if row["access_status"].startswith("downloaded")
    }
    for chunk in chunks:
        assert chunk["source_id"] in valid_ids, (
            f"Chunk source_id {chunk['source_id']!r} not in downloaded sources"
        )
