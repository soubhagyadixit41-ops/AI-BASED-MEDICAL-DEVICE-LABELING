
from pathlib import Path

import pandas as pd
import streamlit as st

from engines.change_impact import find_affected_labels
from engines.compliance_risk import check_label
from engines.genai_labeling import run_rag


# ============================================================
# CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="LabelGuard AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LABELS_FILE = DATA_DIR / "labels.csv"


# ============================================================
# PROFESSIONAL UI + HIGH-CONTRAST STYLING
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --navy: #132B59;
    --blue: #2563EB;
    --background: #F4F7FC;
    --border: #DCE5F3;
    --muted: #526581;
}

.stApp {
    background: var(--background);
    color: #172554;
    font-family: 'Inter', sans-serif;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #17366F 0%, #0A1B3D 100%);
}

[data-testid="stSidebar"] * {
    color: #FFFFFF;
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,.20);
}

/* Headings and general text */
h1, h2, h3, h4 {
    color: var(--navy) !important;
    letter-spacing: -0.3px;
}

h1 {
    font-weight: 800 !important;
}

p, li {
    color: #243B61;
}

/* Metrics */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 17px;
    box-shadow: 0 4px 14px rgba(19,43,89,.04);
}

[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] p {
    color: #526581 !important;
    font-size: 12px !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricValue"] div {
    color: var(--navy) !important;
    font-weight: 800 !important;
}

/* Containers */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 12px;
}

/* Information banner */
.info-banner {
    background: #E4EEFF;
    color: #1D4ED8 !important;
    border: 1px solid #D0E0FF;
    border-radius: 10px;
    padding: 14px 16px;
    margin: 14px 0 24px;
}

/* Make form labels readable */
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
.stTextInput label,
.stTextArea label,
.stSelectbox label,
.stSlider label,
.stNumberInput label,
.stDateInput label,
.stRadio label,
.stCheckbox label {
    color: #243B61 !important;
    opacity: 1 !important;
    font-weight: 600 !important;
}

/* Text inputs and text areas */
.stTextInput input,
.stTextArea textarea,
.stNumberInput input,
[data-testid="stDateInput"] input {
    background-color: #FFFFFF !important;
    color: #172554 !important;
    -webkit-text-fill-color: #172554 !important;
    border: 1px solid #B9C8DD !important;
    border-radius: 8px !important;
    caret-color: #172554 !important;
}

/* Placeholder text */
.stTextInput input::placeholder,
.stTextArea textarea::placeholder {
    color: #64748B !important;
    -webkit-text-fill-color: #64748B !important;
    opacity: 1 !important;
}

/* Dropdown controls */
.stSelectbox div[data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    color: #172554 !important;
    border-color: #B9C8DD !important;
}

.stSelectbox div[data-baseweb="select"] span {
    color: #172554 !important;
}

/* Slider labels and values */
[data-testid="stSlider"] p,
[data-testid="stSlider"] label {
    color: #243B61 !important;
    opacity: 1 !important;
}

/* Buttons */
div.stButton > button,
div.stDownloadButton > button {
    border-radius: 9px;
    font-weight: 600;
    min-height: 42px;
    transition: all .15s ease;
}

div.stButton > button[kind="primary"] {
    background: var(--blue);
    border: 1px solid var(--blue);
    color: #FFFFFF !important;
}

div.stButton > button[kind="primary"] p {
    color: #FFFFFF !important;
}

div.stButton > button:hover,
div.stDownloadButton > button:hover {
    border-color: var(--blue);
    color: var(--blue) !important;
}

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 10px;
}

/* Tables */
div[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
}

/* Expanders / reference chunks */
[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid var(--border);
    border-radius: 10px;
    margin-bottom: 10px;
    overflow: hidden;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #172554 !important;
    font-weight: 600 !important;
}

/* Draft preview and code blocks */
[data-testid="stCode"] {
    border: 1px solid #2B3A55;
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stCode"] pre {
    white-space: pre-wrap !important;
    overflow-wrap: anywhere !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
}

/* Captions and footer */
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] p {
    color: #526581 !important;
}

hr {
    border-color: var(--border);
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# LOAD SAMPLE DATA
# ============================================================

@st.cache_data
def load_labels():
    if not LABELS_FILE.exists():
        return pd.DataFrame(
            columns=[
                "label_id",
                "product",
                "market",
                "language",
                "dependent_fields",
                "version",
            ]
        )

    return pd.read_csv(LABELS_FILE)


labels = load_labels()

products = (
    sorted(labels["product"].dropna().unique().tolist())
    if not labels.empty and "product" in labels.columns
    else []
)

default_product = products[0] if products else "Device X100"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def analyze_change(product, changed_field):
    """Run the existing change-impact engine."""
    if labels.empty:
        return pd.DataFrame()

    return find_affected_labels(
        {
            "change_id": "CR-001",
            "product": product,
            "changed_field": changed_field,
        },
        labels,
    )


def display_artwork(title, filename):
    """Display sample artwork if available."""
    image_path = DATA_DIR / filename

    st.markdown(f"**{title}**")

    if image_path.exists():
        st.image(str(image_path), width="stretch")
    else:
        st.warning(f"Missing file: data/{filename}")


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## ✦ LabelGuard AI")
    st.caption("Medical Device Labeling Platform")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Dashboard",
            "Change Impact",
            "Compliance Risk",
            "Artwork Validation",
            "GenAI + RAG",
    ],
    )

    st.divider()
    st.caption("Prototype · Demo environment")


# ============================================================
# PAGE HEADER
# ============================================================

st.caption("MEDICAL DEVICE LABELING INTELLIGENCE")
st.title(page)

st.write(
    "AI-assisted labeling, change impact analysis and compliance review."
)


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    affected = analyze_change(
        default_product,
        "manufacturer_address",
    )

    demo_label = {
        "product_name": "Device X100",
        "manufacturer": "",
        "intended_use": "Demonstration only",
    }

    findings, _ = check_label(demo_label)

    market_count = (
        labels["market"].nunique()
        if not labels.empty and "market" in labels.columns
        else 0
    )

    metric_columns = st.columns(5)

    metric_values = [
        ("Products in Dataset", len(products)),
        ("Demo Change Requests", 1),
        ("Affected Labels", len(affected)),
        ("Markets in Dataset", market_count),
        ("Missing Required Fields", len(findings)),
    ]

    for column, (label, value) in zip(
        metric_columns, metric_values
    ):
        column.metric(label, value)

    st.markdown(
        '<div class="info-banner">Demonstration data only. '
        'Figures are calculated from the sample dataset and demo checks.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 1])

    with left:
        st.subheader("Change Impact Analysis")
        st.caption(
            f"CR-001 · Manufacturer address change · {default_product}"
        )

        with st.container(border=True):
            st.metric("Affected label records", len(affected))

            if affected.empty:
                st.info("No affected labels found.")
            else:
                st.dataframe(
                    affected,
                    width="stretch",
                    hide_index=True,
                )

    with right:
        st.subheader("Compliance Risk Engine")

        with st.container(border=True):
            if findings:
                st.warning(
                    f"{len(findings)} missing required field(s) detected."
                )

                for item in findings:
                    st.markdown(
                        f"**{item['risk']}** — {item['finding']}"
                    )
            else:
                st.success("No missing required fields detected.")

            st.caption(
                "Demo checks only; this is not a complete regulatory assessment."
            )

    st.subheader("Artwork Validation")

    with st.container(border=True):
        image_columns = st.columns(3)

        artwork_items = [
            ("Old Artwork", "old_label.png"),
            ("New Artwork", "new_label.png"),
            ("Highlighted Differences", "highlighted_changes.png"),
        ]

        for column, (title, filename) in zip(
            image_columns, artwork_items
        ):
            with column:
                display_artwork(title, filename)

    st.subheader("GenAI + RAG")

    with st.container(border=True):
        draft_path = DATA_DIR / "label_draft.txt"

        if draft_path.exists():
            st.success("Saved draft preview available.")

            with st.expander("View saved draft"):
                st.code(
                    draft_path.read_text(encoding="utf-8"),
                    language="text",
                )
        else:
            st.info(
                "No saved draft yet. Open GenAI + RAG to generate one."
            )


# ============================================================
# CHANGE IMPACT
# ============================================================

elif page == "Change Impact":

    st.subheader("Change Impact Analysis")

    st.write(
        "Select a product and changed field to identify dependent labels."
    )

    product = st.selectbox(
        "Product",
        products if products else ["Device X100"],
    )

    changed_field = st.selectbox(
        "Changed field",
        [
            "manufacturer_address",
            "product_name",
            "importer_address",
        ],
    )

    if st.button("Analyze Impact", type="primary"):

        result = analyze_change(product, changed_field)

        st.metric("Affected Labels", len(result))

        if result.empty:
            st.info("No matching labels found.")
        else:
            st.success(
                f"{len(result)} affected label record(s) identified."
            )

            st.dataframe(
                result,
                width="stretch",
                hide_index=True,
            )


# ============================================================
# COMPLIANCE RISK
# ============================================================

elif page == "Compliance Risk":

    st.subheader("Required Field Review")

    st.write(
        "Enter sample label information to check the required fields."
    )

    product_name = st.text_input(
        "Product name",
        value="Device X100",
    )

    manufacturer = st.text_input(
        "Manufacturer",
        value="",
        placeholder="Enter manufacturer name",
    )

    intended_use = st.text_area(
        "Intended use",
        value="Demonstration only",
        height=120,
    )

    if st.button("Check Required Fields", type="primary"):

        result, total_checks = check_label(
            {
                "product_name": product_name,
                "manufacturer": manufacturer,
                "intended_use": intended_use,
            }
        )

        col1, col2 = st.columns(2)
        col1.metric("Fields Checked", total_checks)
        col2.metric("Findings", len(result))

        if result:
            st.warning("Review the detected findings.")

            st.dataframe(
                pd.DataFrame(result),
                width="stretch",
                hide_index=True,
            )
        else:
            st.success("No missing required fields detected.")

    st.info(
        "This demonstration checks only a small set of fields. "
        "It does not establish regulatory compliance."
    )


# ============================================================
# ARTWORK VALIDATION
# ============================================================

elif page == "Artwork Validation":

    st.subheader("Label Artwork Comparison")

    st.write(
        "Compare the original artwork, updated artwork and highlighted differences."
    )

    image_columns = st.columns(3)

    artwork_items = [
        ("Old Artwork", "old_label.png"),
        ("New Artwork", "new_label.png"),
        ("Highlighted Differences", "highlighted_changes.png"),
    ]

    for column, (title, filename) in zip(
        image_columns, artwork_items
    ):
        with column:
            display_artwork(title, filename)

    mask_path = DATA_DIR / "difference_mask.png"

    if mask_path.exists():
        with st.expander("View Difference Mask"):
            st.image(str(mask_path), width="stretch")

    st.info(
        "This prototype uses image-difference analysis. "
        "It does not independently verify regulatory correctness."
    )


# ============================================================
# GENAI + RAG
# ============================================================

elif page == "GenAI + RAG":

    st.subheader("Reference Retrieval and Draft Generation")

    st.write(
        "Search the supplied demonstration reference, inspect retrieved "
        "chunks, and preview a template-based draft."
    )

    query = st.text_input(
        "What information do you want to find?",
        value="What is the product name and manufacturer?",
    )

    k = st.slider(
        "Number of reference chunks",
        min_value=1,
        max_value=5,
        value=3,
    )

    if st.button(
        "Retrieve References and Generate Draft",
        type="primary",
    ):

        try:
            with st.spinner(
                "Loading embedding model and retrieving references..."
            ):
                retrieved, draft = run_rag(query, k=k)

            st.success(
                f"Retrieved {len(retrieved)} reference chunk(s)."
            )

            st.subheader("Retrieved Reference Chunks")

            if retrieved:
                for number, item in enumerate(
                    retrieved, start=1
                ):
                    with st.expander(
                        f"Source chunk {number}",
                        expanded=True,
                    ):
                        st.write(item["text"])
                        st.caption(
                            f"Similarity score: {item['score']:.4f}"
                        )
            else:
                st.info("No reference chunks were retrieved.")

            st.subheader("Draft Preview")

            st.code(draft, language="text")

            st.download_button(
                label="Download Draft",
                data=draft,
                file_name="label_draft.txt",
                mime="text/plain",
            )

        except Exception as error:
            st.error(f"RAG workflow failed: {error}")

    st.info(
        "The current draft generator is template-based, not a live LLM. "
        "The retrieved reference is demonstration material and must be "
        "independently reviewed."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "LabelGuard AI · Educational prototype · Not for clinical use. "
    "Qualified regulatory review is required."
)
