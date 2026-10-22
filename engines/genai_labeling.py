
from pathlib import Path

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent
REFERENCE_FILE = BASE_DIR / "data" / "reference.txt"


def load_chunks():
    text = REFERENCE_FILE.read_text(encoding="utf-8")
    return [
        part.strip()
        for part in text.split("\n\n")
        if part.strip()
    ]


def retrieve_references(query, chunks, model, index, k=3):
    query_vector = model.encode(
        [query], normalize_embeddings=True
    ).astype("float32")

    _, positions = index.search(
        query_vector, min(k, len(chunks))
    )

    return [chunks[i] for i in positions[0] if i >= 0]


def generate_demo_draft(references):
    # Template-based draft for the first prototype.
    # This is not LLM-generated yet.
    context = "\n\n".join(references)

    return f"""
LABEL DRAFT — DEVICE X100
Status: DRAFT — HUMAN REVIEW REQUIRED

Retrieved reference information:
{context}

Product name: Device X100
Manufacturer: Example Medical Ltd.
Intended use: NEEDS REVIEW before real-world use.

Warning:
This is a fictional demonstration draft, not an approved
medical-device label. Verify all fields against applicable
requirements before any real use.
"""


if __name__ == "__main__":
    chunks = load_chunks()

    if not chunks:
        raise ValueError("No reference text found.")

    print("Loading embedding model...")
    model = SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )

    vectors = model.encode(
        chunks, normalize_embeddings=True
    ).astype("float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    query = "What is the product name and manufacturer?"
    retrieved = retrieve_references(
        query, chunks, model, index
    )

    print("\nRAG RETRIEVAL RESULTS")
    print("=" * 45)

    for number, chunk in enumerate(retrieved, start=1):
        print(f"\nSource chunk {number}:")
        print(chunk)

    draft = generate_demo_draft(retrieved)

    output_file = BASE_DIR / "data" / "label_draft.txt"
    output_file.write_text(draft, encoding="utf-8")

    print("\nDraft saved to:", output_file)
    print("\n", draft)
