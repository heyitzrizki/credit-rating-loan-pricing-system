import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.append(str(APP_DIR))
import pandas as pd
import streamlit as st

from utils import load_data_objects

st.set_page_config(page_title="About the System", layout="wide")

data = load_data_objects()
metadata = data["metadata"]

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1400px;
        }
        .section-card {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            padding: 1.15rem 1.2rem 0.95rem 1.2rem;
            margin-bottom: 1rem;
        }
        .section-title {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }
        .muted {
            color: #B7BFCA;
            font-size: 0.97rem;
            line-height: 1.65;
        }
        .policy-pill {
            display: inline-block;
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            margin-right: 0.5rem;
            margin-bottom: 0.55rem;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            font-size: 0.92rem;
            color: #D9DEE7;
        }
        .small-label {
            color: #9EA7B3;
            font-size: 0.88rem;
            margin-bottom: 0.15rem;
        }
        .big-value {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("About the System")
st.caption("Governance, rating logic, and usage guidance for the credit rating dashboard")

# 1. WHAT THIS SYSTEM DOES
c1, c2 = st.columns((1.25, 1))

with c1:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">What this system does</div>
            <div class="muted">
                This system estimates borrower-level probability of default (PD), maps each borrower into an
                <b>AAA–D credit grade</b>, and provides a <b>decision recommendation</b> for approval,
                review, or rejection. The dashboard is designed to support borrower screening, portfolio
                monitoring, and high-risk watchlist management.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">System summary</div>
            <div class="small-label">Model</div>
            <div class="big-value">{metadata.get("final_model_name", "-")}</div>
            <div class="small-label">Calibration</div>
            <div class="big-value">{metadata.get("calibration_method", "-")}</div>
            <div class="small-label">Intended use</div>
            <div class="big-value">Decision Support</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 2. RATING FRAMEWORK
st.markdown("### Rating Framework")

left, right = st.columns(2)

with left:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Credit grade structure</div>
            <div class="muted">
                Borrowers are assigned to an ordered rating framework from <b>AAA</b> to <b>D</b>.
                Higher grades indicate stronger risk quality, while lower grades indicate greater credit risk.
            </div>
            <br>
            <span class="policy-pill">AAA</span>
            <span class="policy-pill">AA</span>
            <span class="policy-pill">A</span>
            <span class="policy-pill">BBB</span>
            <span class="policy-pill">BB</span>
            <span class="policy-pill">B</span>
            <span class="policy-pill">C</span>
            <span class="policy-pill">D</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with right:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Business interpretation</div>
            <div class="muted">
                <b>Investment Grade:</b> AAA, AA, A<br>
                <b>Review Grade:</b> BBB, BB<br>
                <b>High Risk:</b> B, C, D
                <br><br>
                These groupings are used to support business interpretation, analyst review prioritization,
                and portfolio-level monitoring.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 3. DECISION POLICY
st.markdown("### Decision Policy")

d1, d2, d3 = st.columns(3)

with d1:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Approve</div>
            <div class="muted">
                Recommended for borrowers in grades <b>AAA</b>, <b>AA</b>, and <b>A</b>.
                These borrowers fall within the strongest risk-quality segment of the portfolio.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with d2:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Review</div>
            <div class="muted">
                Recommended for borrowers in grades <b>BBB</b> and <b>BB</b>.
                These cases may require analyst review, additional verification, or tighter policy checks.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with d3:
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">Reject</div>
            <div class="muted">
                Recommended for borrowers in grades <b>B</b>, <b>C</b>, and <b>D</b>.
                These borrowers belong to the highest-risk segment under the current framework.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 4. GOVERNANCE
st.markdown("### Governance")

g1, g2 = st.columns(2)

with g1:
    governance_df = pd.DataFrame(
        {
            "Item": [
                "Model Family",
                "Calibration Method",
                "Rating Framework",
                "Decision Policy",
                "Explanation Method",
            ],
            "Value": [
                metadata.get("model_family", metadata.get("final_model_name", "-")),
                metadata.get("calibration_method", "-"),
                "AAA–D",
                "Approve / Review / Reject",
                metadata.get("explanation_method", "Not available"),
            ],
        }
    )
    st.dataframe(governance_df, use_container_width=True, hide_index=True)

with g2:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">Usage note</div>
            <div class="muted">
                {metadata.get("usage_note", "Model output should be treated as decision support and not as a fully automated approval engine.")}
            </div>
            <br>
            <div class="section-title">Intended use</div>
            <div class="muted">
                {metadata.get("intended_use", "Borrower rating and portfolio monitoring")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# 5. LIMITATIONS
st.markdown("### Practical Limitations")

l1, l2, l3 = st.columns(3)

with l1:
    st.warning(
        "This system supports credit assessment, but final lending decisions should remain subject to business rules and analyst judgment."
    )

with l2:
    st.warning(
        "Decision thresholds and grade behavior should be monitored over time, especially if portfolio composition changes."
    )

with l3:
    st.warning(
        "Model explanations help interpret predictions, but they do not prove causal relationships."
    )

# 6. OPTIONAL TECHNICAL DETAILS
with st.expander("Optional technical details"):
    tech_df = pd.DataFrame(
        {
            "Metric": [
                "Valid ROC-AUC",
                "Test ROC-AUC",
                "Valid PR-AUC",
                "Test PR-AUC",
                "Valid Brier (Platt)",
                "Test Brier (Platt)",
            ],
            "Value": [
                metadata.get("valid_roc_auc", None),
                metadata.get("test_roc_auc", None),
                metadata.get("valid_pr_auc", None),
                metadata.get("test_pr_auc", None),
                metadata.get("valid_brier_platt", None),
                metadata.get("test_brier_platt", None),
            ],
        }
    )

    tech_df["Value"] = tech_df["Value"].apply(
        lambda x: f"{x:.4f}" if isinstance(x, (int, float)) and x is not None else "-"
    )

    st.dataframe(tech_df, use_container_width=True, hide_index=True)
