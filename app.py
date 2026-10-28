from pathlib import Path
import html
import pandas as pd
import streamlit as st
import requests

from engines.change_impact import find_affected_labels
from engines.compliance_risk import check_label

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="LabelGuard AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LABELS_FILE = DATA_DIR / "labels.csv"
OLD_ARTWORK = DATA_DIR / "old_label.png"
NEW_ARTWORK = DATA_DIR / "new_label.png"
HIGHLIGHTED_ARTWORK = DATA_DIR / "highlighted_changes.png"
DIFFERENCE_MASK = DATA_DIR / "difference_mask.png"
REFERENCE_FILE = DATA_DIR / "reference.txt"
DRAFT_FILE = DATA_DIR / "label_draft.txt"

# =========================================================
# DATA
# =========================================================
@st.cache_data
def load_labels():
    if LABELS_FILE.exists():
        try:
            return pd.read_csv(LABELS_FILE)
        except Exception:
            pass
    return pd.DataFrame(
        columns=[
            "label_id", "product", "market", "language",
            "dependent_fields", "version"
        ]
    )

labels = load_labels()

# =========================================================
# STYLING
# =========================================================
st.markdown(
    """
    <style>
    :root {
        --navy: #132b4d;
        --navy-2: #1d416f;
        --blue: #2864ed;
        --blue-soft: #eaf1ff;
        --ink: #183252;
        --muted: #627792;
        --line: #dce5f1;
        --page: #f4f7fc;
        --white: #ffffff;
    }
    .stApp {
        background:
          radial-gradient(circle at 92% 0%, rgba(40,100,237,.07), transparent 25%),
          var(--page);
        color: var(--ink);
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 1500px;
        padding-top: 1.15rem;
        padding-bottom: 2.5rem;
        padding-left: clamp(1.25rem, 3vw, 2.8rem);
        padding-right: clamp(1.25rem, 3vw, 2.8rem);
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #204779 0%, #102747 100%);
        min-width: 265px;
        width: 265px;
        border-right: 1px solid rgba(255,255,255,.1);
    }
    [data-testid="stSidebar"] * { color: #f8fbff; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #d8e5f8;
    }
    [data-testid="stSidebar"] .stRadio label {
        font-size: 14px !important;
        font-weight: 550;
    }
    .brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: rgba(255,255,255,.14);
        border: 1px solid rgba(255,255,255,.22);
        font-size: 23px;
        margin-bottom: 10px;
    }
    .brand-title {
        font-size: 28px;
        font-weight: 900;
        letter-spacing: -1px;
        line-height: 1.12;
        color: #fff;
        overflow-wrap: anywhere;
        margin: 0 0 7px 0;
    }
    .brand-subtitle {
        color: #d8e5f8;
        font-size: 12px;
        line-height: 1.5;
        margin-bottom: 18px;
    }
    .eyebrow {
        color: #5f7694;
        font-size: 11px;
        letter-spacing: 2px;
        font-weight: 800;
        text-transform: uppercase;
        margin-bottom: 8px;
    }
    .hero-title {
        font-size: clamp(30px, 3.2vw, 43px);
        line-height: 1.1;
        letter-spacing: -1.4px;
        color: #142f53;
        font-weight: 900;
        margin: 0;
    }
    .hero-copy {
        color: #627792;
        font-size: 15px;
        margin-top: 10px;
        margin-bottom: 20px;
        max-width: 760px;
    }
    .metric-card {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 18px 19px;
        min-height: 125px;
        box-shadow: 0 5px 20px rgba(22,48,83,.045);
    }
    .metric-label {
        color: #61758f;
        font-size: 12px;
        font-weight: 650;
        margin-bottom: 10px;
    }
    .metric-value {
        color: #17365e;
        font-size: clamp(27px, 2.2vw, 35px);
        line-height: 1;
        font-weight: 850;
        letter-spacing: -1px;
    }
    .metric-caption {
        color: #7a8da5;
        font-size: 11px;
        margin-top: 11px;
    }
    .panel {
        background: #fff;
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 18px 20px;
        box-shadow: 0 5px 20px rgba(22,48,83,.035);
    }
    .info-banner {
        background: #eaf1ff;
        border: 1px solid #cfddfb;
        color: #204f91;
        border-radius: 12px;
        padding: 13px 16px;
        font-size: 13px;
        margin: 16px 0 22px 0;
    }
    .warning-banner {
        background: #fff5d9;
        border: 1px solid #f0dda0;
        color: #72510a;
        border-radius: 12px;
        padding: 13px 16px;
        font-size: 13px;
    }
    .footer-text {
        color: #7b8da5;
        font-size: 11px;
        margin-top: 32px;
        border-top: 1px solid #e0e7f1;
        padding-top: 15px;
    }
    h1, h2, h3, h4 { color: #17365e; }
    .stTextInput label, .stTextArea label, .stSelectbox label,
    .stSlider label, .stNumberInput label, .stRadio label {
        color: #183252 !important;
        font-weight: 650 !important;
    }
    .stTextInput input, .stTextArea textarea {
        background: #fff !important;
        color: #183252 !important;
        border: 1px solid #cbd8e9 !important;
        border-radius: 10px !important;
    }
    [data-baseweb="select"] > div {
        background: #fff !important;
        color: #183252 !important;
        border-color: #cbd8e9 !important;
        border-radius: 10px !important;
    }
    div.stButton > button, div.stDownloadButton > button {
        border-radius: 10px;
        font-weight: 700;
        min-height: 42px;
        border: 1px solid #d3deef;
        transition: transform .12s ease, box-shadow .12s ease;
    }
    div.stButton > button[kind="primary"] {
        background: #2864ed;
        color: white;
        border-color: #2864ed;
        box-shadow: 0 5px 14px rgba(40,100,237,.17);
    }
    div.stButton > button:hover {
        border-color: #2864ed;
        transform: translateY(-1px);
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #dce5f1;
        border-radius: 12px;
        overflow: hidden;
    }
    [data-testid="stAlert"] { border-radius: 12px; }
    @media (max-width: 900px) {
        [data-testid="stSidebar"] { min-width: 230px; width: 230px; }
        .brand-title { font-size: 25px; }
    }

    /* High-contrast controls and readable status messages */
    div.stButton > button, div.stDownloadButton > button {
        background: #ffffff !important;
        color: #193968 !important;
        border: 1px solid #cbd8e9 !important;
    }
    div.stButton > button[kind="primary"],
    div.stDownloadButton > button[kind="primary"] {
        background: #2864ed !important;
        color: #ffffff !important;
        border-color: #2864ed !important;
    }
    div.stButton > button:hover, div.stDownloadButton > button:hover {
        background: #edf3ff !important;
        color: #17365e !important;
        border-color: #2864ed !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: #1d50cb !important;
        color: #ffffff !important;
    }
    [data-testid="stAlert"] {
        border-radius: 12px !important;
    }
    [data-testid="stAlert"] p,
    [data-testid="stAlert"] [data-testid="stMarkdownContainer"] {
        color: #243b58 !important;
    }
    [data-testid="stDataFrame"] {
        background: #ffffff !important;
        border: 1px solid #dce5f1 !important;
        border-radius: 12px !important;
    }
    h1, h2, h3, h4 {
        color: #193968 !important;
    }

    .warning-banner {
        background: #fff4d6 !important;
        border: 1px solid #f0d58a !important;
        color: #624600 !important;
    }
    .warning-banner strong { color: #624600 !important; }

    .mini-chart {
        background: #ffffff;
        border: 1px solid #dce5f1;
        border-radius: 14px;
        padding: 16px 18px 12px;
    }
    .bar-row {
        display: grid;
        grid-template-columns: minmax(70px, 100px) 1fr 28px;
        gap: 10px;
        align-items: center;
        margin: 13px 0;
        color: #536d93;
        font-size: 12px;
    }
    .bar-track {
        height: 12px;
        background: #edf2fa;
        border-radius: 99px;
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #2864ed, #65b7f5);
        border-radius: 99px;
    }
    .bar-number {
        color: #193968;
        font-weight: 800;
        text-align: right;
    }


    /* Reference-inspired application shell */
    [data-testid="stSidebar"] {
        min-width: 218px !important;
        width: 218px !important;
        background: linear-gradient(180deg, #153e72 0%, #0d2545 100%) !important;
    }
    [data-testid="stSidebar"] .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .brand-mark {
        width: 34px;
        height: 34px;
        border-radius: 11px;
        font-size: 21px;
    }
    .brand-title { font-size: 25px; letter-spacing: -0.8px; }
    .brand-subtitle { font-size: 11px; }
    .topbar {
        background: rgba(255,255,255,.92);
        border: 1px solid #e1e9f4;
        border-radius: 14px;
        padding: 8px 12px;
        margin-bottom: 18px;
    }
    .welcome-title {
        color: #122e52;
        font-size: clamp(25px, 2.5vw, 34px);
        font-weight: 850;
        letter-spacing: -1px;
        line-height: 1.15;
        margin-bottom: 4px;
    }
    .welcome-subtitle {
        color: #637995;
        font-size: 12px;
        margin-bottom: 15px;
    }
    .metric-card {
        min-height: 98px;
        padding: 15px 15px;
        border-radius: 12px;
        box-shadow: 0 4px 14px rgba(19, 43, 77, .045);
    }
    .metric-label { font-size: 11px; margin-bottom: 7px; }
    .metric-value { font-size: 28px; }
    .metric-caption { font-size: 10px; margin-top: 7px; }
    .dash-panel {
        background: #ffffff;
        border: 1px solid #e0e8f3;
        border-radius: 13px;
        padding: 14px 15px;
        box-shadow: 0 4px 15px rgba(19,43,77,.035);
        margin-bottom: 12px;
    }
    .dash-panel-title {
        font-size: 15px;
        font-weight: 800;
        color: #183a67;
        margin-bottom: 9px;
    }
    .status-pill {
        display: inline-block;
        padding: 4px 8px;
        border-radius: 999px;
        font-size: 10px;
        font-weight: 750;
        white-space: nowrap;
    }
    .pill-blue { background: #e3edff; color: #2356b2; }
    .pill-green { background: #d9f5e7; color: #18744c; }
    .pill-amber { background: #fff0c7; color: #875d00; }
    .pill-red { background: #ffe0e0; color: #a52b2b; }
    .pill-slate { background: #edf1f6; color: #52647b; }
    .workflow {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 5px;
        margin: 13px 0 15px;
    }
    .workflow-step {
        flex: 1;
        min-width: 0;
        text-align: center;
        color: #627792;
        font-size: 10px;
        line-height: 1.25;
    }
    .workflow-dot {
        width: 22px;
        height: 22px;
        margin: 0 auto 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        background: #e6ebf3;
        color: #52647b;
        font-weight: 800;
        border: 2px solid #d6deea;
    }
    .workflow-done .workflow-dot { background: #1a9a68; color: #fff; border-color: #1a9a68; }
    .workflow-active .workflow-dot { background: #2864ed; color: #fff; border-color: #b7ccff; box-shadow: 0 0 0 3px #e7eeff; }
    .compare-card {
        border: 1px solid #dbe5f1;
        background: #fbfdff;
        border-radius: 10px;
        padding: 9px;
        min-height: 110px;
    }
    .compare-label { font-size: 10px; color: #627792; font-weight: 750; margin-bottom: 6px; }
    .compare-text { font-size: 11px; line-height: 1.45; color: #233d5d; }
    .compare-warning {
        background: #fff0f0;
        color: #a52b2b;
        padding: 5px 6px;
        border-radius: 5px;
        font-size: 10px;
        margin-top: 6px;
    }
    .compare-good {
        background: #e3f7ed;
        color: #1b6c49;
        padding: 5px 6px;
        border-radius: 5px;
        font-size: 10px;
        margin-top: 6px;
    }
    .bar-row {
        display: grid;
        grid-template-columns: 72px 1fr 26px;
        gap: 8px;
        align-items: center;
        margin: 11px 0;
        font-size: 11px;
        color: #405976;
    }
    .bar-track { background: #edf2f8; height: 10px; border-radius: 20px; overflow: hidden; }
    .bar-fill { background: linear-gradient(90deg, #25a56f, #58c88f); height: 100%; border-radius: 20px; }
    .bar-number { text-align: right; font-weight: 800; color: #183a67; }
    .alert-row {
        display: flex;
        gap: 8px;
        align-items: flex-start;
        padding: 8px 0;
        border-bottom: 1px solid #edf1f6;
        font-size: 11px;
        line-height: 1.35;
        color: #425a76;
    }
    .alert-row:last-child { border-bottom: 0; }
    .alert-icon { font-size: 14px; }
    .lifecycle {
        display: flex;
        justify-content: space-between;
        gap: 3px;
        margin: 17px 0 10px;
    }
    .life-step { flex: 1; text-align: center; color: #61758f; font-size: 9px; }
    .life-dot {
        width: 19px; height: 19px; margin: 0 auto 5px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        background: #e5eaf1; color: #65758b; font-size: 10px; font-weight: 800;
    }
    .life-done { background: #21986b; color: white; }
    .life-active { background: #2864ed; color: white; box-shadow: 0 0 0 3px #e5edff; }
    .quick-card {
        background: #f8fbff;
        border: 1px solid #e0e8f3;
        border-radius: 11px;
        padding: 12px 10px;
        min-height: 64px;
        color: #24486f;
        font-size: 11px;
        font-weight: 700;
    }
    .quick-icon { font-size: 18px; margin-right: 7px; }
    .mini-table th { background: #f0f5fb; color: #536b86; }
    @media (max-width: 1050px) {
        [data-testid="stSidebar"] { min-width: 200px !important; width: 200px !important; }
        .workflow-step { font-size: 9px; }
    }


    /* Color-rich charts inspired by the reference dashboard */
    .chart-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
        padding: 8px 0 2px;
    }
    .chart-line {
        display: grid;
        grid-template-columns: 62px minmax(80px, 1fr) 25px;
        align-items: center;
        gap: 10px;
        color: #516985;
        font-size: 11px;
    }
    .chart-track {
        height: 12px;
        border-radius: 20px;
        overflow: hidden;
        background: #edf2f8;
        box-shadow: inset 0 1px 2px rgba(16,38,67,.05);
    }
    .chart-fill {
        height: 100%;
        border-radius: 20px;
    }
    .chart-value {
        text-align: right;
        color: #203e65;
        font-size: 11px;
        font-weight: 800;
    }
    .donut-layout {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 18px;
        padding: 10px 0;
    }
    .donut {
        width: 124px;
        height: 124px;
        flex: 0 0 124px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        background: conic-gradient(#24a36b 0 82%, #f4bd38 82% 94%, #e64b52 94% 100%);
        position: relative;
    }
    .donut::before {
        content: "";
        position: absolute;
        inset: 15px;
        background: #fff;
        border-radius: 50%;
    }
    .donut-center {
        position: relative;
        z-index: 1;
        text-align: center;
        color: #183a67;
        font-size: 24px;
        line-height: 1;
        font-weight: 900;
    }
    .donut-center small {
        display: block;
        font-size: 9px;
        color: #72849b;
        font-weight: 650;
        margin-top: 5px;
    }
    .legend-list { display: grid; gap: 9px; }
    .legend-row {
        display: flex;
        align-items: center;
        gap: 7px;
        font-size: 11px;
        color: #526984;
        white-space: nowrap;
    }
    .legend-dot { width: 9px; height: 9px; border-radius: 50%; flex: 0 0 9px; }
    .vertical-bars {
        display: flex;
        align-items: end;
        justify-content: space-around;
        gap: 13px;
        height: 145px;
        padding: 8px 8px 0;
        border-bottom: 1px solid #e0e8f2;
        background: repeating-linear-gradient(to bottom, transparent 0, transparent 35px, #edf2f8 36px, transparent 37px);
    }
    .vbar-wrap { flex: 1; min-width: 0; height: 100%; display: flex; flex-direction: column; justify-content: end; align-items: center; gap: 5px; }
    .vbar-value { color: #536985; font-size: 10px; font-weight: 800; }
    .vbar { width: min(34px, 78%); min-height: 8px; border-radius: 6px 6px 0 0; box-shadow: 0 2px 6px rgba(24,58,103,.12); }
    .vbar-label { color: #536985; font-size: 10px; padding-top: 5px; }
    .risk-strip { display:flex; gap:8px; flex-wrap:wrap; margin: 8px 0 2px; }
    .risk-chip { border-radius: 8px; padding: 7px 10px; font-size: 10px; font-weight: 800; }
    .risk-high { color:#a52b2b; background:#ffe3e3; }
    .risk-medium { color:#895d00; background:#fff0c9; }
    .risk-low { color:#16764c; background:#dff7e9; }
    .color-card-blue { border-top: 3px solid #3478f6; }
    .color-card-green { border-top: 3px solid #22a36b; }
    .color-card-purple { border-top: 3px solid #8b5cf6; }
    .color-card-orange { border-top: 3px solid #f59e0b; }
    .color-card-teal { border-top: 3px solid #0ea5a4; }


    /* Visual polish v2: richer SaaS dashboard */
    .stApp {
        background:
          radial-gradient(ellipse at 88% 2%, rgba(81, 130, 255, .13), transparent 25%),
          radial-gradient(ellipse at 10% 28%, rgba(14, 165, 164, .055), transparent 24%),
          #f3f7fd !important;
    }
    .metric-card {
        position: relative;
        overflow: hidden;
        min-height: 112px;
        border-radius: 15px;
        padding: 17px 17px 15px;
        box-shadow: 0 7px 22px rgba(23, 55, 95, .065);
        transition: transform .18s ease, box-shadow .18s ease;
    }
    .metric-card:after {
        content: "";
        position: absolute;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        right: -28px;
        top: -30px;
        background: rgba(60, 115, 230, .08);
    }
    .metric-label {
        text-transform: uppercase;
        letter-spacing: .55px;
        font-size: 10px;
        font-weight: 800;
    }
    .metric-value { font-size: 31px; position: relative; z-index: 1; }
    .metric-caption { position: relative; z-index: 1; }
    .color-card-blue { border-top: 3px solid #3478f6; background: linear-gradient(135deg,#fff 0%,#f1f6ff 100%); }
    .color-card-green { border-top: 3px solid #21a675; background: linear-gradient(135deg,#fff 0%,#effcf6 100%); }
    .color-card-purple { border-top: 3px solid #8b5cf6; background: linear-gradient(135deg,#fff 0%,#f7f2ff 100%); }
    .color-card-orange { border-top: 3px solid #f59e0b; background: linear-gradient(135deg,#fff 0%,#fff8e9 100%); }
    .color-card-teal { border-top: 3px solid #0ea5a4; background: linear-gradient(135deg,#fff 0%,#ecfbfb 100%); }
    .dash-panel-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 15px;
        letter-spacing: -.2px;
        margin-bottom: 11px;
    }
    .dash-panel-title:before {
        content: "";
        width: 4px;
        height: 17px;
        border-radius: 5px;
        background: linear-gradient(180deg,#3478f6,#8b5cf6);
        display: inline-block;
    }
    .chart-grid { gap: 13px; padding: 12px 2px 6px; }
    .chart-line { grid-template-columns: 65px minmax(80px, 1fr) 24px; font-size: 11px; }
    .chart-track { height: 13px; background: #eaf0f8; }
    .chart-fill { box-shadow: 0 2px 6px rgba(29, 65, 111, .14); }
    .donut {
        width: 138px;
        height: 138px;
        flex-basis: 138px;
        box-shadow: 0 8px 22px rgba(20, 54, 94, .1);
    }
    .donut::before { inset: 17px; box-shadow: inset 0 0 0 1px #edf2f8; }
    .donut-center { font-size: 27px; }
    .legend-row { padding: 5px 0; border-bottom: 1px solid #f0f3f8; }
    .vertical-bars { height: 155px; border-radius: 10px; padding: 10px 10px 0; }
    .vbar { width: min(42px, 78%); }
    .info-banner {
        background: linear-gradient(100deg,#eaf1ff,#f2f6ff);
        box-shadow: 0 3px 10px rgba(40,100,237,.035);
    }
    .dash-panel {
        box-shadow: 0 7px 22px rgba(23,55,95,.045);
        border-radius: 15px;
    }
    .compare-card {
        box-shadow: 0 3px 10px rgba(20,54,94,.035);
        transition: transform .16s ease;
    }
    .compare-warning { background: #fff0f0; border-left: 3px solid #ef5350; }
    .compare-good { background: #e6f9ef; border-left: 3px solid #22a36b; }
    .alert-row { padding: 10px 9px; border-radius: 9px; margin-bottom: 5px; border: 1px solid #edf1f7; background: #fff; }
    .alert-row:nth-of-type(1) { border-left: 3px solid #ef5350; }
    .alert-row:nth-of-type(2) { border-left: 3px solid #f59e0b; }
    .alert-row:nth-of-type(3) { border-left: 3px solid #3b82f6; }
    .lifecycle { background: #f8fbff; border: 1px solid #e4ebf5; border-radius: 12px; padding: 15px 8px 12px; }
    .quick-card { box-shadow: 0 3px 9px rgba(23,55,95,.035); }
    div.stButton > button {
        box-shadow: 0 3px 9px rgba(23,55,95,.045);
        font-size: 12px;
    }
    [data-testid="stDataFrame"] { box-shadow: 0 4px 13px rgba(23,55,95,.035); }


    /* Fill the dashboard columns with aligned, useful panels */
    .dash-panel-title { margin-top: 3px; }
    .alert-row { min-height: 55px; }
    .lifecycle { margin-top: 9px; margin-bottom: 8px; }
    .quick-actions-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
    div[data-testid="stHorizontalBlock"] { align-items: stretch; }


    /* Reference-matched left navigation */
    [data-testid="stSidebar"] {
        min-width: 242px !important;
        width: 242px !important;
        background: linear-gradient(180deg, #173f70 0%, #0d2748 100%) !important;
        border-right: 1px solid rgba(255,255,255,.08);
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 0.75rem; }
    [data-testid="stSidebar"] .block-container {
        padding: 0.65rem 0.85rem 1.25rem;
    }
    .brand-lockup {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 2px 13px;
        min-width: 0;
    }
    .brand-symbol {
        flex: 0 0 38px;
        height: 38px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 11px;
        color: #fff;
        font-size: 23px;
        background: linear-gradient(145deg,#5f9cff,#2864ed);
        box-shadow: 0 5px 14px rgba(0,0,0,.16);
    }
    .brand-title {
        font-size: 23px !important;
        letter-spacing: -.75px;
        line-height: 1.1;
        white-space: nowrap;
        margin: 0;
    }
    .brand-subtitle {
        font-size: 9.5px;
        line-height: 1.3;
        margin-top: 4px;
        color: #d4e3f7;
        white-space: normal;
    }
    .sidebar-divider {
        height: 1px;
        background: rgba(255,255,255,.18);
        margin: 14px 0 18px;
    }
    .sidebar-section-label {
        color: #9db8d9;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1.2px;
        margin: 0 0 10px 2px;
    }
    .sidebar-demo-title {
        color: #fff;
        font-size: 11px;
        font-weight: 850;
        letter-spacing: .4px;
        margin: 0 0 13px 2px;
    }
    .sidebar-note {
        color: #b7cce5;
        font-size: 11px;
        padding: 7px 2px;
    }
    [data-testid="stSidebar"] div.stButton > button {
        border: 0 !important;
        border-radius: 8px !important;
        min-height: 36px;
        height: 36px;
        justify-content: flex-start;
        text-align: left;
        padding: 0 11px;
        margin: 2px 0;
        box-shadow: none !important;
        font-size: 12px;
        font-weight: 600;
        background: transparent !important;
        color: #eaf2ff !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        background: rgba(255,255,255,.10) !important;
        transform: none;
    }
    [data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg,#2864ed,#3979fa) !important;
        color: #fff !important;
        box-shadow: 0 4px 11px rgba(0,0,0,.12) !important;
    }
    [data-testid="stSidebar"] div.stButton > button p {
        font-size: 12px;
        text-align: left;
    }
    .sidebar-divider-bottom { margin-top: 20px; }
    @media (max-width: 900px) {
        [data-testid="stSidebar"] { min-width: 220px !important; width: 220px !important; }
        .brand-title { font-size: 21px !important; }
    }


    [data-testid="stMainBlockContainer"] [data-testid="stTextInput"] input {
        background: #ffffff !important;
        color: #183252 !important;
        border: 1px solid #d4dfef !important;
        border-radius: 10px !important;
    }
    [data-testid="stMainBlockContainer"] [data-baseweb="select"] > div {
        background: #ffffff !important;
        color: #183252 !important;
        border: 1px solid #d4dfef !important;
        border-radius: 10px !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# HELPERS
# =========================================================
def footer():
    st.markdown(
        '<div class="footer-text">✦ LabelGuard AI · Educational prototype · '
        'Not for clinical use. Qualified regulatory review is required.</div>',
        unsafe_allow_html=True,
    )

def metric_card(label, value, caption):
    color_classes = {
        "Total products": "color-card-blue",
        "Affected labels": "color-card-orange",
        "Labels in scope": "color-card-purple",
        "Markets covered": "color-card-teal",
        "Fields to review": "color-card-green",
    }
    icons = {
        "Total products": "▦",
        "Affected labels": "↗",
        "Labels in scope": "▤",
        "Markets covered": "◎",
        "Fields to review": "✓",
    }
    color_class = color_classes.get(label, "color-card-blue")
    icon = icons.get(label, "✦")
    st.markdown(
        f"""
        <div class="metric-card {color_class}">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;">
              <div class="metric-label">{label}</div>
              <div style="width:28px;height:28px;border-radius:9px;background:rgba(52,120,246,.10);color:#3478f6;display:flex;align-items:center;justify-content:center;font-size:17px;font-weight:900;">{icon}</div>
            </div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def page_header(eyebrow, title, description):
    st.markdown(f'<div class="eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-copy">{description}</div>', unsafe_allow_html=True)


def get_affected(product="Device X100", field="manufacturer_address"):
    if labels.empty:
        return pd.DataFrame()

    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/change-impact",
            json={
                "product": product,
                "changed_field": field,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        return pd.DataFrame(data.get("affected_labels", []))

    except requests.RequestException as exc:
        st.error(
            "Could not connect to the LabelGuard AI backend. "
            "Make sure FastAPI is running on port 8000. "
            f"Details: {exc}"
        )
        return pd.DataFrame()


def show_artwork():
    columns = st.columns(3)
    items = [
        ("Previous artwork", OLD_ARTWORK),
        ("Revised artwork", NEW_ARTWORK),
        ("Detected differences", HIGHLIGHTED_ARTWORK),
    ]
    for column, (title, path) in zip(columns, items):
        with column:
            st.markdown(f"**{title}**")
            if path.exists():
                st.image(str(path), use_container_width=True)
            else:
                st.warning(f"Missing file: {path.name}")
    if DIFFERENCE_MASK.exists():
        with st.expander("Inspect difference mask"):
            st.image(str(DIFFERENCE_MASK), use_container_width=True)
    st.caption(
        "Image-difference demonstration only. It does not independently verify "
        "label content or regulatory correctness."
    )

def show_bar_chart(data, x_label, y_label):
    """Render a colorful, theme-independent horizontal bar chart."""
    if data is None or len(data) == 0:
        st.info("No sample records are available for this chart.")
        return
    palette = ["#22a36b", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef5350", "#0ea5a4"]
    pairs = [(str(key), int(value)) for key, value in data.items()]
    max_value = max((value for _, value in pairs), default=1) or 1
    rows = []
    for index, (label, value) in enumerate(pairs):
        width = max(4, int(value / max_value * 100))
        safe_label = html.escape(label)
        color = palette[index % len(palette)]
        rows.append(
            f'<div class="chart-line"><span>{safe_label}</span>'
            f'<div class="chart-track"><div class="chart-fill" style="width:{width}%;background:linear-gradient(90deg,{color},{color}bb);"></div></div>'
            f'<span class="chart-value">{value}</span></div>'
        )
    st.markdown('<div class="chart-grid">' + "".join(rows) + '</div>', unsafe_allow_html=True)

def show_html_table(dataframe):
    """Render a simple light table so browser theme settings cannot make it dark."""
    if dataframe is None or dataframe.empty:
        st.info("No records to display.")
        return
    def esc(value):
        return (str(value).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))
    headers = "".join(
        f'<th style="text-align:left;padding:11px 12px;background:#edf3fb;'
        f'color:#34516f;border-bottom:1px solid #dce5f1;font-size:12px;">{esc(col)}</th>'
        for col in dataframe.columns
    )
    body_rows = []
    for _, row in dataframe.iterrows():
        cells = "".join(
            f'<td style="padding:11px 12px;border-bottom:1px solid #e8eef6;'
            f'color:#203955;font-size:12px;vertical-align:top;">{esc(value)}</td>'
            for value in row.tolist()
        )
        body_rows.append(f'<tr>{cells}</tr>')
    st.markdown(
        '<div style="overflow-x:auto;background:#fff;border:1px solid #dce5f1;'
        'border-radius:12px;"><table style="border-collapse:collapse;width:100%;'
        'background:#fff;"><thead><tr>' + headers + '</tr></thead><tbody>'
        + "".join(body_rows) + '</tbody></table></div>',
        unsafe_allow_html=True,
    )

# =========================================================
# NAVIGATION — SIMPLIFIED TO FIVE CORE AREAS
# =========================================================
PAGES = [
    "Overview",
    "Change Impact",
    "Label Studio",
    "Artwork Review",
    "AI Draft Lab",
]
PAGE_ICONS = {
    "Overview": "⌂",
    "Change Impact": "↗",
    "Label Studio": "▤",
    "Artwork Review": "▧",
    "AI Draft Lab": "✧",
}

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div class="brand-symbol">✦</div>'
        '<div><div class="brand-title">LabelGuard AI</div>'
        '<div class="brand-subtitle">Medical Device Labeling Platform</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section-label">WORKSPACE</div>', unsafe_allow_html=True)
    if "page_navigation" not in st.session_state:
        st.session_state["page_navigation"] = "Overview"

    # Buttons create a compact icon-based navigation rather than radio circles.
    for nav_page in PAGES:
        active = st.session_state["page_navigation"] == nav_page
        icon = PAGE_ICONS[nav_page]
        if st.button(
            f"{icon}    {nav_page}",
            key=f"nav_{nav_page}",
            use_container_width=True,
            type="primary" if active else "secondary",
        ):
            st.session_state["page_navigation"] = nav_page
            st.rerun()

    page = st.session_state["page_navigation"]
    st.markdown('<div class="sidebar-divider sidebar-divider-bottom"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-demo-title">DEMO ENVIRONMENT</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sidebar-note">Sample records only</div>'
        '<div class="sidebar-note">Human review required</div>'
        '<div class="sidebar-note">No live regulatory approval</div>',
        unsafe_allow_html=True,
    )

# =========================================================
# OVERVIEW
# =========================================================
if page == "Overview":
    # Top workspace bar
    top_search, top_view, top_notice = st.columns([5.2, 1.15, 0.8], vertical_alignment="center")
    with top_search:
        st.text_input(
            "Search workspace",
            placeholder="Search product, label ID, change request...",
            label_visibility="collapsed",
            key="overview_search",
        )
    with top_view:
        st.selectbox("Scope", ["Global View", "EU", "India", "US"], label_visibility="collapsed", key="overview_scope")
    with top_notice:
        st.markdown(
            '<div style="text-align:right;color:#637995;font-size:12px;padding-top:8px;">'
            '🔔 <strong>Demo</strong></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:3px;">'
        '<span style="width:9px;height:32px;border-radius:8px;background:linear-gradient(180deg,#3478f6,#8b5cf6);display:inline-block;"></span>'
        '<div class="welcome-title">Welcome back to LabelGuard AI</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="welcome-subtitle">Manage label changes, artwork review, and reference-assisted drafting from one workspace.</div>',
        unsafe_allow_html=True,
    )

    # Use only actual sample dataset-derived metrics; clearly label demo values.
    affected = get_affected()
    demo_findings, total_checks = check_label({
        "product_name": "Device X100",
        "manufacturer": "",
        "intended_use": "Demonstration only",
    })
    product_count = labels["product"].nunique() if not labels.empty and "product" in labels.columns else 0
    market_count = labels["market"].nunique() if not labels.empty and "market" in labels.columns else 0
    language_count = labels["language"].nunique() if not labels.empty and "language" in labels.columns else 0

    metric_cols = st.columns(5)
    metrics = [
        ("Total products", product_count, "Sample dataset"),
        ("Affected labels", len(affected), "CR-001 impact estimate"),
        ("Labels in scope", len(labels), "Sample label records"),
        ("Markets covered", market_count, "Distinct sample markets"),
        ("Fields to review", len(demo_findings), "Demo field check"),
    ]
    for col, item in zip(metric_cols, metrics):
        with col:
            metric_card(*item)

    st.markdown(
        '<div class="info-banner"><strong>Prototype data:</strong> Metrics and alerts are based on local sample records and demonstration rules. '
        'They are not live operational statistics or a regulatory compliance score.</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.03, 1.22], gap="medium")
    with left:
        st.markdown('<div class="dash-panel-title">Recent change requests</div>', unsafe_allow_html=True)
        recent = pd.DataFrame([
            ["CR-001", "Device X100", "Manufacturer address", "EU / India", "Review required", "High"],
            ["CR-002", "Device X200", "Product name", "EU", "Draft", "Medium"],
            ["CR-003", "Device X100", "Importer address", "India", "Needs review", "Medium"],
        ], columns=["CR ID", "Product", "Change type", "Markets", "Status", "Demo risk"])
        # Show only requests grounded in available sample products where possible.
        if not labels.empty and "product" in labels.columns:
            valid_products = set(labels["product"].dropna().astype(str))
            recent = recent[recent["Product"].isin(valid_products)]
        show_html_table(recent)

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="dash-panel-title">Compliance overview</div>', unsafe_allow_html=True)
        total_demo = max(1, len(labels))
        needs_review = min(total_demo, max(1, len(demo_findings)))
        compliant_demo = max(0, total_demo - needs_review)
        review_pct = int(compliant_demo / total_demo * 100)
        st.markdown(
            f'<div class="donut-layout"><div class="donut" style="background:conic-gradient(#22a36b 0 {review_pct}%, #f4bd38 {review_pct}% 92%, #e64b52 92% 100%);">'
            f'<div class="donut-center">{review_pct}%<small>demo fields present</small></div></div>'
            f'<div class="legend-list"><div class="legend-row"><span class="legend-dot" style="background:#22a36b"></span>Present <strong>{compliant_demo}</strong></div>'
            f'<div class="legend-row"><span class="legend-dot" style="background:#f4bd38"></span>Needs review <strong>{needs_review}</strong></div>'
            f'<div class="legend-row"><span class="legend-dot" style="background:#e64b52"></span>Not assessed <strong>—</strong></div></div></div>',
            unsafe_allow_html=True,
        )
        st.caption("Illustrative required-field summary only; not a regulatory compliance score.")
        st.markdown('<div class="dash-panel-title" style="margin-top:12px;">Labels by market</div>', unsafe_allow_html=True)
        if not labels.empty and "market" in labels.columns:
            market_counts = labels["market"].value_counts()
            palette = ["#25a56f", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef5350"]
            maximum = max(market_counts.values) if len(market_counts) else 1
            bars = []
            for index, (market, count) in enumerate(market_counts.items()):
                height = max(8, int(float(count) / maximum * 100))
                color = palette[index % len(palette)]
                bars.append(f'<div class="vbar-wrap"><div class="vbar-value">{count}</div><div class="vbar" style="height:{height}%;background:{color};"></div><div class="vbar-label">{market}</div></div>')
            st.markdown('<div class="vertical-bars">' + ''.join(bars) + '</div>', unsafe_allow_html=True)
        else:
            st.info("No sample market data available.")

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="dash-panel-title">AI insights & alerts</div>', unsafe_allow_html=True)
        if demo_findings:
            first = demo_findings[0]
            st.markdown(
                '<div class="alert-row"><span class="alert-icon">🔴</span><div><strong>Required field needs review</strong><br>'
                + str(first.get("finding", "A required field is missing"))
                + '<br><span style="color:#8493a6;">Demo field check</span></div></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div class="alert-row"><span class="alert-icon">🟠</span><div><strong>Change impact detected</strong><br>'
            + str(len(affected)) + ' label record(s) match CR-001.<br><span style="color:#8493a6;">Sample dataset</span></div></div>'
            '<div class="alert-row"><span class="alert-icon">🔵</span><div><strong>Human review required</strong><br>Confirm field and artwork changes before release.<br>'
            '<span style="color:#8493a6;">Workflow reminder</span></div></div>',
            unsafe_allow_html=True,
        )

    with right:
        st.markdown('<div class="dash-panel-title">Change request · CR-001</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;">'
            '<div><div style="font-size:13px;font-weight:800;color:#1b3d69;">Device X100</div>'
            '<div style="font-size:11px;color:#647995;margin-top:4px;">Manufacturer address update · EU / India</div></div>'
            '<span class="status-pill pill-blue">REVIEW REQUIRED</span></div>',
            unsafe_allow_html=True,
        )
        workflow_steps = [
            ("✓", "Impact<br>analysis", "workflow-done"),
            ("✓", "Field<br>review", "workflow-done"),
            ("3", "Artwork<br>review", "workflow-active"),
            ("4", "Approval", ""),
            ("5", "Release", ""),
        ]
        flow_html = '<div class="workflow">'
        for mark, label, cls in workflow_steps:
            flow_html += (
                f'<div class="workflow-step {cls}"><div class="workflow-dot">{mark}</div>'
                f'<div>{label}</div></div>'
            )
        flow_html += "</div>"
        st.markdown(flow_html, unsafe_allow_html=True)

        st.markdown(
            '<div class="risk-strip"><span class="risk-chip risk-high">● HIGH · Address change</span>'
            '<span class="risk-chip risk-medium">● MEDIUM · Market review</span>'
            '<span class="risk-chip risk-low">● HUMAN REVIEW REQUIRED</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="dash-panel-title" style="font-size:12px;margin-top:10px;">Artwork comparison</div>', unsafe_allow_html=True)
        artwork_cols = st.columns([1, 0.12, 1], vertical_alignment="center")
        with artwork_cols[0]:
            st.markdown(
                '<div class="compare-card"><div class="compare-label">CURRENT ARTWORK</div>'
                '<div class="compare-text"><strong>Device X100</strong><br>Example Medical Ltd.<br>Manufacturer address on file</div>'
                '<div class="compare-warning">⚠ Address field needs review</div></div>',
                unsafe_allow_html=True,
            )
        with artwork_cols[1]:
            st.markdown('<div style="text-align:center;font-size:20px;color:#7d91a9;">›</div>', unsafe_allow_html=True)
        with artwork_cols[2]:
            st.markdown(
                '<div class="compare-card"><div class="compare-label">REVISED PREVIEW</div>'
                '<div class="compare-text"><strong>Device X100</strong><br>Example Medical Ltd.<br>Updated address for review</div>'
                '<div class="compare-good">✓ Proposed change highlighted</div></div>',
                unsafe_allow_html=True,
            )
        st.caption("Illustrative preview only. Actual artwork files are available in Artwork Review.")

        affected_for_table = affected.copy()
        if not affected_for_table.empty:
            st.markdown('<div class="dash-panel-title" style="font-size:12px;margin-top:10px;">Affected label records</div>', unsafe_allow_html=True)
            show_html_table(affected_for_table.head(4))

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="dash-panel-title">Labeling lifecycle</div>', unsafe_allow_html=True)
        life_steps = [
            ("✓", "Product<br>design", "life-done"),
            ("✓", "Regulatory<br>review", "life-done"),
            ("✓", "Label<br>authoring", "life-done"),
            ("4", "Translation", "life-active"),
            ("5", "Artwork<br>review", ""),
            ("6", "Approval", ""),
            ("7", "Release", ""),
        ]
        life_html = '<div class="lifecycle">'
        for mark, label, cls in life_steps:
            life_html += f'<div class="life-step"><div class="life-dot {cls}">{mark}</div><div>{label}</div></div>'
        life_html += '</div><div style="font-size:10px;color:#8191a6;">Illustrative workflow · No approval or release is performed</div>'
        st.markdown(life_html, unsafe_allow_html=True)

        st.markdown('<div class="dash-panel-title" style="margin-top:14px;">Quick actions</div>', unsafe_allow_html=True)
        quick_cols = st.columns(2, gap="small")
        quick_actions = [
            ("✍️", "Author label", "Label Studio"),
            ("🌐", "Review artwork", "Artwork Review"),
            ("🛡️", "Check fields", "Label Studio"),
            ("✨", "Prepare draft", "AI Draft Lab"),
        ]
        for idx, (icon, label, destination) in enumerate(quick_actions):
            with quick_cols[idx % 2]:
                if st.button(f"{icon}  {label}", use_container_width=True, key=f"quick_{idx}"):
                    st.session_state["page_navigation"] = destination
                    st.rerun()

    footer()

# CHANGE IMPACT
# =========================================================
elif page == "Change Impact":
    page_header(
        "CHANGE CONTROL",
        "Change Impact",
        "Find sample label records that depend on a changed product field.",
    )
    products = (
        sorted(labels["product"].dropna().unique().tolist())
        if not labels.empty and "product" in labels.columns
        else ["Device X100"]
    )
    col1, col2 = st.columns(2)
    with col1:
        selected_product = st.selectbox("Product", products)
    with col2:
        selected_field = st.selectbox(
            "Changed field",
            ["manufacturer_address", "product_name", "importer_address"],
            format_func=lambda value: value.replace("_", " ").title(),
        )

    if st.button("Analyze impact", type="primary"):
        result = get_affected(selected_product, selected_field)
        st.session_state["impact_result"] = result
        st.session_state["impact_product"] = selected_product
        st.session_state["impact_field"] = selected_field

    if "impact_result" in st.session_state:
        result = st.session_state["impact_result"]
        st.markdown("---")
        if result is not None and not result.empty:
            metric_card(
                "Affected label records",
                len(result),
                f"{st.session_state.get('impact_product', selected_product)} · "
                f"{st.session_state.get('impact_field', selected_field).replace('_', ' ')}",
            )
            show_html_table(result)
            st.warning("Impact results identify records for review; they do not approve or reject a change.")
        else:
            st.success("No matching sample labels were found.")
    st.info("The result is calculated from the dependent_fields column in the sample CSV.")
    footer()

# =========================================================
# LABEL STUDIO — AUTHORING + REQUIRED-FIELD REVIEW
# =========================================================
elif page == "Label Studio":
    page_header(
        "LABEL PREPARATION",
        "Label Studio",
        "Prepare a basic label preview and run a small required-field check.",
    )
    author_col, review_col = st.columns([1.1, 0.9], gap="large")
    with author_col:
        st.subheader("Label details")
        product_name = st.text_input("Product name", "Device X100")
        manufacturer = st.text_input("Manufacturer", "Example Medical Ltd.")
        intended_use = st.text_area(
            "Intended use",
            "Demonstration only; not for clinical use.",
            height=110,
        )
        if st.button("Preview label", type="primary", use_container_width=True):
            st.session_state["label_preview"] = {
                "product_name": product_name.strip(),
                "manufacturer": manufacturer.strip(),
                "intended_use": intended_use.strip(),
            }
    with review_col:
        st.subheader("Required-field check")
        st.write("Checks only the demo fields: product name, manufacturer, and intended use.")

        if st.button("Check fields", use_container_width=True):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/api/compliance-risk",
                    json={
                        "product_name": product_name.strip(),
                        "manufacturer": manufacturer.strip(),
                        "intended_use": intended_use.strip(),
                    },
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()

                st.session_state["label_findings"] = result.get("findings", [])
                st.session_state["label_checks"] = result.get("total_checks", 3)
                st.session_state["compliance_api_result"] = result
                st.success("Required-field check completed by the backend.")
            except requests.RequestException as exc:
                st.error(
                    "Could not connect to the compliance backend. "
                    "Ensure FastAPI is running on port 8000."
                )
                st.caption(str(exc))
            except (ValueError, TypeError) as exc:
                st.error("The backend returned an unexpected response.")
                st.caption(str(exc))

        if "label_findings" in st.session_state:
            findings = st.session_state["label_findings"]
            checks = st.session_state.get("label_checks", 3)
            result_cols = st.columns(2)
            result_cols[0].metric("Fields checked", checks)
            result_cols[1].metric("Fields needing review", len(findings))

            if findings:
                st.warning("Review the following field finding(s):")
                for finding in findings:
                    if isinstance(finding, dict):
                        risk = finding.get("risk", "Review")
                        message = finding.get(
                            "finding", finding.get("message", "Field requires review")
                        )
                        st.write(f"**{risk}** — {message}")
                    else:
                        st.write(f"• {finding}")
            else:
                st.success("All demo-required fields are present.")

        if "label_preview" in st.session_state:
            preview = st.session_state["label_preview"]
            st.markdown("---")
            st.subheader("Label preview")
            st.markdown(
                f"""
                <div class="panel">
                  <div class="eyebrow">DEMONSTRATION LABEL</div>
                  <h2>{html.escape(preview['product_name'] or 'Product name needs review')}</h2>
                  <p><strong>Manufacturer</strong><br>{html.escape(preview['manufacturer'] or 'Needs review')}</p>
                  <p><strong>Intended use</strong><br>{html.escape(preview['intended_use'] or 'Needs review')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.warning(
                "Preview only. It is not a validated label and requires qualified human review."
            )

        st.info(
            "This tool does not establish regulatory compliance or release a production label."
        )

    footer()

# =========================================================
# ARTWORK REVIEW
# =========================================================
elif page == "Artwork Review":
    page_header(
        "VISUAL QUALITY REVIEW",
        "Artwork Review",
        "Compare the supplied example artwork and inspect highlighted pixel differences.",
    )
    show_artwork()

    st.subheader("Generate demo artwork through FastAPI")
    artwork_address = st.text_input(
        "Manufacturer address",
        "Example Medical Ltd., 123 Demo Street",
        key="artwork_api_address",
    )

    if st.button("Generate artwork via backend", type="primary"):
        if not artwork_address.strip():
            st.warning("Please enter a manufacturer address first.")
        else:
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/api/artwork/create",
                    json={"address": artwork_address.strip()},
                    timeout=30,
                )
                response.raise_for_status()
                result = response.json()
                st.session_state["artwork_api_result"] = result

                if result.get("status") == "success":
                    st.success("Demo artwork generated successfully through FastAPI.")
                    image_path = result.get("image_path", "")
                    st.write("Generated image path:", image_path or "Not returned")
                    st.caption(result.get("note", ""))

                    if image_path:
                        generated_image = Path(image_path)
                        if not generated_image.is_absolute():
                            generated_image = BASE_DIR / generated_image

                        if generated_image.exists():
                            st.image(
                                str(generated_image),
                                caption="Generated demo artwork",
                                use_container_width=True,
                            )
                        else:
                            st.warning(
                                "The generated image file was not found at the returned path. "
                                "Check that the backend saves it inside the project data folder."
                            )
                else:
                    st.error(f"Artwork generation returned: {result}")

            except requests.RequestException as exc:
                st.error(
                    "Could not connect to the artwork backend. "
                    "Ensure FastAPI is running on port 8000."
                )
                st.caption(str(exc))
            except (ValueError, TypeError) as exc:
                st.error(f"The backend returned an unexpected response: {exc}")

    st.markdown(
        '<div class="warning-banner"><strong>Review limitation:</strong> '
        'Pixel differences can flag visual changes, but they do not determine '
        'whether a change is correct, approved, or compliant.</div>',
        unsafe_allow_html=True,
    )
    footer()

# =========================================================
# AI DRAFT LAB — RETRIEVAL + TEMPLATE DRAFT
# =========================================================
elif page == "AI Draft Lab":
    page_header(
        "REFERENCE-ASSISTED DRAFTING",
        "AI Draft Lab",
        "Retrieve relevant chunks from the supplied demo reference and preview a template-based draft.",
    )

    query = st.text_input(
        "What information do you want to find?",
        "What is the product name and manufacturer?",
    )
    retrieval_count = st.slider(
        "Reference chunks to retrieve", 1, 5, 3
    )

    if st.button("Retrieve references and prepare draft", type="primary"):
        if not query.strip():
            st.warning("Please enter a question first.")
        else:
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/api/ai-draft",
                    json={
                        "query": query,
                        "k": retrieval_count,
                    },
                    timeout=180,
                )
                response.raise_for_status()
                result = response.json()

                st.session_state["rag_retrieved"] = result.get(
                    "references", []
                )
                st.session_state["rag_draft"] = result.get("draft", "")
                st.session_state["rag_saved"] = False

                try:
                    DATA_DIR.mkdir(parents=True, exist_ok=True)
                    DRAFT_FILE.write_text(
                        str(st.session_state["rag_draft"]),
                        encoding="utf-8",
                    )
                    st.session_state["rag_saved"] = True
                except OSError as exc:
                    st.warning(
                        f"Draft generated but could not be saved: {exc}"
                    )

                st.success("Draft generated successfully through the backend.")

            except requests.RequestException as exc:
                st.error(
                    "Could not connect to the LabelGuard AI backend. "
                    "Ensure FastAPI is running on port 8000."
                )
                st.caption(str(exc))
            except (ValueError, KeyError) as exc:
                st.error(f"The backend returned an unexpected response: {exc}")

    if "rag_retrieved" in st.session_state:
        st.subheader("Retrieved reference chunks")
        retrieved = st.session_state["rag_retrieved"]

        if retrieved:
            for index, chunk in enumerate(retrieved, start=1):
                with st.expander(
                    f"Reference chunk {index}",
                    expanded=(index == 1),
                ):
                    st.write(chunk)
        else:
            st.info("No reference chunks were returned for this query.")

        st.subheader("Draft preview")
        st.text_area(
            "Demonstration draft",
            value=st.session_state.get("rag_draft", ""),
            height=240,
        )

        if st.session_state.get("rag_saved"):
            st.success("Draft preview saved to data/label_draft.txt.")
        else:
            st.info(
                "Draft is available in this session but could not be saved to disk."
            )

        st.download_button(
            "Download draft",
            data=st.session_state.get("rag_draft", ""),
            file_name="labelguard_demo_draft.txt",
            mime="text/plain",
        )

    st.info(
        "The current generator is template-based, not a live LLM. "
        "Reference material is demonstration content and must be independently reviewed."
    )
    footer()
