
from pathlib import Path
import streamlit as st
import pandas as pd

from engines.change_impact import find_affected_labels
from engines.compliance_risk import check_label

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

st.set_page_config(
    page_title="LabelGuard AI",
    page_icon="✦",
    layout="wide"
)

# ---------- Styling ----------
st.markdown("""
<style>
.stApp {
    background: #f1f6ff;
    color: #172554;
}
[data-testid="stSidebar"] {
    background: #102c63;
}
[data-testid="stSidebar"] * {
    color: white !important;
}
[data-testid="stMetric"] {
    background: white;
    border: 1px solid #dce7fa;
    padding: 16px;
    border-radius: 12px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: white;
    border: 1px solid #dce7fa;
    border-radius: 12px;
    padding: 14px;
}
h1, h2, h3 {
    color: #173775;
}
</style>
""", unsafe_allow_html=True)

# ---------- Sidebar ----------
st.sidebar.markdown("# ✦ LabelGuard AI")
st.sidebar.caption("Medical Device Labeling Platform")
st.sidebar.divider()

page = st.sidebar.radio(
    "NAVIGATION",
    [
        "Dashboard",
        "Change Impact",
        "Compliance Risk",
        "Artwork Validation",
        "GenAI + RAG"
    ]
)

st.sidebar.divider()
st.sidebar.caption("Prototype • Demo environment")

# ---------- Shared data ----------
labels_path = DATA / "labels.csv"

if labels_path.exists():
    labels = pd.read_csv(labels_path)
else:
    st.error("data/labels.csv not found.")
    st.stop()

change = {
    "change_id": "CR-001",
    "product": "Device X100",
    "changed_field": "manufacturer_address"
}

affected = find_affected_labels(change, labels)

def section_title(title, subtitle=None):
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

def show_artwork():
    old = DATA / "old_label.png"
    new = DATA / "new_label.png"
    diff = DATA / "highlighted_changes.png"

    c1, c2, c3 = st.columns(3)

    for col, path, title in [
        (c1, old, "Old Artwork"),
        (c2, new, "New Artwork"),
        (c3, diff, "Detected Difference")
    ]:
        with col:
            st.markdown(f"**{title}**")
            if path.exists():
                st.image(str(path), use_container_width=True)
            else:
                st.info(f"{path.name} not found")

# ---------- Dashboard ----------
if page == "Dashboard":
    st.title("Welcome to LabelGuard AI 👋")
    st.caption(
        "AI-assisted medical device labeling, change impact "
        "analysis and compliance review."
    )

    a, b, c, d, e = st.columns(5)

    a.metric("Demo Products", labels["product"].nunique())
    b.metric("Demo Change Requests", 1)
    c.metric("Affected Labels", len(affected))
    d.metric("Markets in Dataset", labels["market"].nunique())
    e.metric("Compliance Findings", "Test below")

    st.info(
        "Demonstration data only. These counts describe the "
        "current sample dataset, not a production system."
    )

    left, right = st.columns([1.05, 1])

    with left:
        with st.container(border=True):
            section_title(
                "Change Impact Analysis",
                "CR-001 · Manufacturer address change · Device X100"
            )
            st.metric("Affected labels", len(affected))
            if not affected.empty:
                st.dataframe(
                    affected,
                    use_container_width=True,
                    hide_index=True
                )

        with st.container(border=True):
            section_title("Compliance Risk Engine")
            demo_label = {
                "product_name": "Device X100",
                "manufacturer": "",
                "intended_use": "Demo intended use"
            }
            findings, total_checks = check_label(demo_label)
            st.metric("Demo fields checked", total_checks)
            st.metric("Missing-field findings", len(findings))

            if findings:
                for item in findings:
                    st.warning(
                        f"{item['risk']}: {item['finding']}"
                    )
            else:
                st.success("No missing demo fields detected.")

    with right:
        with st.container(border=True):
            section_title(
                "Artwork Validation",
                "Old vs updated label artwork"
            )
            show_artwork()

        with st.container(border=True):
            section_title("GenAI + RAG")
            draft_path = DATA / "label_draft.txt"

            if draft_path.exists():
                draft = draft_path.read_text(encoding="utf-8")
                st.success("Reference retrieval completed")
                st.caption("Draft status: Human review required")
                st.text_area(
                    "Label draft preview",
                    value=draft,
                    height=180,
                    disabled=True
                )
            else:
                st.info("Run engines/genai_labeling.py first.")

# ---------- Change Impact ----------
elif page == "Change Impact":
    st.title("Smart Change Impact Analysis")
    st.caption("Identify labels affected by a product change.")

    product = st.selectbox(
        "Select product",
        sorted(labels["product"].unique())
    )
    changed_field = st.selectbox(
        "Changed field",
        [
            "manufacturer_address",
            "product_name",
            "importer_address"
        ]
    )

    if st.button("Analyse Impact", type="primary"):
        request = {
            "change_id": "CR-DEMO",
            "product": product,
            "changed_field": changed_field
        }
        result = find_affected_labels(request, labels)
        st.metric("Affected labels", len(result))

        if result.empty:
            st.info("No matching labels found in this demo dataset.")
        else:
            st.dataframe(
                result,
                use_container_width=True,
                hide_index=True
            )

# ---------- Compliance ----------
elif page == "Compliance Risk":
    st.title("Compliance Risk Checker")
    st.caption("Illustrative required-field checks; not regulatory approval.")

    product_name = st.text_input("Product name", "Device X100")
    manufacturer = st.text_input("Manufacturer", "")
    intended_use = st.text_area("Intended use", "Demo intended use")

    if st.button("Check Label", type="primary"):
        findings, total_checks = check_label({
            "product_name": product_name,
            "manufacturer": manufacturer,
            "intended_use": intended_use
        })

        x, y = st.columns(2)
        x.metric("Fields checked", total_checks)
        y.metric("Findings", len(findings))

        if findings:
            st.error("Review required")
            st.dataframe(
                pd.DataFrame(findings),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("No missing demo-required fields.")

# ---------- Artwork ----------
elif page == "Artwork Validation":
    st.title("Computer Vision Artwork Validator")
    st.caption("Pixel-level comparison of the sample artwork.")
    show_artwork()
    st.warning(
        "This demo detects image differences. It does not establish "
        "regulatory compliance or barcode correctness."
    )

# ---------- GenAI / RAG ----------
elif page == "GenAI + RAG":
    st.title("GenAI + RAG Label Authoring")
    st.caption("Retrieved source content and draft preview.")

    draft_path = DATA / "label_draft.txt"

    if draft_path.exists():
        st.text_area(
            "Draft preview",
            draft_path.read_text(encoding="utf-8"),
            height=300,
            disabled=True
        )
    else:
        st.info("Run python engines/genai_labeling.py first.")
