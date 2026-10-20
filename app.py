"""LabelAI Streamlit application — redesigned for readability."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from labelai_rag import streamlit_service as svc

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="LabelAI",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Design tokens ────────────────────────────────────────────────────────────
NAVY = "#0f2747"
ACCENT = "#1a56db"
BG = "#f8fafc"
CARD_BG = "#ffffff"
BORDER = "#dde4f0"
TEXT = "#1e2a3b"
MUTED = "#4b5a6e"
SUCCESS_BG = "#edfcf3"
SUCCESS_BORDER = "#22c55e"
WARN_BG = "#fffbeb"
WARN_BORDER = "#f59e0b"
DANGER_BG = "#fef2f2"
DANGER_BORDER = "#ef4444"
INFO_BG = "#eff6ff"
INFO_BORDER = "#3b82f6"


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        /* ── Base ─────────────────────────────────── */
        html, body, [data-testid="stAppViewContainer"] {{
            background: {BG};
            color: {TEXT};
        }}
        [data-testid="stApp"] {{
            background: {BG};
        }}
        /* ── Typography ───────────────────────────── */
        h1 {{ color: {NAVY}; font-size: 1.9rem; font-weight: 700; margin-bottom: 0.15rem; }}
        h2 {{ color: {NAVY}; font-size: 1.35rem; font-weight: 700; margin-top: 1.6rem; margin-bottom: 0.5rem; }}
        h3 {{ color: {NAVY}; font-size: 1.1rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.3rem; }}
        p, li {{ color: {TEXT}; line-height: 1.65; }}
        /* ── Remove Streamlit top padding ─────────── */
        [data-testid="stAppViewContainer"] > .main > div:first-child {{
            padding-top: 1.2rem;
        }}
        /* ── Cards ────────────────────────────────── */
        .la-card {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 1.1rem 1.25rem;
        }}
        /* ── Metric card ──────────────────────────── */
        .la-metric {{
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 1rem 1.1rem 0.9rem;
            text-align: center;
        }}
        .la-metric .lm-label {{
            color: {MUTED};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            margin-bottom: 0.35rem;
        }}
        .la-metric .lm-value {{
            color: {NAVY};
            font-size: 2rem;
            font-weight: 700;
            line-height: 1.15;
        }}
        /* ── Workflow step ─────────────────────────── */
        .la-step-row {{
            display: flex;
            align-items: center;
            gap: 0.4rem;
            flex-wrap: wrap;
            margin: 0.8rem 0;
        }}
        .la-step {{
            background: {ACCENT};
            color: #ffffff;
            padding: 0.45rem 0.85rem;
            border-radius: 6px;
            font-size: 0.82rem;
            font-weight: 600;
        }}
        .la-arrow {{
            color: {MUTED};
            font-size: 1rem;
        }}
        /* ── Source pill ──────────────────────────── */
        .la-pill-ok {{
            display: inline-block;
            background: {SUCCESS_BG};
            color: #166534;
            border: 1px solid {SUCCESS_BORDER};
            border-radius: 20px;
            padding: 0.2rem 0.7rem;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 0.15rem;
        }}
        .la-pill-fail {{
            display: inline-block;
            background: {DANGER_BG};
            color: #991b1b;
            border: 1px solid {DANGER_BORDER};
            border-radius: 20px;
            padding: 0.2rem 0.7rem;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 0.15rem;
        }}
        .la-pill-warn {{
            display: inline-block;
            background: {WARN_BG};
            color: #92400e;
            border: 1px solid {WARN_BORDER};
            border-radius: 20px;
            padding: 0.2rem 0.7rem;
            font-size: 0.75rem;
            font-weight: 600;
            margin: 0.15rem;
        }}
        /* ── Alert banners ────────────────────────── */
        .la-notice {{
            border-left: 4px solid {ACCENT};
            background: {INFO_BG};
            padding: 0.75rem 1rem;
            border-radius: 4px;
            font-size: 0.88rem;
            color: {TEXT};
        }}
        .la-warn {{
            border-left: 4px solid {WARN_BORDER};
            background: {WARN_BG};
            padding: 0.75rem 1rem;
            border-radius: 4px;
            font-size: 0.88rem;
            color: #78350f;
        }}
        .la-danger {{
            border-left: 4px solid {DANGER_BORDER};
            background: {DANGER_BG};
            padding: 0.75rem 1rem;
            border-radius: 4px;
            font-size: 0.88rem;
            color: #7f1d1d;
        }}
        /* ── Evidence card ────────────────────────── */
        .la-ev-header {{
            font-size: 0.93rem;
            font-weight: 600;
            color: {NAVY};
        }}
        .la-ev-meta {{
            font-size: 0.78rem;
            color: {MUTED};
            margin-top: 0.15rem;
            margin-bottom: 0.5rem;
        }}
        .la-ev-excerpt {{
            font-size: 0.82rem;
            color: {TEXT};
            background: {BG};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 0.6rem 0.8rem;
            white-space: pre-wrap;
            line-height: 1.6;
        }}
        /* ── Section divider ──────────────────────── */
        .la-divider {{
            border: none;
            border-top: 1px solid {BORDER};
            margin: 1.2rem 0;
        }}
        /* ── State badge ──────────────────────────── */
        .la-badge-support  {{ background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-partial  {{ background:#fef9c3; color:#713f12; border:1px solid #fde047; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-gap      {{ background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-review   {{ background:#e0f2fe; color:#0c4a6e; border:1px solid #7dd3fc; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-mod      {{ background:#fef3c7; color:#92400e; border:1px solid #fcd34d; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-unchanged {{ background:#f1f5f9; color:#475569; border:1px solid #cbd5e1; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-added    {{ background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-removed  {{ background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-accepted {{ background:#dcfce7; color:#166534; border:1px solid #86efac; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-pending  {{ background:#fef9c3; color:#713f12; border:1px solid #fde047; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-rejected {{ background:#fee2e2; color:#991b1b; border:1px solid #fca5a5; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        .la-badge-needsrev {{ background:#fed7aa; color:#9a3412; border:1px solid #fdba74; border-radius:4px; padding:0.15rem 0.55rem; font-size:0.75rem; font-weight:600; }}
        /* ── Streamlit tab label tweaks ───────────── */
        button[data-baseweb="tab"] {{
            font-weight: 600;
            font-size: 0.88rem;
        }}
        /* ── Suppress Streamlit "Made with" footer ── */
        footer {{ visibility: hidden; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Reusable UI helpers ──────────────────────────────────────────────────────

def metric_card(label: str, value: object) -> None:
    st.markdown(
        f"""<div class="la-metric">
               <div class="lm-label">{label}</div>
               <div class="lm-value">{value}</div>
            </div>""",
        unsafe_allow_html=True,
    )


def section_gap() -> None:
    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)


def divider() -> None:
    st.markdown("<hr class='la-divider'>", unsafe_allow_html=True)


def notice(text: str) -> None:
    st.markdown(f"<div class='la-notice'>{text}</div>", unsafe_allow_html=True)


def warn_box(text: str) -> None:
    st.markdown(f"<div class='la-warn'>{text}</div>", unsafe_allow_html=True)


def danger_box(text: str) -> None:
    st.markdown(f"<div class='la-danger'>{text}</div>", unsafe_allow_html=True)


def _evidence_state_badge(state: str) -> str:
    if state == "evidence_supported":
        return "<span class='la-badge-support'>Supported</span>"
    if state in ("potentially_relevant", "partially_supported"):
        return "<span class='la-badge-partial'>Partial / Potentially relevant</span>"
    if state == "evidence_gap":
        return "<span class='la-badge-gap'>Evidence gap</span>"
    return f"<span class='la-badge-review'>{state}</span>"


def _change_type_badge(change_type: str) -> str:
    if change_type == "modified":
        return "<span class='la-badge-mod'>Modified</span>"
    if change_type == "added":
        return "<span class='la-badge-added'>Added</span>"
    if change_type == "removed":
        return "<span class='la-badge-removed'>Removed</span>"
    return "<span class='la-badge-unchanged'>Unchanged</span>"


def _review_status_badge(status: str) -> str:
    if status == "Accepted":
        return "<span class='la-badge-accepted'>Accepted</span>"
    if status == "Needs revision":
        return "<span class='la-badge-needsrev'>Needs revision</span>"
    if status == "Rejected":
        return "<span class='la-badge-rejected'>Rejected</span>"
    return "<span class='la-badge-pending'>Pending</span>"



def render_evidence_cards(items: list[dict]) -> None:
    if not items:
        st.info("No supporting evidence was returned by the backend.")
        return
    for item in items:
        title = item.get("source_title") or item.get("source") or "Source"
        ev_id = item.get("evidence_id") or "EV"
        page = item.get("page")
        section = item.get("section") or ""
        location_parts = []
        if page:
            location_parts.append(f"Page {page}")
        if section:
            # Truncate very long section strings
            short_section = section[:80] + "…" if len(section) > 80 else section
            location_parts.append(short_section)
        location = " · ".join(location_parts) if location_parts else "Location unavailable"
        score = item.get("retrieval_score", item.get("score"))
        url = item.get("url", "")
        excerpt = item.get("excerpt", "")

        label = f"{ev_id} — {title}"
        with st.expander(label, expanded=False):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(
                    f"<div class='la-ev-header'>{title}</div>"
                    f"<div class='la-ev-meta'>"
                    f"Source ID: <code>{item.get('source_id', '—')}</code> &nbsp;·&nbsp; "
                    f"Jurisdiction: {item.get('jurisdiction', '—')} &nbsp;·&nbsp; "
                    f"{location}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if url:
                    st.markdown(f"[Open source ↗]({url})")
            with col_b:
                if score is not None:
                    st.metric("Retrieval score", f"{score:.3f}")
            if excerpt:
                st.markdown("<div class='la-ev-excerpt'>" + excerpt.replace("\n", "<br>") + "</div>", unsafe_allow_html=True)


# ── Tab 1: Overview ──────────────────────────────────────────────────────────

def overview_tab(summary: dict) -> None:
    st.markdown("<h1>LabelAI</h1>", unsafe_allow_html=True)
    st.markdown(
        "<p style='color:#4b5a6e;font-size:1.05rem;margin-top:-0.2rem;margin-bottom:0.8rem'>"
        "Evidence-grounded medical-device labeling intelligence</p>",
        unsafe_allow_html=True,
    )
    notice(
        "⚠️ <strong>Illustrative prototype only.</strong> "
        "All outputs require qualified regulatory review and do not constitute a regulatory compliance determination."
    )
    section_gap()

    # ── Metric cards ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Indexed Chunks", summary["indexed_chunks"])
    with c2:
        metric_card("Indexed Sources", summary["indexed_sources"])
    with c3:
        metric_card("Evaluation Questions", summary["evaluation_questions"])
    with c4:
        metric_card(
            "Answerable / Unanswerable",
            f"{summary['answerable_questions']} / {summary['unanswerable_questions']}",
        )

    divider()

    # ── Workflow ──────────────────────────────────────────────────────────────
    st.markdown("<h2>Workflow</h2>", unsafe_allow_html=True)
    st.markdown(
        "<div class='la-step-row'>"
        "<span class='la-step'>1 · Product Change</span>"
        "<span class='la-arrow'>→</span>"
        "<span class='la-step'>2 · Rule Mapping</span>"
        "<span class='la-arrow'>→</span>"
        "<span class='la-step'>3 · Regulatory Evidence</span>"
        "<span class='la-arrow'>→</span>"
        "<span class='la-step'>4 · Impact Assessment</span>"
        "<span class='la-arrow'>→</span>"
        "<span class='la-step'>5 · Human Review</span>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#4b5a6e;font-size:0.88rem'>"
        "Change requests are validated, classified into potentially affected label elements, "
        "linked to retrieved regulatory evidence, and routed for qualified human review. "
        "The system distinguishes <em>evidence-supported</em>, <em>potentially relevant</em>, "
        "and <em>evidence-gap</em> findings."
        "</p>",
        unsafe_allow_html=True,
    )

    divider()

    # ── Source coverage ───────────────────────────────────────────────────────
    st.markdown("<h2>Source Coverage</h2>", unsafe_allow_html=True)

    indexed_ids = summary.get("indexed_source_ids", [])
    non_indexed = summary.get("non_indexed_sources", [])

    col_ok, col_gap = st.columns(2)
    with col_ok:
        st.markdown("**Indexed (searchable)**")
        if indexed_ids:
            pills = "".join(f"<span class='la-pill-ok'>✓ {sid}</span>" for sid in indexed_ids)
            st.markdown(pills, unsafe_allow_html=True)
        else:
            st.markdown("<span class='la-pill-fail'>None indexed</span>", unsafe_allow_html=True)

    with col_gap:
        st.markdown("**Not indexed (coverage gaps)**")
        if non_indexed:
            for row in non_indexed:
                sid = row.get("source_id", "")
                status = row.get("access_status", "unknown")
                if "metadata_only" in status:
                    css = "la-pill-warn"
                    icon = "⚠"
                else:
                    css = "la-pill-fail"
                    icon = "✗"
                st.markdown(f"<span class='{css}'>{icon} {sid}</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span class='la-pill-ok'>All sources indexed</span>", unsafe_allow_html=True)

    if non_indexed:
        section_gap()
        warn_box(
            "<strong>Coverage limitation:</strong> Some sources are not indexed. "
            "US market (FDA) and ISO standard assessments use available international evidence only. "
            "Evidence states are disclosed accordingly."
        )
        with st.expander("View gap details", expanded=False):
            gap_rows = [
                {
                    "Source ID": r.get("source_id"),
                    "Status": r.get("access_status"),
                    "Reason": (r.get("notes") or "")[:120],
                }
                for r in non_indexed
            ]
            st.dataframe(gap_rows, use_container_width=True, hide_index=True)

    divider()

    # ── System status ─────────────────────────────────────────────────────────
    st.markdown("<h2>System Status</h2>", unsafe_allow_html=True)
    report = summary.get("evaluation_report") or {}
    s1, s2, s3, s4, s5 = st.columns(5)
    metrics_map = [
        (s1, "Recall@5", report.get("retrieval_recall_at_k")),
        (s2, "MRR", report.get("retrieval_mrr")),
        (s3, "Key-fact Hit", report.get("retrieved_evidence_key_fact_hit_rate")),
        (s4, "Citation Meta", report.get("citation_metadata_correctness")),
        (s5, "Abstention", report.get("abstention_accuracy")),
    ]
    for col, label, val in metrics_map:
        with col:
            display = f"{val:.3f}" if isinstance(val, float) else "—"
            metric_card(label, display)

    section_gap()
    with st.expander("Evaluation methodology & limitations", expanded=False):
        st.markdown(
            report.get("methodology", "No methodology recorded.") + "\n\n**Known limitations:**"
        )
        for lim in report.get("limitations", []):
            st.markdown(f"- {lim}")
        st.caption("These scores reflect retrieval behaviour on a closed corpus — not regulatory correctness.")


# ── Tab 2: Change Impact Analysis ────────────────────────────────────────────

def change_impact_tab() -> None:
    st.markdown("<h2>Change Impact Analysis</h2>", unsafe_allow_html=True)
    notice(
        "All product information in this form is <strong>fictional and illustrative</strong>. "
        "No real patient or device data is required or collected."
    )
    section_gap()

    # ── Form ──────────────────────────────────────────────────────────────────
    sample = svc.load_sample_change_request()
    product_context = sample["product_context"]

    with st.form("change_form"):
        st.markdown("<h3 style='margin-top:0'>Change Request Details</h3>", unsafe_allow_html=True)
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            change_id = st.text_input(
                "Change request ID",
                sample["change_id"],
                help="Unique identifier for this change request",
            )
            product_name = st.text_input(
                "Product name",
                product_context["product"],
                help="Name of the fictional product",
            )
            device_category = st.text_input(
                "Device category",
                product_context["device_type"],
                help="General category of the medical device",
            )
        with r1c2:
            target_market = st.selectbox(
                "Target market",
                ["US", "European Union", "International", "India"],
                index=0,
                help="Market for which regulatory evidence will be retrieved",
            )
            change_category = st.selectbox(
                "Change category",
                [
                    "Manufacturer information change",
                    "Intended-purpose change",
                    "Device specifications change",
                    "Materials or composition change",
                    "Warning or precaution change",
                    "Sterilization or shelf-life change",
                    "UDI or identifier change",
                    "Packaging change",
                    "Translation change",
                    "Other or unknown change",
                    "Address update",
                    "UDI update",
                    "Warnings update",
                    "IFU update",
                    "Symbols update",
                ],
                index=0,
            )
            label_elements = st.multiselect(
                "Current label elements",
                [
                    "manufacturer name/address",
                    "device identifier",
                    "UDI",
                    "warnings",
                    "symbols",
                    "instructions for use",
                    "intended purpose",
                    "precautions",
                    "storage/shelf life",
                    "sterility",
                    "composition",
                    "packaging",
                ],
                default=sample["current_label_elements"],
                help="Label elements present on the current label",
            )

        change_description = st.text_area(
            "Detailed change description",
            sample["change_description"],
            height=100,
            help="Describe the proposed change in plain language",
        )
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            optional_context = st.text_area(
                "Optional product context",
                "",
                height=70,
                help="Any additional context helpful for the reviewer",
            )
        with r2c2:
            reviewer_notes = st.text_area(
                "Optional reviewer notes",
                "",
                height=70,
            )
            review_state = st.selectbox(
                "Workflow review state",
                [
                    "Pending review",
                    "Reviewed — needs changes",
                    "Reviewed — ready for qualified approval",
                ],
            )

        submitted = st.form_submit_button(
            "▶  Run live impact assessment",
            use_container_width=True,
            type="primary",
        )

    # ── Run backend ───────────────────────────────────────────────────────────
    if submitted:
        with st.spinner("Running change-impact analysis…"):
            try:
                request = svc.build_change_request(
                    change_id,
                    product_name,
                    device_category,
                    target_market,
                    change_category,
                    change_description,
                    label_elements,
                    optional_context,
                    reviewer_notes,
                )
                assessment = svc.run_change_impact(request)
                st.session_state["last_request"] = request
                st.session_state["last_assessment"] = assessment
                st.session_state["review_state"] = review_state
                st.success("Assessment complete. Results shown below.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Assessment failed: {exc}")

    assessment = st.session_state.get("last_assessment")
    request = st.session_state.get("last_request")

    if not assessment:
        st.info("Submit the form above to run the actual backend. A pre-generated fixture exists in `data/change_impact/` but is not shown as a live result here.")
        return

    divider()

    # ── Assessment summary bar ────────────────────────────────────────────────
    st.markdown("<h3>Assessment Summary</h3>", unsafe_allow_html=True)
    sb1, sb2, sb3, sb4 = st.columns(4)
    confidence = assessment.get("confidence_or_uncertainty", {}).get("overall", "—")
    with sb1:
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Change ID</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{NAVY}'>{assessment['change_id']}</div></div>",
            unsafe_allow_html=True,
        )
    with sb2:
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Market</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{NAVY}'>{assessment.get('product_context', {}).get('market', '—')}</div></div>",
            unsafe_allow_html=True,
        )
    with sb3:
        conf_color = NAVY if confidence != "low" else "#b45309"
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Confidence</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{conf_color}'>{confidence.upper()}</div></div>",
            unsafe_allow_html=True,
        )
    with sb4:
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Workflow State</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{NAVY}'>{st.session_state.get('review_state', 'Pending review')}</div></div>",
            unsafe_allow_html=True,
        )

    section_gap()
    danger_box(
        "⚠️ <strong>Human review required.</strong> "
        "This assessment does not constitute a regulatory compliance determination. "
        "All outputs must be reviewed by a qualified regulatory professional before any labeling decision."
    )

    divider()

    # ── Affected elements table ───────────────────────────────────────────────
    st.markdown("<h3>Potentially Affected Label Elements</h3>", unsafe_allow_html=True)
    elements = assessment.get("affected_label_elements", [])
    reasons = {r["element"]: r for r in assessment.get("reason_for_impact", [])}
    actions = {a["element"]: a for a in assessment.get("recommended_review_actions", [])}

    if not elements:
        st.info("No label elements were matched by the deterministic rules for this change. Manual triage is recommended.")
    else:
        for elem in elements:
            el_name = elem["element"]
            state = elem.get("evidence_state", "unknown")
            badge = _evidence_state_badge(state)
            reason_text = reasons.get(el_name, {}).get("reason", "—")
            action_text = actions.get(el_name, {}).get("action", "—")
            refs = elem.get("evidence_refs", [])

            with st.expander(f"**{el_name}**  ·  {state.replace('_', ' ').title()}", expanded=True):
                ea, eb = st.columns([1, 2])
                with ea:
                    st.markdown(f"**Evidence quality:** {badge}", unsafe_allow_html=True)
                    if refs:
                        st.markdown(f"**Evidence refs:** `{', '.join(refs)}`")
                    else:
                        st.markdown("**Evidence refs:** None retrieved")
                with eb:
                    st.markdown(f"**Reason for review:** {reason_text}")
                    st.markdown(f"**Recommended action:** {action_text}")

    divider()

    # ── Supporting evidence ───────────────────────────────────────────────────
    st.markdown("<h3>Supporting Evidence</h3>", unsafe_allow_html=True)
    render_evidence_cards(assessment.get("supporting_evidence", []))

    divider()

    # ── Limitations & missing information ─────────────────────────────────────
    st.markdown("<h3>Missing Information & Coverage Limitations</h3>", unsafe_allow_html=True)
    missing = assessment.get("missing_information", [])
    limitations = assessment.get("source_coverage_limitations", [])

    if missing:
        st.markdown("**Missing information (required before release):**")
        for item in missing:
            st.markdown(f"- {item}")

    if limitations:
        section_gap()
        st.markdown("**Source coverage limitations:**")
        for item in limitations:
            st.markdown(f"- {item}")

    divider()

    # ── Downloads ─────────────────────────────────────────────────────────────
    st.markdown("<h3>Download Results</h3>", unsafe_allow_html=True)
    dl1, dl2 = st.columns(2)
    with dl1:
        st.download_button(
            "⬇ Download request JSON",
            svc.result_to_json_bytes(request),
            "change_request.json",
            "application/json",
            use_container_width=True,
        )
    with dl2:
        st.download_button(
            "⬇ Download assessment JSON",
            svc.result_to_json_bytes(assessment),
            "impact_assessment.json",
            "application/json",
            use_container_width=True,
        )


# ── Tab 3: Label Authoring ───────────────────────────────────────────────────

def label_authoring_tab() -> None:
    st.markdown("<h2>Evidence-Grounded Label Authoring & Review</h2>", unsafe_allow_html=True)
    notice(
        "Drafting and review workbench: proposed revisions are grounded strictly in approved product facts, "
        "change-impact candidate sections, and retrieved regulatory evidence. "
        "Unchanged sections are preserved. Unprovided facts are explicitly flagged as limitations."
    )
    section_gap()

    preset = st.selectbox(
        "Preset Demonstration Scenario",
        [
            "Scenario 1: Facility Relocation (CardioFlex Coronary Stent — US)",
            "Scenario 2: UDI & Identifier Update (OrthoSpine Pedicle Screw — US)",
            "Custom Label & Facts",
        ],
        index=0,
    )

    if preset.startswith("Scenario 1"):
        default_label = svc.load_sample_existing_label()
        default_facts = svc.load_sample_approved_facts()
    elif preset.startswith("Scenario 2"):
        default_label = json.loads(Path("data/label_authoring/sample_existing_label_udi.json").read_text(encoding="utf-8"))
        default_facts = json.loads(Path("data/label_authoring/sample_approved_facts_udi.json").read_text(encoding="utf-8"))
    else:
        default_label = svc.load_sample_existing_label()
        default_facts = {}

    with st.form("authoring_form"):
        f1, f2 = st.columns(2)
        with f1:
            target_jurisdiction = st.selectbox("Target Jurisdiction", ["US", "European Union", "International", "India"], index=0)
            use_impact = st.checkbox("Link to active Change-Impact Assessment from Tab 2", value=True)
        with f2:
            target_version = st.text_input("Target Draft Label Version (optional)", "", help="e.g. Rev C or v2.0 (leave blank to auto-increment)")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Approved Product Facts (JSON)**")
            facts_text = st.text_area(
                "Approved Facts",
                json.dumps(default_facts, indent=2),
                height=180,
                label_visibility="collapsed",
            )
        with c2:
            st.markdown("**Existing Approved Label (JSON)**")
            label_text = st.text_area(
                "Existing Label",
                json.dumps(default_label, indent=2),
                height=180,
                label_visibility="collapsed",
            )

        generate_submitted = st.form_submit_button(
            "🚀  Generate Grounded Label Draft & Version Diff",
            type="primary",
            use_container_width=True,
        )

    if generate_submitted:
        with st.spinner("Executing grounded label authoring pipeline…"):
            try:
                parsed_facts = json.loads(facts_text)
                parsed_label = json.loads(label_text)
                impact_assessment = st.session_state.get("last_assessment") if use_impact else None
                authoring_res = svc.run_label_authoring(
                    approved_product_facts=parsed_facts,
                    existing_label=parsed_label,
                    target_jurisdiction=target_jurisdiction,
                    impact_assessment=impact_assessment,
                    target_version=target_version.strip() if target_version.strip() else None,
                )
                st.session_state["authoring_result"] = authoring_res
                st.success("Draft generated and compared with existing label. Review items below.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Authoring failed: {exc}")

    result = st.session_state.get("authoring_result")
    if not result:
        st.info("Configure approved product facts and existing label above, then click **Generate Grounded Label Draft**.")
        return

    report = result["comparison_report"]
    proposed = result["proposed_label"]

    divider()
    st.markdown("<h3>Drafting & Comparison Summary</h3>", unsafe_allow_html=True)
    sb1, sb2, sb3, sb4 = st.columns(4)
    with sb1:
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Version Transition</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{NAVY}'>{report['from_version']} → {report['to_version']}</div></div>",
            unsafe_allow_html=True,
        )
    with sb2:
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Modified Fields</div>"
            f"<div style='font-size:1rem;font-weight:700;color:#92400e'>{report['modified_fields']}</div></div>",
            unsafe_allow_html=True,
        )
    with sb3:
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Preserved Unchanged</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{NAVY}'>{report['unchanged_fields']}</div></div>",
            unsafe_allow_html=True,
        )
    with sb4:
        st.markdown(
            f"<div class='la-card'><div style='font-size:0.75rem;color:{MUTED};text-transform:uppercase;font-weight:600'>Jurisdiction</div>"
            f"<div style='font-size:1rem;font-weight:700;color:{NAVY}'>{report['target_jurisdiction']}</div></div>",
            unsafe_allow_html=True,
        )

    section_gap()
    danger_box(
        "⚠️ <strong>Human regulatory review required.</strong> "
        "This is an AI-assisted drafting tool. Proposed drafts do not constitute a regulatory compliance determination. "
        "Every section must be reviewed and accepted by a qualified regulatory professional prior to release."
    )

    if report.get("missing_information"):
        section_gap()
        warn_box(
            "<strong>Missing Information Identified:</strong><br>"
            + "<br>".join(f"• {m}" for m in report["missing_information"])
        )

    if report.get("limitations"):
        section_gap()
        notice(
            "<strong>Coverage & Methodology Disclosures:</strong><br>"
            + "<br>".join(f"• {lim}" for lim in report["limitations"])
        )

    divider()
    st.markdown("<h3>Field-by-Field Comparison & Human Review Decisions</h3>", unsafe_allow_html=True)

    diffs = report.get("field_diffs", [])
    for d in diffs:
        fid = d["field_id"]
        fname = d["label_name"]
        ctype = d["change_type"]
        estate = d["evidence_state"]
        rstatus = d["review_status"]
        cbadge = _change_type_badge(ctype)
        ebadge = _evidence_state_badge(estate)
        rbadge = _review_status_badge(rstatus)

        exp_open = ctype != "unchanged" or estate == "evidence_gap"
        with st.expander(f"**{fname}** (`{fid}`)  ·  {ctype.upper()}  ·  Review: {rstatus}", expanded=exp_open):
            st.markdown(f"**Change Type:** {cbadge} &nbsp;|&nbsp; **Evidence Quality:** {ebadge} &nbsp;|&nbsp; **Review Decision:** {rbadge}", unsafe_allow_html=True)
            st.markdown(f"**Rationale:** {d['reason_for_change']}")
            if d.get("evidence_refs"):
                st.markdown(f"**Evidence References:** `{', '.join(d['evidence_refs'])}`")

            col_orig, col_prop = st.columns(2)
            with col_orig:
                st.markdown("**Original Approved Value:**")
                st.text_area(f"orig_{fid}", d["original_value"], height=90, disabled=True, key=f"orig_disp_{fid}")
            with col_prop:
                st.markdown("**Proposed Value:**")
                st.text_area(f"prop_{fid}", d["proposed_value"], height=90, disabled=True, key=f"prop_disp_{fid}")

            # Interactive field review
            st.markdown("---")
            rc1, rc2, rc3 = st.columns([1, 2, 1])
            with rc1:
                decision_choice = st.selectbox(
                    f"Decision ({fid})",
                    ["Pending", "Accepted", "Needs revision", "Rejected"],
                    index=["Pending", "Accepted", "Needs revision", "Rejected"].index(rstatus) if rstatus in ["Pending", "Accepted", "Needs revision", "Rejected"] else 0,
                    key=f"dec_sel_{fid}",
                )
            with rc2:
                notes_input = st.text_input(
                    f"Reviewer notes ({fid})",
                    value=d.get("reviewer_notes", ""),
                    key=f"notes_in_{fid}",
                )
            with rc3:
                st.markdown("<div style='margin-top:1.8rem'></div>", unsafe_allow_html=True)
                if st.button("Update Decision", key=f"save_btn_{fid}", use_container_width=True):
                    updated = svc.update_label_field_review(report, fid, decision_choice, notes_input)
                    st.session_state["authoring_result"]["comparison_report"] = updated["comparison_report"]
                    st.session_state["authoring_result"]["markdown_report"] = updated["markdown_report"]
                    st.rerun()

    divider()
    st.markdown("<h3>Download Authoring Deliverables</h3>", unsafe_allow_html=True)
    d1, d2, d3 = st.columns(3)
    with d1:
        st.download_button(
            "⬇ Download Proposed Label (JSON)",
            svc.result_to_json_bytes(proposed),
            f"{proposed.get('label_id', 'draft_label')}.json",
            "application/json",
            use_container_width=True,
        )
    with d2:
        st.download_button(
            "⬇ Download Comparison Report (JSON)",
            svc.result_to_json_bytes(report),
            "version_comparison_report.json",
            "application/json",
            use_container_width=True,
        )
    with d3:
        st.download_button(
            "⬇ Download Audit Report (Markdown)",
            result.get("markdown_report", "").encode("utf-8"),
            "label_version_diff.md",
            "text/markdown",
            use_container_width=True,
        )


# ── Tab 4: Regulatory Q&A ────────────────────────────────────────────────────


EXAMPLE_QUESTIONS = [
    "What does IMDRF say about manufacturer address on the label?",
    "What does IMDRF say a UDI allows?",
    "What exact FDA rule applies to this US cardiac stent label?",
]


def qa_tab() -> None:
    st.markdown("<h2>Regulatory Q&A</h2>", unsafe_allow_html=True)
    notice(
        "Retrieval-grounded answers only — no AI-generated regulatory conclusions. "
        "Evidence is drawn from the indexed corpus. Unanswerable questions are flagged explicitly."
    )
    section_gap()

    # ── Question form ─────────────────────────────────────────────────────────
    with st.form("qa_form"):
        question = st.text_input(
            "Question",
            EXAMPLE_QUESTIONS[0],
            help="Ask about labeling requirements for the indexed sources",
        )
        target_market = st.selectbox(
            "Target market (filters evidence jurisdiction)",
            ["International", "European Union", "US", "India"],
            index=0,
        )
        ask_submitted = st.form_submit_button("🔍  Search evidence", use_container_width=True, type="primary")

    if ask_submitted:
        with st.spinner("Searching the regulatory corpus…"):
            try:
                st.session_state["last_qa"] = svc.ask_regulatory_question(question, target_market)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Question failed: {exc}")

    qa = st.session_state.get("last_qa")

    if not qa:
        st.info("Ask a question above to retrieve live evidence from the current index.")
        with st.expander("Example questions to try"):
            for q in EXAMPLE_QUESTIONS:
                st.markdown(f"- {q}")
        return

    divider()

    # ── Evidence status ────────────────────────────────────────────────────────
    if qa["insufficient_evidence"]:
        warn_box(
            "⚠️ <strong>Insufficient evidence</strong> in the currently indexed sources. "
            "Additional authoritative sources and qualified regulatory review are required."
        )
    else:
        notice("✓ Evidence retrieved from the indexed corpus. Review source excerpts below.")

    section_gap()

    # ── Answer ────────────────────────────────────────────────────────────────
    st.markdown("<h3>Answer</h3>", unsafe_allow_html=True)
    # Strip the raw citation markers and render cleanly
    answer_text = qa.get("answer", "")
    # Show as a bordered text block for readability
    st.markdown(
        f"<div class='la-card' style='font-size:0.9rem;line-height:1.7'>{answer_text.replace(chr(10), '<br>')}</div>",
        unsafe_allow_html=True,
    )
    st.caption(qa.get("interpretation_note", ""))

    divider()

    # ── Evidence cards ────────────────────────────────────────────────────────
    st.markdown("<h3>Retrieved Evidence</h3>", unsafe_allow_html=True)
    render_evidence_cards(qa.get("evidence", []))


# ── Tab 4: Evidence & Evaluation ─────────────────────────────────────────────

def evidence_tab(summary: dict) -> None:
    st.markdown("<h2>Evidence & Evaluation</h2>", unsafe_allow_html=True)
    section_gap()

    # ── Source manifest ────────────────────────────────────────────────────────
    st.markdown("<h3>Source Manifest</h3>", unsafe_allow_html=True)
    manifest = svc.load_manifest()

    def _status_label(status: str) -> str:
        if status.startswith("downloaded"):
            return "✓ Indexed"
        if "metadata_only" in status:
            return "⚠ Metadata only"
        return "✗ Not indexed"

    manifest_rows = [
        {
            "Source ID": r.get("source_id"),
            "Title": (r.get("official_title") or "")[:60],
            "Publisher": (r.get("publisher") or "")[:35],
            "Jurisdiction": r.get("jurisdiction"),
            "Status": _status_label(r.get("access_status", "")),
            "Date": r.get("document_date") or "—",
        }
        for r in manifest
    ]
    st.dataframe(manifest_rows, use_container_width=True, hide_index=True)

    with st.expander("Full manifest details (URLs and notes)"):
        full_rows = [
            {
                "source_id": r.get("source_id"),
                "access_status": r.get("access_status"),
                "url": r.get("url"),
                "notes": r.get("notes") or "—",
            }
            for r in manifest
        ]
        st.dataframe(full_rows, use_container_width=True, hide_index=True)

    divider()

    # ── Evaluation metrics ─────────────────────────────────────────────────────
    st.markdown("<h3>Evaluation Metrics</h3>", unsafe_allow_html=True)
    report = summary.get("evaluation_report") or {}

    if not report:
        st.warning(
            "No saved evaluation report found. "
            "Run: `.venv\\Scripts\\python.exe -m labelai_rag.cli evaluate`"
        )
    else:
        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            metric_card("Total questions", report.get("evaluation_set_size", "—"))
        with ec2:
            metric_card("Answerable", report.get("answerable_questions", "—"))
        with ec3:
            metric_card("Unanswerable", report.get("unanswerable_questions", "—"))

        section_gap()

        metric_defs = {
            "retrieval_recall_at_k": "Expected source ID appears in top-k retrieved chunks.",
            "retrieval_mrr": "Mean reciprocal rank of the first expected source ID hit.",
            "retrieved_evidence_key_fact_hit_rate": "Expected key-fact substring appears in top-k retrieved text.",
            "citation_metadata_correctness": "Retrieved chunks have non-empty title and URL metadata.",
            "abstention_accuracy": "Unanswerable questions that correctly returned an insufficient-evidence response.",
        }
        metric_rows = [
            {
                "Metric": key.replace("_", " ").capitalize(),
                "Value": f"{report[key]:.3f}" if isinstance(report.get(key), float) else "—",
                "Definition": defn,
            }
            for key, defn in metric_defs.items()
        ]
        st.dataframe(metric_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Scores are based on retrieval checks against the saved evaluation set. "
            "Opening this tab does not rerun the evaluation."
        )

        with st.expander("Methodology and limitations"):
            st.markdown(report.get("methodology", "No methodology recorded."))
            st.markdown("**Known limitations:**")
            for lim in report.get("limitations", []):
                st.markdown(f"- {lim}")
            st.markdown(
                "**Important:** Perfect scores on a small closed corpus do not imply regulatory accuracy. "
                "These metrics confirm that retrieval and abstention mechanisms work as designed."
            )
            st.markdown("**Refresh evaluation from CLI:**")
            st.code(
                r".\.venv\Scripts\python.exe -m labelai_rag.cli evaluate",
                language="powershell",
            )


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    inject_css()
    summary = svc.runtime_summary()
    tabs = st.tabs([
        "🏠 Overview",
        "🔄 Change Impact",
        "📝 Label Authoring",
        "❓ Regulatory Q&A",
        "📊 Evidence & Evaluation",
    ])
    with tabs[0]:
        overview_tab(summary)
    with tabs[1]:
        change_impact_tab()
    with tabs[2]:
        label_authoring_tab()
    with tabs[3]:
        qa_tab()
    with tabs[4]:
        evidence_tab(summary)


if __name__ == "__main__":
    main()

