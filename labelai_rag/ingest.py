from __future__ import annotations

import hashlib
import re
from pathlib import Path

import fitz
from bs4 import BeautifulSoup

from .io import read_json, write_jsonl
from .models import Chunk, SourceRecord
from .paths import CHUNKS_PATH, MANIFEST_PATH, PROJECT_ROOT


HEADING_RE = re.compile(
    r"^(#{1,4}\s+|[0-9]+(\.[0-9]+)*\.?\s+|Article\s+[0-9A-Za-z]+|ANNEX\s+[IVXLCDM]+|Chapter\s+[IVXLCDM]+|Section\s+[0-9]+)",
    re.I,
)

# Boilerplate patterns to strip from FDA / government HTML
BOILERPLATE_RE = re.compile(
    r"(skip to (main content|search|footer)|official website of the united states|here.s how you know|"
    r"\.gov means it.s official|site is secure|https means you.ve safely|"
    r"subscribe to rss feeds?|follow fda on|sharing tools|website feedback|"
    r"contact fda|report a (problem|adverse|safety)|usa\.gov|back to top)",
    re.I,
)

# Terminal/footer section headings that signal end of substantive content
FDA_SECTION_SKIP = re.compile(
    r"^(related links|related information|get email updates|subscribe to rss|"
    r"accessibility|nondiscrimination|freedom of information|report a website problem|"
    r"privacy policy$|contact (fda|us)$|website feedback|site map)",
    re.I,
)


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\u00a0", " ").replace("\u2011", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def stable_chunk_id(source_id: str, text: str, page: int | None, section: str | None) -> str:
    basis = f"{source_id}|{page}|{section}|{text[:500]}"
    return f"{source_id}:{hashlib.sha1(basis.encode('utf-8')).hexdigest()[:12]}"


def load_manifest() -> list[SourceRecord]:
    rows = read_json(MANIFEST_PATH)
    assert isinstance(rows, list)
    return [SourceRecord(**row) for row in rows]


def _is_boilerplate_line(line: str) -> bool:
    """Return True for government nav, cookie, footer boilerplate."""
    stripped = line.strip()
    if len(stripped) < 5:
        return True
    if BOILERPLATE_RE.search(stripped):
        return True
    return False


def _clean_html_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove script, style, nav, footer, cookie banners, breadcrumbs."""
    for tag in soup(
        [
            "script",
            "style",
            "nav",
            "footer",
            "header",
            "form",
            "aside",
            "noscript",
            "iframe",
            "svg",
            "picture",
        ]
    ):
        tag.decompose()
    # FDA-specific breadcrumb / share panels
    for cls_name in [
        "breadcrumbs",
        "usa-breadcrumb",
        "page-nav",
        "social-sharing",
        "back-to-top",
        "cookie",
        "site-search",
        "utility-nav",
        "alert",
    ]:
        for tag in soup.find_all(class_=re.compile(cls_name, re.I)):
            tag.decompose()
    return soup


def html_to_sections(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    soup = _clean_html_soup(soup)
    main = soup.find("main") or soup.find("article") or soup.body or soup

    sections: list[tuple[str, list[str]]] = []
    current_heading = "Page content"
    current_lines: list[str] = []
    skip_rest = False

    for elem in main.find_all(["h1", "h2", "h3", "h4", "p", "li", "td", "th"]):
        raw = elem.get_text(" ", strip=True)
        if not raw or _is_boilerplate_line(raw):
            continue

        # Stop when we hit footer-style sections
        if elem.name in {"h2", "h3"} and FDA_SECTION_SKIP.match(raw):
            skip_rest = True
        if skip_rest:
            continue

        if elem.name in {"h1", "h2", "h3", "h4"}:
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = raw
            current_lines = [raw]
        else:
            current_lines.append(raw)

    if current_lines:
        sections.append((current_heading, current_lines))

    result = []
    for heading, lines in sections:
        combined = clean_text("\n".join(lines))
        if len(combined) > 80:
            result.append((heading, combined))
    return result


def pdf_to_sections(path: Path) -> list[tuple[int, str, str]]:
    sections: list[tuple[int, str, str]] = []
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            text = clean_text(page.get_text("text"))
            if not text:
                continue
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            heading = f"Page {page_index}"
            for line in lines[:12]:
                if HEADING_RE.match(line) and len(line) < 140:
                    heading = line
                    break
            sections.append((page_index, heading, text))
    return sections


def split_long_text(text: str, max_chars: int = 1800) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n|(?<=\.)\s+(?=[A-Z0-9])", text) if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 <= max_chars:
            current = f"{current}\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def ingest_sources() -> list[Chunk]:
    chunks: list[Chunk] = []
    seen_hashes: set[str] = set()
    source_counts: dict[str, int] = {}
    errors: list[str] = []

    for source in load_manifest():
        if not source.local_path or not source.access_status.startswith("downloaded"):
            continue
        raw_path = PROJECT_ROOT / source.local_path
        if not raw_path.exists():
            errors.append(f"[WARN] {source.source_id}: local_path does not exist: {raw_path}")
            continue

        try:
            extracted: list[tuple[int | None, str, str]]
            if source.source_type == "pdf" or raw_path.suffix.lower() == ".pdf":
                extracted = list(pdf_to_sections(raw_path))
            else:
                html = raw_path.read_text(encoding="utf-8", errors="replace")
                extracted = [(None, section, text) for section, text in html_to_sections(html)]
        except Exception as exc:  # noqa: BLE001
            errors.append(f"[ERROR] {source.source_id}: extraction failed: {exc}")
            continue

        if not extracted:
            errors.append(f"[WARN] {source.source_id}: no sections extracted — check file content.")
            continue

        count = 0
        for page, section, text in extracted:
            for part in split_long_text(text):
                cleaned = clean_text(part)
                digest = hashlib.sha1(cleaned.lower().encode("utf-8")).hexdigest()
                if digest in seen_hashes or len(cleaned) < 80:
                    continue
                seen_hashes.add(digest)
                chunks.append(
                    Chunk(
                        chunk_id=stable_chunk_id(source.source_id, cleaned, page, section),
                        source_id=source.source_id,
                        title=source.official_title,
                        publisher=source.publisher,
                        jurisdiction=source.jurisdiction,
                        url=source.url,
                        text=cleaned,
                        section=section,
                        page=page,
                        metadata={
                            "document_date": source.document_date,
                            "access_status": source.access_status,
                        },
                    )
                )
                count += 1
        source_counts[source.source_id] = count

    if errors:
        for msg in errors:
            print(msg)

    print(f"Ingested {len(chunks)} chunks from {len(source_counts)} source(s):")
    for sid, cnt in source_counts.items():
        print(f"  {sid}: {cnt} chunk(s)")

    write_jsonl(CHUNKS_PATH, chunks)
    return chunks
