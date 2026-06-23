import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"
ARTIFACT_DIR = PROJECT_ROOT / "artifacts"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from pricing_engine import (  # noqa: E402
    apply_borrower_stress,
    calculate_loan_pricing,
    lgd_from_grade,
    safe_float,
)
from utils import (  # noqa: E402
    assign_credit_grade_from_summary,
    assign_decision_from_grade,
    build_existing_borrower_sequence,
    build_temporal_preset,
    get_tcn_embedding,
    load_data_objects,
    load_models,
    preprocess_static_row,
    score_borrower,
)


st.set_page_config(
    page_title="Credit Rating & Loan Pricing Decision System",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data
def load_decision_data():
    risk_ecl = pd.read_csv(ARTIFACT_DIR / "portfolio_ecl_base.csv")
    profile = pd.read_csv(ARTIFACT_DIR / "borrower_profile_ui.csv")
    explanation_path = ARTIFACT_DIR / "borrower_explanation_summary.csv"
    explanations = (
        pd.read_csv(explanation_path) if explanation_path.exists() else pd.DataFrame()
    )

    borrowers = risk_ecl.merge(
        profile,
        on="SK_ID_CURR",
        how="left",
        suffixes=("", "_profile"),
    )
    borrowers["LGD"] = borrowers.apply(
        lambda row: (
            float(row["LGD"]) if pd.notna(row.get("LGD")) else lgd_from_grade(row["credit_grade"])
        ),
        axis=1,
    )
    borrowers["EAD"] = borrowers["EAD"].fillna(borrowers["AMT_CREDIT"])
    borrowers["ECL_base"] = borrowers["ECL_base"].fillna(
        borrowers["pd_calibrated"] * borrowers["LGD"] * borrowers["EAD"]
    )
    borrowers = borrowers.sort_values("SK_ID_CURR").reset_index(drop=True)
    return borrowers, explanations


def fmt_pct(value, decimals=2):
    if pd.isna(value):
        return "-"
    return f"{float(value) * 100:,.{decimals}f}%"


def fmt_currency(value):
    if pd.isna(value):
        return "-"
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.1f}K"
    return f"{value:,.0f}"


def fmt_number(value):
    if pd.isna(value):
        return "-"
    return f"{float(value):,.0f}"


def render_decision(decision):
    if decision == "Approve":
        st.success("Final Decision: Approve")
    elif decision == "Approve if Repriced":
        st.info("Final Decision: Approve if Repriced")
    elif decision == "Manual Review":
        st.warning("Final Decision: Manual Review")
    else:
        st.error("Final Decision: Reject")


def get_drivers(explanations, borrower_id):
    if explanations.empty:
        return [], []

    matched = explanations[explanations["SK_ID_CURR"].eq(borrower_id)]
    if matched.empty:
        return [], []

    row = matched.iloc[0]
    risk_cols = ["top_1_risk_driver", "top_2_risk_driver", "top_3_risk_driver"]
    support_cols = [
        "top_1_support_driver",
        "top_2_support_driver",
        "top_3_support_driver",
    ]

    risk = [str(row[col]) for col in risk_cols if col in row.index and pd.notna(row[col])]
    support = [
        str(row[col])
        for col in support_cols
        if col in row.index and pd.notna(row[col])
    ]
    return risk, support


def build_no_history_sequence(data_dict):
    temporal_cols = data_dict["temporal_feature_cols_v2"]
    seq = np.zeros((12, len(temporal_cols)), dtype=np.float32)
    mask = np.zeros((12, 1), dtype=bool)
    return seq, mask


def score_existing_borrower_live(selected_borrower):
    xgb_model, platt, encoder, _ = load_models()
    data = load_data_objects()

    borrower_row_full = data["app_static"][
        data["app_static"]["SK_ID_CURR"].eq(selected_borrower)
    ].copy()

    if borrower_row_full.empty:
        raise ValueError(f"Borrower {selected_borrower} is not available for live scoring.")

    static_raw = borrower_row_full.drop(
        columns=[c for c in ["SK_ID_CURR", "TARGET"] if c in borrower_row_full.columns]
    )
    static_processed = preprocess_static_row(static_raw, data)
    seq, mask = build_existing_borrower_sequence(selected_borrower, data)
    embedding, _ = get_tcn_embedding(encoder, seq, mask)
    raw_pd, calibrated_pd = score_borrower(
        static_processed,
        embedding,
        xgb_model,
        platt,
        data["emb_cols_v2"],
    )
    grade = assign_credit_grade_from_summary(
        calibrated_pd,
        data.get("credit_grade_summary"),
    )
    recommendation = assign_decision_from_grade(grade)

    return {
        "pd_raw": raw_pd,
        "pd_calibrated": calibrated_pd,
        "credit_grade": grade,
        "decision_recommendation": recommendation,
        "score_source": "Live model scoring",
    }


def build_new_borrower_static_row(data, inputs):
    static_source = data["app_static"].drop(
        columns=[c for c in ["SK_ID_CURR", "TARGET"] if c in data["app_static"].columns],
        errors="ignore",
    )

    values = {}
    for col in static_source.columns:
        if pd.api.types.is_numeric_dtype(static_source[col]):
            values[col] = static_source[col].median()
        else:
            mode = static_source[col].mode(dropna=True)
            values[col] = mode.iloc[0] if not mode.empty else "Unknown"

    values.update({k: v for k, v in inputs.items() if k in static_source.columns})
    return pd.DataFrame([values])


def score_new_borrower_live(inputs, temporal_assumption):
    xgb_model, platt, encoder, _ = load_models()
    data = load_data_objects()

    static_raw = build_new_borrower_static_row(data, inputs)
    static_processed = preprocess_static_row(static_raw, data)

    if temporal_assumption == "No prior repayment history":
        seq, mask = build_no_history_sequence(data)
    else:
        seq, mask = build_temporal_preset(data, temporal_assumption)

    embedding, _ = get_tcn_embedding(encoder, seq, mask)
    raw_pd, calibrated_pd = score_borrower(
        static_processed,
        embedding,
        xgb_model,
        platt,
        data["emb_cols_v2"],
    )
    grade = assign_credit_grade_from_summary(
        calibrated_pd,
        data.get("credit_grade_summary"),
    )
    recommendation = assign_decision_from_grade(grade)

    return {
        "pd_raw": raw_pd,
        "pd_calibrated": calibrated_pd,
        "credit_grade": grade,
        "decision_recommendation": recommendation,
        "score_source": "Live new-borrower simulation",
    }


borrowers, explanations = load_decision_data()

st.title("Credit Rating & Loan Pricing Decision System")
st.caption(
    "Decision tool for borrower credit risk, expected loss, risk-based pricing, and final lending action."
)

st.divider()

left, right = st.columns([1, 1.45], gap="large")

with left:
    st.subheader("1. Borrower / Loan Profile")

    applicant_mode = st.radio(
        "Applicant type",
        ["Existing borrower", "New borrower simulation"],
        horizontal=True,
    )

    if applicant_mode == "Existing borrower":
        borrower_ids = borrowers["SK_ID_CURR"].astype(int).tolist()
        selected_borrower = st.selectbox("Borrower ID", borrower_ids)
        row = borrowers[borrowers["SK_ID_CURR"].eq(selected_borrower)].iloc[0].copy()
        live_score = score_existing_borrower_live(int(selected_borrower))
        row["pd_raw"] = live_score["pd_raw"]
        row["pd_calibrated"] = live_score["pd_calibrated"]
        row["credit_grade"] = live_score["credit_grade"]
        row["decision_recommendation"] = live_score["decision_recommendation"]
        score_source = live_score["score_source"]
    else:
        selected_borrower = None
        n1, n2 = st.columns(2)
        income = n1.number_input(
            "Annual income",
            min_value=10_000.0,
            max_value=2_000_000.0,
            value=180_000.0,
            step=10_000.0,
        )
        requested_credit = n2.number_input(
            "Requested credit amount",
            min_value=10_000.0,
            max_value=3_000_000.0,
            value=500_000.0,
            step=10_000.0,
        )
        annuity = n1.number_input(
            "Regular payment amount",
            min_value=1_000.0,
            max_value=300_000.0,
            value=25_000.0,
            step=1_000.0,
        )
        goods_price = n2.number_input(
            "Goods price",
            min_value=10_000.0,
            max_value=3_000_000.0,
            value=450_000.0,
            step=10_000.0,
        )
        contract_type = n1.selectbox("Contract type", ["Cash loans", "Revolving loans"])
        family_status = n2.selectbox(
            "Family status",
            ["Married", "Single / not married", "Civil marriage", "Separated", "Widow"],
        )
        owns_car = n1.selectbox("Owns car", ["N", "Y"])
        owns_realty = n2.selectbox("Owns realty", ["Y", "N"])
        ext_source_2 = n1.slider("External credit score 2", 0.0, 1.0, 0.50, 0.01)
        ext_source_3 = n2.slider("External credit score 3", 0.0, 1.0, 0.50, 0.01)
        temporal_assumption = st.selectbox(
            "Repayment history assumption",
            [
                "No prior repayment history",
                "Stable payer",
                "Mild deterioration",
                "High delinquency",
                "Recovering borrower",
            ],
        )

        new_inputs = {
            "AMT_INCOME_TOTAL": income,
            "AMT_CREDIT": requested_credit,
            "AMT_ANNUITY": annuity,
            "AMT_GOODS_PRICE": goods_price,
            "NAME_CONTRACT_TYPE": contract_type,
            "NAME_FAMILY_STATUS": family_status,
            "FLAG_OWN_CAR": owns_car,
            "FLAG_OWN_REALTY": owns_realty,
            "EXT_SOURCE_2": ext_source_2,
            "EXT_SOURCE_3": ext_source_3,
        }
        live_score = score_new_borrower_live(new_inputs, temporal_assumption)
        row = pd.Series(
            {
                "SK_ID_CURR": "New application",
                "AMT_INCOME_TOTAL": income,
                "AMT_CREDIT": requested_credit,
                "AMT_ANNUITY": annuity,
                "AMT_GOODS_PRICE": goods_price,
                "NAME_CONTRACT_TYPE": contract_type,
                "NAME_FAMILY_STATUS": family_status,
                "EAD": requested_credit,
                "pd_raw": live_score["pd_raw"],
                "pd_calibrated": live_score["pd_calibrated"],
                "credit_grade": live_score["credit_grade"],
                "decision_recommendation": live_score["decision_recommendation"],
            }
        )
        score_source = live_score["score_source"]

    profile_cols = st.columns(2)
    profile_cols[0].metric("Income", fmt_currency(row.get("AMT_INCOME_TOTAL")))
    profile_cols[1].metric("Credit Exposure", fmt_currency(row.get("EAD")))
    profile_cols[0].metric("Annuity", fmt_currency(row.get("AMT_ANNUITY")))
    profile_cols[1].metric("Goods Price", fmt_currency(row.get("AMT_GOODS_PRICE")))
    profile_cols[0].metric("Contract", row.get("NAME_CONTRACT_TYPE", "-"))
    profile_cols[1].metric("Family Status", row.get("NAME_FAMILY_STATUS", "-"))
    st.caption(f"Credit score source: {score_source}")

    st.subheader("Pricing Inputs")
    loan_amount = st.number_input(
        "Loan amount / EAD",
        min_value=1_000.0,
        max_value=3_000_000.0,
        value=max(safe_float(row.get("EAD"), 1_000.0), 1_000.0),
        step=10_000.0,
    )
    offered_rate = st.slider(
        "Offered annual interest rate",
        min_value=0.00,
        max_value=0.50,
        value=0.12,
        step=0.0025,
        format="%.3f",
    )
    term_months = st.selectbox("Loan term", [12, 24, 36, 48, 60], index=2)

    with st.expander("Business assumptions", expanded=False):
        a1, a2 = st.columns(2)
        funding_cost_rate = a1.slider("Funding cost", 0.00, 0.25, 0.04, 0.0025)
        operating_cost_rate = a2.slider("Operating cost", 0.00, 0.20, 0.02, 0.0025)
        target_margin_rate = a1.slider("Target margin", 0.00, 0.25, 0.03, 0.0025)
        capital_cost_rate = a2.slider("Capital cost", 0.00, 0.50, 0.08, 0.005)
        collection_cost_rate = a1.slider("Collection cost", 0.00, 0.50, 0.10, 0.005)
        tail_risk_multiplier = a2.slider("Tail risk multiplier", 0.00, 2.00, 0.35, 0.05)
        max_allowed_rate = a1.slider("Maximum allowed rate", 0.05, 0.60, 0.30, 0.005)

with right:
    st.subheader("2. Credit Risk Result")

    pd_value = safe_float(row["pd_calibrated"])
    grade = str(row.get("credit_grade", "Unrated"))
    lgd = safe_float(row.get("LGD"), lgd_from_grade(grade))
    ead = safe_float(row.get("EAD"), loan_amount)
    ecl_base = safe_float(row.get("ECL_base"), pd_value * lgd * ead)
    credit_recommendation = row.get("decision_recommendation", "-")
    ecl_base = pd_value * lgd * ead

    risk_cols = st.columns(5)
    risk_cols[0].metric("Calibrated PD", fmt_pct(pd_value))
    risk_cols[1].metric("Credit Grade", grade)
    risk_cols[2].metric("LGD", fmt_pct(lgd))
    risk_cols[3].metric("EAD", fmt_currency(ead))
    risk_cols[4].metric("ECL", fmt_currency(ecl_base))

    st.caption(f"Credit model recommendation: {credit_recommendation}")

    pricing = calculate_loan_pricing(
        loan_amount=loan_amount,
        term_months=int(term_months),
        offered_rate=float(offered_rate),
        pd_value=pd_value,
        lgd=lgd,
        funding_cost_rate=float(funding_cost_rate),
        operating_cost_rate=float(operating_cost_rate),
        target_margin_rate=float(target_margin_rate),
        capital_cost_rate=float(capital_cost_rate),
        collection_cost_rate=float(collection_cost_rate),
        tail_risk_multiplier=float(tail_risk_multiplier),
        max_allowed_rate=float(max_allowed_rate),
    )

    st.subheader("3. Pricing Recommendation")

    price_cols = st.columns(4)
    price_cols[0].metric("Required Rate", fmt_pct(pricing["required_rate"]))
    price_cols[1].metric("Offered Rate", fmt_pct(pricing["offered_rate"]))
    price_cols[2].metric("Pricing Gap", fmt_pct(pricing["pricing_gap"]))
    price_cols[3].metric("Economic Profit", fmt_currency(pricing["economic_profit"]))

    render_decision(pricing["decision"])
    st.caption(f"Pricing status: {pricing['pricing_status']}")

    profit_chart = pd.DataFrame(
        {
            "Economic Profit": {
                "Current Offer": pricing["economic_profit"],
                "If Repriced": pricing["repriced_economic_profit"],
            }
        }
    )
    st.bar_chart(profit_chart)

st.divider()

stress_col, explanation_col = st.columns(2, gap="large")

with stress_col:
    st.subheader("4. Stress Scenario / What-if")

    s1, s2 = st.columns(2)
    income_decline_pct = s1.slider(
        "Income decline",
        min_value=0,
        max_value=80,
        value=20,
        step=5,
        format="%d%%",
    )
    exposure_increase_pct = s2.slider(
        "Exposure increase",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        format="%d%%",
    )
    repayment_stress = st.selectbox(
        "Repayment behavior",
        [
            "No change",
            "Mild deterioration",
            "Repeated late payments",
            "Severe delinquency",
        ],
        index=1,
    )

    stress = apply_borrower_stress(
        base_pd=pd_value,
        base_ead=loan_amount,
        income_decline_pct=income_decline_pct,
        exposure_increase_pct=exposure_increase_pct,
        repayment_stress=repayment_stress,
    )
    stressed_ecl = stress["stressed_pd"] * lgd * stress["stressed_ead"]

    stress_metrics = st.columns(3)
    stress_metrics[0].metric(
        "Stressed PD",
        fmt_pct(stress["stressed_pd"]),
        delta=fmt_pct(stress["stressed_pd"] - pd_value),
    )
    stress_metrics[1].metric("Risk Multiplier", f"{stress['pd_multiplier']:.2f}x")
    stress_metrics[2].metric("Stressed ECL", fmt_currency(stressed_ecl))

    st.bar_chart(
        pd.DataFrame(
            {
                "Expected Loss": {
                    "Baseline": pricing["expected_loss"],
                    "Stressed": stressed_ecl,
                }
            }
        )
    )

with explanation_col:
    st.subheader("5. Explanation / Risk Drivers")

    if applicant_mode == "Existing borrower":
        risk_drivers, support_drivers = get_drivers(explanations, int(selected_borrower))
    else:
        risk_drivers, support_drivers = [], []

    if risk_drivers:
        st.markdown("**Main risk drivers**")
        for driver in risk_drivers:
            st.write(f"- {driver}")
    else:
        st.write("No borrower-level risk driver artifact is available for this application.")

    if support_drivers:
        st.markdown("**Supportive factors**")
        for driver in support_drivers:
            st.write(f"- {driver}")

    st.markdown("**Limitations**")
    st.write(
        "- Pricing is a decision-support simulation, not a regulatory pricing engine.\n"
        "- LGD is assumption-based because recovery outcomes are unavailable.\n"
        "- New-borrower scoring uses a form-based profile and a repayment-history assumption.\n"
        "- Stress testing is a what-if overlay, not a retrained model prediction.\n"
        "- Final lending action should remain subject to underwriting policy and analyst review."
    )
