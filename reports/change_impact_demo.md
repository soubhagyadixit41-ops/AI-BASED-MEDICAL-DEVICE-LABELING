# Change-Impact Demo

## Scenario

Fictional demo input only; no patient data or real product record is used.

- Product: illustrative cardiac stent
- Market: US
- Change: manufacturer address updated
- Current label elements: manufacturer name/address, device identifier, UDI, warnings, symbols, instructions for use

Input file:

`data/change_impact/sample_change_request.json`

Generated assessment:

`data/change_impact/sample_impact_assessment.json`

Command:

```powershell
.\.venv\Scripts\python.exe -m labelai_rag.cli impact data\change_impact\sample_change_request.json --output data\change_impact\sample_impact_assessment.json
```

## Evidence Used

The engine identified `manufacturer name/address` as the affected label element.

Supporting evidence came from IMDRF GRRP WG/N52 FINAL:2024:

- Page 19, Section 5.2.9: label should contain the manufacturer name and address in a recognizable format that allows the manufacturer location to be established.
- Page 21, Section 5.3.9: instructions for use should contain manufacturer name and address and contact information where required by the regulatory authority having jurisdiction.

## Assessment Behavior

The engine recommends review actions rather than declaring the label compliant or noncompliant. It marks human review as required and preserves traceability between:

- original change request
- affected label element
- retrieved evidence
- reason for impact
- recommended review action
- missing information

## Limitations

- The requested market is US, but FDA sources are not indexed because local discovery/download failed.
- The supporting evidence is therefore from international IMDRF labeling principles, not US-specific FDA requirements.
- The indexed corpus is currently limited to IMDRF labeling principles and the European Commission UDI/Device Registration page.
- This output is informational and requires qualified regulatory review.

## Test Results

Full test suite:

```text
16 passed in 3.13s
```

The tests cover relevant evidence, incomplete evidence, unsupported markets, unrelated label elements, missing product context, invalid input, provenance, and human-review flags.
