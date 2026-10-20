# LabelAI — Streamlit Demo Report (Phase 3)

**Date:** 2026-10-13  
**Streamlit Version:** 1.65.0  
**Python Version:** 3.11.0rc2  
**Test Suite:** 47 passing automated tests  

---

## 1. Server Launch Command

```powershell
& ".\.venv\Scripts\python.exe" -m streamlit run app.py --server.port 8506
```

---

## 2. Server Startup & Verification

- **Endpoint Smoke Test:** `GET http://localhost:8506` -> `200 OK`
- **Healthz Check:** `GET http://localhost:8506/healthz` -> `200 OK`
- **Port:** Port 8506 (running clean and responsive; port 8505 avoided due to zombie process reservation).

---

## 3. UI Overview of 4 Functional Tabs

### Tab 1: Overview Dashboard
- **Runtime Metrics:** Dynamically reflects **92 indexed chunks**, **6 indexed sources**, **50 evaluation questions**, and **42 answerable / 8 unanswerable questions**.
- **Interactive Source Cards:** Displays 6 green indexed source pills (`fda_general_device_labeling`, `fda_qsr_labeling`, `fda_specific_device_labeling`, `fda_udi_guidance`, `imdrf_grrp_wg_n52_2024`, `ec_udi_device_registration`) and 4 gap disclosures for unindexed sources (ISO 15223-1, ISO 20417, EUR-Lex, FDA obsolete).
- **Workflow Stepper:** 5-step horizontal pipeline: Product Change → Concept Analysis → Regulatory Evidence → Impact Assessment → Qualified Human Review.
- **Evaluation Metrics:** Displays Recall@5 (1.000), MRR (0.976), Key-fact Hit (1.000), and Abstention (1.000).

### Tab 2: Generalized Change Impact Analysis
- **Expanded Input Model:** Supports all 10 regulatory change categories (Manufacturer info, Intended purpose, Device specs, Materials/composition, Warning/precaution, Sterilization/shelf life, UDI/identifier, Packaging, Translation, Other/unknown) alongside legacy inputs.
- **Expanded Label Elements Selection:** Allows multi-selection across `manufacturer name/address`, `device identifier`, `UDI`, `warnings`, `precautions`, `symbols`, `instructions for use`, `intended purpose`, `storage/shelf life`, `sterility`, `composition`, and `packaging`.
- **Live Multi-Stage Pipeline Execution:** Runs `labelai_rag.change_impact.assess_change_impact` directly upon form submission.
- **Evidence Quality Badges:** Renders `Supported` (green), `Partial / Potentially relevant` (yellow), or `Evidence gap` (red) badges for each element based on target market alignment and retrieved score.
- **Traceable Provenance:** Expandable cards display source title, publisher, jurisdiction, section/page, retrieval score, and official links.
- **Missing Information & Limitations:** Highlights required technical validation documentation (e.g. ISO 11607 packaging validation, ISO 11135 sterilization reports) prior to label sign-off.
- **Audit Exports:** Downloads live `change_request.json` and `impact_assessment.json`.

### Tab 3: Regulatory Q&A
- **Corpus Search:** Queries the 92-chunk indexed knowledge base with TF-IDF and exact clause boosting.
- **Jurisdiction Filtering:** Automatically filters by selected target market (United States, European Union, International).
- **Abstention Safeguards:** Questions regarding unindexed topics or unsupported markets trigger explicit abstention notifications.

### Tab 4: Evidence & Evaluation
- **Source Manifest:** Real-time table of all 10 sources with access status, document date, and notes.
- **Evaluation Metrics Table:** Displays 50-question evaluation metrics, exact definitions, and limitations.
