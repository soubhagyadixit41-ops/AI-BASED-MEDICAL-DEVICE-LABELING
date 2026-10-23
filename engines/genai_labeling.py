
from pathlib import Path

import faiss
from sentence_transformers import SentenceTransformer


# ==================================================
# LABELGUARD AI - RAG ENGINE
# ==================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

REFERENCE_FILE = DATA_DIR / "reference.txt"
OUTPUT_FILE = DATA_DIR / "label_draft.txt"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_TOP_K = 3


# ==================================================
# 1. LOAD REFERENCE TEXT
# ==================================================

def load_chunks():
    """Load the reference document and split it into chunks."""

    if not REFERENCE_FILE.exists():
        raise FileNotFoundError(
            f"Reference file not found: {REFERENCE_FILE}"
        )

    text = REFERENCE_FILE.read_text(encoding="utf-8")

    chunks = [
        part.strip()
        for part in text.split("\n\n")
        if part.strip()
    ]

    if not chunks:
        raise ValueError("No reference text found.")

    return chunks


# ==================================================
# 2. BUILD EMBEDDINGS AND FAISS INDEX
# ==================================================

def build_search_index(chunks):
    """Create embeddings and a FAISS similarity-search index."""

    if not chunks:
        raise ValueError("Cannot create an index without text chunks.")

    model = SentenceTransformer(MODEL_NAME)

    vectors = model.encode(
        chunks,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    return model, index


# ==================================================
# 3. RETRIEVE RELEVANT REFERENCE CHUNKS
# ==================================================

def retrieve_references(
    query,
    chunks,
    model,
    index,
    k=DEFAULT_TOP_K,
):
    """Retrieve relevant text chunks ranked by similarity."""

    if not isinstance(query, str) or not query.strip():
        raise ValueError("Please enter a search query.")

    if not chunks:
        return []

    k = max(1, min(int(k), len(chunks)))

    query_vector = model.encode(
        [query.strip()],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    scores, positions = index.search(query_vector, k)

    retrieved = []

    for score, position in zip(scores[0], positions[0]):
        if position < 0:
            continue

        retrieved.append({
            "text": chunks[int(position)],
            "score": float(score),
            "source_number": int(position) + 1,
        })

    return retrieved


# ==================================================
# 4. GENERATE DEMONSTRATION DRAFT
# ==================================================

def generate_demo_draft(query, references):
    """
    Create a template-based draft from retrieved information.

    This function does not call a live LLM.
    """

    reference_text = "\n\n".join(
        item["text"] for item in references
    )

    if not reference_text:
        reference_text = "No reference information retrieved."

    return f"""LABELGUARD AI
LABEL DRAFT — DEVICE X100

Status: DRAFT — HUMAN REVIEW REQUIRED

User query:
{query}

RETRIEVED REFERENCE INFORMATION
{reference_text}

DEMONSTRATION LABEL FIELDS

Product name: Device X100
Manufacturer: Example Medical Ltd.
Intended use: NEEDS REVIEW before real-world use.

REVIEW CHECKLIST
- Verify the product name and manufacturer.
- Confirm the intended use against approved documentation.
- Verify applicable market-specific requirements.
- Review warnings, symbols, translations, and required fields.
- Confirm information with qualified regulatory reviewers.

IMPORTANT DISCLAIMER
This is a fictional demonstration draft generated using a
template. It is not an approved medical-device label and does
not establish regulatory compliance. It is not intended for
clinical or commercial use without appropriate independent review.
"""


# ==================================================
# 5. COMPLETE WORKFLOW FOR STREAMLIT
# ==================================================

def run_rag(query, k=DEFAULT_TOP_K):
    """
    Retrieve relevant reference chunks and generate a draft.

    Returns:
        retrieved: list of dictionaries containing text, score,
                   and source_number.
        draft: template-based draft text.
    """

    chunks = load_chunks()

    model, index = build_search_index(chunks)

    retrieved = retrieve_references(
        query=query,
        chunks=chunks,
        model=model,
        index=index,
        k=k,
    )

    draft = generate_demo_draft(query, retrieved)

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(draft, encoding="utf-8")

    return retrieved, draft


# ==================================================
# 6. RUN DIRECTLY FROM THE TERMINAL
# ==================================================

if __name__ == "__main__":
    query = "What is the product name and manufacturer?"

    print("Loading reference documents and embedding model...")

    retrieved, draft = run_rag(query)

    print("\n" + "=" * 50)
    print("LABELGUARD AI - RAG RETRIEVAL RESULTS")
    print("=" * 50)

    for number, item in enumerate(retrieved, start=1):
        print(f"\nSource chunk {number}")
        print(f"Similarity score: {item['score']:.4f}")
        print(item["text"])

    print("\n" + "=" * 50)
    print("DEMONSTRATION DRAFT")
    print("=" * 50)
    print(draft)

    print(f"\nDraft saved to: {OUTPUT_FILE}")
