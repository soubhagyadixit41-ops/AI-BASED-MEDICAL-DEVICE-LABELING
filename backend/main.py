from pathlib import Path
import logging
import sys

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LABELS_FILE = DATA_DIR / "labels.csv"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engines.change_impact import find_affected_labels
from engines.compliance_risk import check_label
from engines.genai_labeling import run_rag
from engines.artwork_validator import create_label

logger = logging.getLogger(__name__)

app = FastAPI(
    title="LabelGuard AI API",
    description=(
        "Prototype APIs for label impact analysis, required-field checks, "
        "reference-assisted drafting, and demo artwork generation."
    ),
    version="1.0.0",
)

# Allow the local Streamlit frontend. CORS is relevant to browser-based
# requests; Python requests() calls from Streamlit are not subject to CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:8503",
        "http://127.0.0.1:8503",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ChangeImpactRequest(BaseModel):
    product: str = Field(min_length=1, max_length=200)
    changed_field: str = Field(min_length=1, max_length=200)

    @field_validator("product", "changed_field")
    @classmethod
    def reject_blank_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field must not be blank.")
        return value


class LabelRiskRequest(BaseModel):
    product_name: str = Field(default="", max_length=300)
    manufacturer: str = Field(default="", max_length=500)
    intended_use: str = Field(default="", max_length=2000)


class DraftRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    k: int = Field(default=3, ge=1, le=10)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Query must contain at least 3 non-whitespace characters.")
        return value


class ArtworkRequest(BaseModel):
    address: str = Field(min_length=1, max_length=300)

    @field_validator("address")
    @classmethod
    def address_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Address must not be blank.")
        return value


def load_labels() -> pd.DataFrame:
    """Load label records or raise an HTTP error with a safe message."""
    if not LABELS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="data/labels.csv was not found.",
        )

    try:
        return pd.read_csv(LABELS_FILE).fillna("")
    except Exception as exc:
        logger.exception("Could not read labels CSV")
        raise HTTPException(
            status_code=500,
            detail="Could not read the product labels CSV.",
        ) from exc


@app.get("/")
def home():
    return {
        "message": "Welcome to LabelGuard AI API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/products")
def get_products():
    df = load_labels()
    return {
        "count": len(df),
        "columns": list(df.columns),
        "records": df.to_dict(orient="records"),
    }


@app.post("/api/change-impact")
def change_impact(request: ChangeImpactRequest):
    labels = load_labels()

    try:
        change = {
            "product": request.product,
            "changed_field": request.changed_field,
        }
        result = find_affected_labels(change, labels)
        records = result.fillna("").to_dict(orient="records")

        return {
            "status": "success",
            "product": request.product,
            "changed_field": request.changed_field,
            "affected_count": len(records),
            "affected_labels": records,
        }
    except KeyError as exc:
        logger.exception("Required data missing during change-impact analysis")
        raise HTTPException(
            status_code=400,
            detail=f"Required CSV column or input field is missing: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("Change-impact analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Change-impact analysis failed. Check the backend terminal.",
        ) from exc


@app.post("/api/compliance-risk")
def compliance_risk(request: LabelRiskRequest):
    try:
        label = request.model_dump()
        findings, total_checks = check_label(label)
        return {
            "status": "success",
            "total_checks": total_checks,
            "finding_count": len(findings),
            "findings": findings,
            "result_type": "prototype required-field check",
        }
    except Exception as exc:
        logger.exception("Required-field check failed")
        raise HTTPException(
            status_code=500,
            detail="The required-field check failed.",
        ) from exc


@app.post("/api/ai-draft")
def ai_draft(request: DraftRequest):
    try:
        retrieved, draft = run_rag(request.query, k=request.k)
        return {
            "status": "success",
            "query": request.query,
            "retrieved_count": len(retrieved),
            "references": retrieved,
            "draft": draft,
            "note": (
                "Demo retrieval and template-based drafting; "
                "review all content independently."
            ),
        }
    except Exception as exc:
        logger.exception("RAG drafting failed")
        raise HTTPException(
            status_code=500,
            detail=(
                "RAG drafting failed. Check the backend terminal for "
                "model, dependency, or reference-file errors."
            ),
        ) from exc


@app.post("/api/artwork/create")
def create_artwork(request: ArtworkRequest):
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        output_path = DATA_DIR / "api_generated_label.png"
        create_label(output_path, request.address)

        if not output_path.is_file():
            raise HTTPException(
                status_code=500,
                detail="The artwork engine did not create the expected file.",
            )

        return {
            "status": "success",
            "image_path": str(output_path.relative_to(PROJECT_ROOT)),
            "note": (
                "Synthetic demo artwork only; not for clinical or commercial use."
            ),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Artwork generation failed")
        raise HTTPException(
            status_code=500,
            detail="Artwork generation failed. Check the backend terminal.",
        ) from exc
