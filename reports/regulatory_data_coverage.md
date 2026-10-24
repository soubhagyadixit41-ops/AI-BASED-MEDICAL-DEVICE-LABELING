# LabelAI — Regulatory Data Coverage Report

**Date:** 2026-10-13  
**Corpus Chunks:** 92  
**Manifest Sources:** 10  
**Indexed Sources:** 6  

---

## 1. Executive Summary

In Phase 2, the LabelAI knowledge base was expanded from a 2-source baseline (64 chunks) to a 6-source corpus (92 chunks). Crucially, official US FDA regulatory requirements (21 CFR Part 801 General Device Labeling, Quality System Regulation Labeling, Specific Device Labeling, and UDI guidance) were recovered and successfully indexed into the pipeline.

All source download attempts adhere strictly to legal and technical constraints: no bot protection was bypassed, paywalls were respected, and official access status is accurately recorded in `data/sources/source_manifest.json`.

---

## 2. Source Inventory & Access Status

| Source ID | Title / Regulation | Jurisdiction | Format | Access Status | Chunks | Local Path / Notes |
|---|---|---|---|---|---|---|
| `fda_general_device_labeling` | General Device Labeling Requirements (21 CFR 801) | United States | HTML | `downloaded_public_html` | 7 | `data/sources/raw/fda_general_device_labeling_08590e47_general-device-labeling-requirements.html` |
| `fda_qsr_labeling` | Quality System Regulation Labeling Requirements (21 CFR 820) | United States | HTML | `downloaded_public_html` | 17 | `data/sources/raw/fda_qsr_labeling_cb23586d_quality-system-regulation-labeling-requirements.html` |
| `fda_specific_device_labeling` | Labeling Requirements for Specific Devices (21 CFR 801.405–437) | United States | HTML | `downloaded_public_html` | 2 | `data/sources/raw/fda_specific_device_labeling_b45cb539_labeling-requirements-specific-devices.html` |
| `fda_udi_guidance` | Form and Content of UDI (21 CFR 801.40) | United States | HTML | `downloaded_public_html` | 2 | `data/sources/raw/fda_udi_guidance_682167b6_unique-device-identification-system-form-and-conte.html` |
| `imdrf_grrp_wg_n52_2024` | Principles of Labelling for Medical Devices & IVDs (Ed. 2) | International | PDF | `downloaded_public_pdf` | 55 | `data/sources/raw/imdrf_grrp_wg_n52_2024_f02d4162_IMDRF_20GRRP_20WG_20N52_20_28Edition_202_29.pdf.pdf` |
| `ec_udi_device_registration` | EUDAMED UDI/Device Registration & EMDN | European Union | HTML | `downloaded_public_html` | 9 | `data/sources/raw/ec_udi_device_registration_2dfd2327_udidevice-registration_en.html` |
| `eu_mdr_2017_745_consolidated_2023_03_20` | Consolidated Regulation (EU) 2017/745 on Medical Devices | European Union | PDF | `download_failed` | 0 | EUR-Lex endpoint returned HTTP 202 with 0 bytes (server-side async render). |
| `fda_udi_form_content_guidance_2021` | Form & Content of UDI (Direct PDF endpoint) | United States | PDF | `download_failed` | 0 | Direct media endpoint redirected to FDA abuse detection apology page; HTML guidance document indexed instead. |
| `iso_20417_2026` | ISO 20417:2026 (Information to be supplied by manufacturer) | International standard | Metadata | `metadata_only_full_standard_not_publicly_downloaded` | 0 | Copyrighted / paywalled standard. Official catalogue entry recorded. |
| `iso_15223_1_2021` | ISO 15223-1:2021 (Symbols for medical device labeling) | International standard | Metadata | `metadata_only_full_standard_not_publicly_downloaded` | 0 | Copyrighted / paywalled standard. Official catalogue entry recorded. |

**Total Chunks in Corpus:** 92 (0 duplicates, SHA-1 deduplicated).

---

## 3. Ingestion Pipeline Improvements

1. **Idempotence and Deduplication:**
   - Content-hashing using SHA-1 on canonicalized chunk text (`stable_chunk_id`).
   - Duplicate chunk detection verifies zero duplicate IDs (`test_no_duplicate_chunk_ids`).
   - Multiple ingestion runs produce identical chunk counts (`test_ingestion_is_idempotent`).

2. **Boilerplate Stripping:**
   - Cleaned government and agency navigation: removed USWDS breadcrumbs, `.gov` banners, social sharing, footer links, and cookie alerts.
   - Terminal footer recognition prevents trailing utility links from contaminating chunk content.

3. **Provenance Integrity:**
   - Every chunk retains `chunk_id`, `source_id`, `title`, `publisher`, `jurisdiction`, `url`, `page` (for PDFs), `section` (for HTML/PDF), and document dates.
   - 100% of chunk source references link to validated entries in `source_manifest.json` (`test_provenance_fields_resolve_to_indexed_sources`).

---

## 4. Remaining Coverage Limitations

1. **EUR-Lex Consolidated MDR Text:**
   - EUR-Lex returns HTTP 202 (Accepted) with 0 bytes on programmatic requests. EU MDR regulatory questions that require the raw legislative text correctly abstain.
2. **ISO Standards (ISO 15223-1 & ISO 20417):**
   - Retained as metadata-only records in compliance with copyright restrictions. Full symbols and clause numbers correctly trigger abstention.
3. **Indian Medical Device Rules (CDSCO):**
   - India is currently an unindexed market. Indian-market requests correctly trigger evidence-gap warnings.
