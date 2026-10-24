from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .io import write_json
from .models import SourceRecord
from .paths import MANIFEST_PATH, PROJECT_ROOT, RAW_DIR, ensure_dirs


SOURCE_CONFIG: list[dict] = [
    {
        "source_id": "fda_general_device_labeling",
        "official_title": "General Device Labeling Requirements",
        "publisher": "U.S. Food and Drug Administration",
        "jurisdiction": "United States",
        "url": "https://www.fda.gov/medical-devices/device-labeling/general-device-labeling-requirements",
        "source_type": "html",
    },
    {
        "source_id": "fda_qsr_labeling",
        "official_title": "Quality System Regulation Labeling Requirements",
        "publisher": "U.S. Food and Drug Administration",
        "jurisdiction": "United States",
        "url": "https://www.fda.gov/medical-devices/device-labeling/quality-system-regulation-labeling-requirements",
        "source_type": "html",
    },
    {
        "source_id": "fda_specific_device_labeling",
        "official_title": "Labeling Requirements for Specific Devices",
        "publisher": "U.S. Food and Drug Administration",
        "jurisdiction": "United States",
        "url": "https://www.fda.gov/medical-devices/general-device-labeling-requirements/labeling-requirements-specific-devices",
        "source_type": "html",
    },
    {
        "source_id": "fda_udi_guidance",
        "official_title": "Unique Device Identification System: Form and Content of the Unique Device Identifier (UDI)",
        "publisher": "U.S. Food and Drug Administration",
        "jurisdiction": "United States",
        "url": "https://www.fda.gov/regulatory-information/search-fda-guidance-documents/unique-device-identification-system-form-and-content-unique-device-identifier-udi",
        "source_type": "html",
    },
    {
        "source_id": "eu_mdr_2017_745_consolidated_2023_03_20",
        "official_title": "Consolidated text: Regulation (EU) 2017/745 on medical devices",
        "publisher": "EUR-Lex / Publications Office of the European Union",
        "jurisdiction": "European Union",
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:02017R0745-20230320",
        "document_date": "2023-03-20",
        "source_type": "pdf",
    },
    {
        "source_id": "imdrf_grrp_wg_n52_2024",
        "official_title": "Principles of Labelling for Medical Devices and IVD Medical Devices",
        "publisher": "International Medical Device Regulators Forum",
        "jurisdiction": "International",
        "url": "https://www.imdrf.org/sites/default/files/2024-04/IMDRF%20GRRP%20WG%20N52%20%28Edition%202%29.pdf",
        "document_date": "2024-04-26",
        "source_type": "pdf",
    },
    {
        "source_id": "ec_udi_device_registration",
        "official_title": "UDI/Device registration",
        "publisher": "European Commission Directorate-General for Health and Food Safety",
        "jurisdiction": "European Union",
        "url": "https://health.ec.europa.eu/medical-devices-eudamed/udidevice-registration_en",
        "source_type": "html",
    },
    {
        "source_id": "fda_udi_form_content_guidance_2021",
        "official_title": "Unique Device Identification System: Form and Content of the Unique Device Identifier (UDI)",
        "publisher": "U.S. Food and Drug Administration",
        "jurisdiction": "United States",
        "url": "https://www.fda.gov/media/99084/download",
        "document_date": "2021-07",
        "source_type": "pdf",
    },
    {
        "source_id": "iso_20417_2026",
        "official_title": "ISO 20417:2026 Medical devices - Information to be supplied by the manufacturer",
        "publisher": "International Organization for Standardization",
        "jurisdiction": "International standard",
        "url": "https://www.iso.org/standard/88714.html",
        "document_date": "2026",
        "source_type": "metadata",
        "restricted": True,
    },
    {
        "source_id": "iso_15223_1_2021",
        "official_title": "ISO 15223-1:2021 Medical devices - Symbols to be used with information to be supplied by the manufacturer - Part 1: General requirements",
        "publisher": "International Organization for Standardization",
        "jurisdiction": "International standard",
        "url": "https://www.iso.org/standard/77326.html",
        "document_date": "2021",
        "source_type": "metadata",
        "restricted": True,
    },
]


def safe_filename(source_id: str, url: str, source_type: str) -> str:
    suffix = ".pdf" if source_type == "pdf" else ".html"
    parsed = urlparse(url)
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", parsed.path.strip("/").split("/")[-1] or source_id)
    return f"{source_id}_{digest}_{stem[:50]}{suffix}"


def extract_title_date_from_html(html: str) -> tuple[str | None, str | None]:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = h1.get_text(" ", strip=True) if h1 else None
    text = soup.get_text("\n", strip=True)
    match = re.search(
        r"(Published date|Issued|Last updated|Date Issued)\s*[:\n]\s*"
        r"([0-9]{1,2}\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+[0-9]{4})",
        text,
    )
    return title, match.group(2) if match else None


def _make_session() -> requests.Session:
    """Return a fresh session with a browser-like User-Agent."""
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return sess


def _is_bot_protection_page(url: str, content: bytes) -> bool:
    """Return True if the response looks like a bot-protection or apology page."""
    if "apology" in url or "abuse-detection" in url:
        return True
    if b"apology_objects" in content or b"abuse-detection" in content:
        return True
    return False


def discover_sources(timeout: int = 45) -> list[SourceRecord]:
    ensure_dirs()
    discovered_at = datetime.now(timezone.utc).isoformat()
    manifest: list[SourceRecord] = []

    for config in SOURCE_CONFIG:
        source_id = config["source_id"]
        url = config["url"]
        source_type = config["source_type"]

        # ISO / paywalled metadata-only sources — record without downloading.
        if config.get("restricted"):
            manifest.append(
                SourceRecord(
                    source_id=source_id,
                    official_title=config["official_title"],
                    publisher=config["publisher"],
                    jurisdiction=config["jurisdiction"],
                    url=url,
                    document_date=config.get("document_date"),
                    access_status="metadata_only_full_standard_not_publicly_downloaded",
                    source_type=source_type,
                    notes=(
                        "Official ISO catalogue page recorded. "
                        "Full standard text is copyrighted/paywalled and was not downloaded or indexed."
                    ),
                    discovered_at=discovered_at,
                )
            )
            continue

        # Reuse if already downloaded (idempotent).
        expected_fname = safe_filename(source_id, url, source_type)
        reuse_path = RAW_DIR / expected_fname
        if reuse_path.exists() and reuse_path.stat().st_size > 500:
            local_path = str(reuse_path.relative_to(PROJECT_ROOT))
            status = "downloaded_public_pdf" if source_type == "pdf" else "downloaded_public_html"
            title = config["official_title"]
            document_date = config.get("document_date")
            if source_type != "pdf":
                html_title, html_date = extract_title_date_from_html(
                    reuse_path.read_text(encoding="utf-8", errors="replace")
                )
                title = html_title or title
                document_date = document_date or html_date
            manifest.append(
                SourceRecord(
                    source_id=source_id,
                    official_title=title,
                    publisher=config["publisher"],
                    jurisdiction=config["jurisdiction"],
                    url=url,
                    document_date=document_date,
                    access_status=status,
                    source_type=source_type,
                    local_path=local_path,
                    notes="Reused existing downloaded file.",
                    discovered_at=discovered_at,
                )
            )
            continue

        # Attempt download — use a fresh session per request to defeat session-based bot protection.
        local_path = None
        status = "download_failed"
        notes = ""
        title = config["official_title"]
        document_date = config.get("document_date")

        try:
            session = _make_session()
            response = session.get(url, timeout=timeout, allow_redirects=True)

            # Detect bot-protection redirect (FDA abuse-detection, etc.)
            if _is_bot_protection_page(response.url, response.content[:512]):
                raise RuntimeError(
                    f"Bot-protection page detected (final URL: {response.url}). Content was not saved."
                )

            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code} from {response.url}")

            if len(response.content) < 500:
                raise RuntimeError(
                    f"Downloaded response was empty or too small ({len(response.content)} bytes)"
                )

            content_type = response.headers.get("content-type", "").lower()
            if source_type == "pdf" or "application/pdf" in content_type:
                if not response.content.startswith(b"%PDF"):
                    raise RuntimeError(
                        f"Expected PDF but received content-type {content_type or 'unknown'}"
                    )
                filename = safe_filename(source_id, response.url, "pdf")
                path = RAW_DIR / filename
                path.write_bytes(response.content)
                local_path = str(path.relative_to(PROJECT_ROOT))
                status = "downloaded_public_pdf"
            else:
                filename = safe_filename(source_id, response.url, "html")
                path = RAW_DIR / filename
                path.write_text(response.text, encoding=response.encoding or "utf-8")
                local_path = str(path.relative_to(PROJECT_ROOT))
                html_title, html_date = extract_title_date_from_html(response.text)
                title = html_title or title
                document_date = document_date or html_date
                status = "downloaded_public_html"

        except Exception as exc:  # noqa: BLE001 — manifest must record discovery failures.
            notes = f"Discovery/download failed: {exc}"

        manifest.append(
            SourceRecord(
                source_id=source_id,
                official_title=title,
                publisher=config["publisher"],
                jurisdiction=config["jurisdiction"],
                url=url,
                document_date=document_date,
                access_status=status,
                source_type=source_type,
                local_path=local_path,
                notes=notes,
                discovered_at=discovered_at,
            )
        )

        # Polite delay between HTTP requests.
        time.sleep(0.5)

    write_json(MANIFEST_PATH, [record.__dict__ for record in manifest])
    return manifest
