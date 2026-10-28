# 🏥 LabelGuard AI
### AI-Powered Medical Device Labeling & Regulatory Intelligence

**LabelGuard AI** is an AI-assisted platform designed to streamline medical device labeling workflows through regulatory document retrieval, structured label authoring, label version comparison, and regulatory change-impact analysis.

The project combines Retrieval-Augmented Generation (RAG), regulatory knowledge sources, and automated analysis tools to support more efficient and traceable labeling reviews.

---

## ✨ Features

- 🔍 **Regulatory Question Answering** — Retrieve relevant regulatory information from indexed source documents using evidence-grounded RAG.
- 🧠 **Change-Impact Analysis** — Analyze potential impacts of regulatory changes across supported categories.
- 📝 **AI-Assisted Label Authoring** — Generate and organize structured medical device label content across 14 fields.
- 🔄 **Label Version Comparison** — Compare old and new label versions and highlight differences.
- 🎨 **Artwork Validation** — Validate supported label artwork and generate visual representations of differences.
- 📚 **Regulatory Knowledge Base** — Search indexed regulatory resources from the FDA, IMDRF, and European Commission.
- 🧪 **Evaluation & Testing** — Automated tests and a benchmark for evaluating retrieval, grounding, citations, and abstention.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| FastAPI | Backend API |
| Streamlit | Interactive user interface |
| Retrieval-Augmented Generation (RAG) | Evidence-grounded question answering |
| TF-IDF | Local document retrieval |
| Pytest | Automated testing |

## 🏗️ System Architecture

```text
                 ┌──────────────────────┐
                 │       User           │
                 └──────────┬───────────┘
                            │
                 ┌──────────▼───────────┐
                 │   Streamlit Frontend │
                 │       app.py         │
                 └──────────┬───────────┘
                            │
                 ┌──────────▼───────────┐
                 │     FastAPI Backend  │
                 │    backend/main.py   │
                 └──────────┬───────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
  ┌───────▼────────┐ ┌──────▼────────┐ ┌──────▼────────┐
  │ Regulatory RAG │ │ Change-Impact  │ │ Label Authoring│
  │ & Retrieval    │ │ Analysis       │ │ & Comparison   │
  └───────┬────────┘ └──────┬────────┘ └──────┬────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                 ┌──────────▼───────────┐
                 │ Regulatory Sources & │
                 │ Project Data         │
                 └──────────────────────┘
```

## 📚 Regulatory Knowledge Base

The project has been developed around regulatory resources covering:

- FDA general medical device labeling
- FDA Quality System Regulation
- FDA device-specific resources
- FDA Unique Device Identification (UDI) guidance
- IMDRF UDI guidance
- European Commission UDI/EUDAMED resources

The indexed corpus has previously been reported to contain **92 chunks across six source groups**. Coverage may change as the knowledge base evolves.

## 📂 Project Structure

```text
AI-BASED-MEDICAL-DEVICE-LABELING/
│
├── app.py                 # Streamlit frontend
├── backend/
│   └── main.py            # FastAPI backend entry point
├── labelai_rag/           # RAG and retrieval components
├── engines/               # Labeling and analysis engines
├── data/                  # Project data and resources
├── reports/               # Generated reports and outputs
├── tests/                 # Automated tests
├── requirements.txt       # Python dependencies
├── .gitignore
└── README.md
```

## 🚀 Installation & Setup

### Prerequisites

- Python installed on your system
- Git
- pip

### 1. Clone the repository

```bash
git clone https://github.com/soubhagyadixit41-ops/AI-BASED-MEDICAL-DEVICE-LABELING.git
cd AI-BASED-MEDICAL-DEVICE-LABELING
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Start the FastAPI backend

From the project root, run:

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

Backend API documentation:

**http://127.0.0.1:8000/docs**

Keep this terminal running.

### 5. Start the Streamlit frontend

Open a second terminal in the project root, activate the virtual environment, and run:

```bash
python -m streamlit run app.py --server.port 8501
```

Open the application:

**http://localhost:8501**

> Ensure the frontend's configured API URL matches the backend address and port.

## 🧪 Running Tests

Run the automated test suite from the project root:

```bash
python -m pytest -q
```

Review the test output to confirm that the expected tests were discovered and passed.

## 📊 Evaluation

The project includes evaluation workflows for assessing:

- Retrieval quality and ranking
- Evidence coverage in generated answers
- Citation metadata correctness
- Abstention when evidence is insufficient
- Reliability of core labeling and change-impact workflows

Previously reported results include Recall@5 of 1.000 and MRR of 0.963 on an evaluation set. These are historical benchmark results and should be revalidated against the current code and dataset before being treated as current.

## 🔐 Responsible Use

- Verify generated answers against authoritative regulatory documents.
- Have qualified regulatory professionals review generated label content and impact assessments.
- Do not commit API keys, passwords, or confidential information.
- Use the correct jurisdiction, device classification, and applicable regulatory revisions when reviewing requirements.

## 🗺️ Future Improvements

- Expand regulatory document coverage.
- Improve clause-level evidence traceability.
- Strengthen automated regression testing.
- Enhance audit trails and report exports.
- Improve deployment configuration and error handling.
- Add further evaluation datasets and real-world validation.

## ⚖️ Disclaimer

LabelGuard AI is an AI-assisted research and workflow prototype. It is not an official FDA, IMDRF, or European Commission product and does not certify regulatory compliance. Outputs may be incomplete or incorrect and must be independently reviewed by qualified professionals against applicable authoritative requirements before being used for regulatory submissions or labeling decisions.
