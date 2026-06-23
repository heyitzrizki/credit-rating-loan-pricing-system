import pandas as pd
import streamlit as st

from utils import (
    assign_credit_grade_from_summary,
    assign_decision_from_grade,
    assign_grade_group,
    build_existing_borrower_sequence,
    format_currency,
    format_pct,
    get_tcn_embedding,
    load_data_objects,
    load_models,
    preprocess_static_row,
    score_borrower,
)

st.set_page_config(page_title="Borrower Rating & Stress Scenario", layout="wide")

xgb_model, platt, encoder, _ = load_models()
data = load_data_objects()

risk_table = data["risk_table"].copy()
grade_summary = data["credit_grade_summary"].copy()
borrower_profile_ui = data["borrower_profile_ui"].copy()
borrower_explanation_summary = data.get("borrower_explanation_summary", pd.DataFrame())
portfolio_ecl = data.get("portfolio_ecl_base", pd.DataFrame())

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
            padding: 1.1rem 1.15rem 0.95rem 1.15rem;
            margin-bottom: 1rem;
        }
        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.55rem;
        }
        .muted {
            color: #B7BFCA;
            font-size: 0.96rem;
            line-height: 1.65;
        }
        .profile-label {
            color: #97A1AE;
            font-size: 0.85rem;
            margin-bottom: 0.15rem;
        }
        .profile-value {
            font-size: 1.02rem;
            font-weight: 600;
            margin-bottom: 0.8rem;
        }
        .pill {
            display: inline-block;
            padding: 0.38rem 0.72rem;
            border-radius: 999px;
            margin-right: 0.45rem;
            margin-bottom: 0.4rem;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            font-size: 0.9rem;
            color: #D9DEE7;
        }
        .footnote-box {
            background: rgba(255,255,255,0.03);
            border-left: 4px solid rgba(255,255,255,0.22);
            border-radius: 10px;
            padding: 0.9rem 1rem;
            margin-top: 0.5rem;
            margin-bottom: 1rem;
        }
        .warning-box {
            background: rgba(255, 193, 7, 0.08);
            border: 1px solid rgba(255, 193, 7, 0.22);
            border-radius: 14px;
            padding: 1rem;
            margin-bottom: 1rem;
            color: #F4E4B3;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Borrower Rating & Stress Scenario")
st.caption(
    "Review an existing borrower’s credit rating, then apply stress assumptions to see how risk, rating, and expected loss may change."
)


# ============================================================
# Helper functions
# ============================================================

def fmt_num(x, digits=2):
    if pd.isna(x):
        return "-"
    return f"{x:.{digits}f}"


def years_from_negative_days(x):
    if pd.isna(x):
        return None
    return abs(float(x)) / 365.25


def flag_to_yes_no(value):
    return "Yes" if str(value).upper() == "Y" else "No"


def humanize_feature_name(feature_name: str) -> str:
    """
    Convert raw Home Credit / engineered feature names into business-friendly labels.
    Local fallback to avoid deployment import-cache issues.
    """
    if pd.isna(feature_name):
        return "-"

    name = str(feature_name)

    feature_map = {
        # Core Home Credit application variables
        "EXT_SOURCE_1": "External credit score 1",
        "EXT_SOURCE_2": "External credit score 2",
        "EXT_SOURCE_3": "External credit score 3",
        "DAYS_BIRTH": "Borrower age",
        "DAYS_EMPLOYED": "Employment length",
        "DAYS_REGISTRATION": "Time since registration",
        "DAYS_ID_PUBLISH": "Time since ID document update",
        "DAYS_LAST_PHONE_CHANGE": "Time since phone number change",
        "AMT_INCOME_TOTAL": "Income amount",
        "AMT_CREDIT": "Credit amount",
        "AMT_ANNUITY": "Regular payment amount",
        "AMT_GOODS_PRICE": "Goods price",
        "CNT_CHILDREN": "Number of children",
        "CNT_FAM_MEMBERS": "Family size",
        "CODE_GENDER": "Gender",
        "FLAG_OWN_CAR": "Car ownership",
        "FLAG_OWN_REALTY": "Property ownership",
        "NAME_INCOME_TYPE": "Income type",
        "NAME_EDUCATION_TYPE": "Education level",
        "NAME_FAMILY_STATUS": "Family status",
        "NAME_HOUSING_TYPE": "Housing type",
        "NAME_CONTRACT_TYPE": "Loan contract type",
        "OCCUPATION_TYPE": "Occupation type",
        "ORGANIZATION_TYPE": "Employer organization type",
        "REGION_RATING_CLIENT": "Region risk rating",
        "REGION_RATING_CLIENT_W_CITY": "Region risk rating with city",

        # Bureau / previous credit variables
        "AMT_CREDIT_SUM": "Total previous credit amount",
        "AMT_CREDIT_SUM_DEBT": "Outstanding debt from previous credit",
        "AMT_CREDIT_SUM_LIMIT": "Previous credit limit",
        "AMT_CREDIT_SUM_OVERDUE": "Overdue amount from previous credit",
        "CREDIT_DAY_OVERDUE": "Days overdue on previous credit",
        "DAYS_CREDIT": "Time since previous credit application",
        "DAYS_CREDIT_ENDDATE": "Remaining time to previous credit end date",
        "DAYS_ENDDATE_FACT": "Actual previous credit closing time",
        "CNT_CREDIT_PROLONG": "Number of previous credit prolongations",

        # Engineered temporal features
        "inst_late_rate": "Late repayment pattern",
        "inst_underpay_rate": "Underpayment pattern",
        "inst_payment_ratio_mean": "Average repayment completion ratio",
        "inst_payment_delay_mean": "Average repayment delay",
        "pos_dpd_max": "Maximum POS loan delinquency",
        "pos_dpd_mean": "Average POS loan delinquency",
        "cc_dpd_max": "Maximum credit card delinquency",
        "cc_dpd_mean": "Average credit card delinquency",
        "cc_balance_mean": "Average credit card balance",
        "cc_drawings_mean": "Average credit card usage",
        "cc_payment_ratio_mean": "Average credit card repayment ratio",
        "bureau_any_delinquent": "Previous credit delinquency flag",
        "bureau_debt_ratio": "Previous credit debt burden",
        "bureau_active_credit_count": "Number of active previous credits",

        # Missing indicators
        "EXT_SOURCE_1_is_missing": "Missing external credit score 1",
        "EXT_SOURCE_2_is_missing": "Missing external credit score 2",
        "EXT_SOURCE_3_is_missing": "Missing external credit score 3",
        "AMT_ANNUITY_is_missing": "Missing regular payment amount",
        "DAYS_EMPLOYED_is_missing": "Missing employment history",
    }

    if name in feature_map:
        return feature_map[name]

    categorical_prefixes = {
        "NAME_INCOME_TYPE_": "Income type",
        "NAME_EDUCATION_TYPE_": "Education level",
        "NAME_FAMILY_STATUS_": "Family status",
        "NAME_HOUSING_TYPE_": "Housing type",
        "NAME_CONTRACT_TYPE_": "Loan contract type",
        "OCCUPATION_TYPE_": "Occupation type",
        "ORGANIZATION_TYPE_": "Employer organization type",
        "CODE_GENDER_": "Gender",
        "FLAG_OWN_CAR_": "Car ownership",
        "FLAG_OWN_REALTY_": "Property ownership",
    }

    for prefix, label in categorical_prefixes.items():
        if name.startswith(prefix):
            value = name.replace(prefix, "").replace("_", " ")
            return f"{label}: {value}"

    cleaned = name.replace("_is_missing", " missing")
    cleaned = cleaned.replace("_", " ").strip()
    return cleaned.title()


def lgd_by_grade(grade: str) -> float:
    mapping = {
        "AAA": 0.25,
        "AA": 0.25,
        "A": 0.25,
        "BBB": 0.40,
        "BB": 0.40,
        "B": 0.55,
        "CCC": 0.55,
        "CC": 0.70,
        "C": 0.70,
        "D": 0.70,
    }
    return mapping.get(str(grade), 0.55)


def apply_borrower_stress(
    base_pd: float,
    income_decline_pct: float,
    exposure_increase_pct: float,
    employment_stress: str,
    repayment_stress: str,
) -> tuple[float, float]:
    """
    Apply scenario-based stress assumptions to borrower-level estimated default risk.

    This is not a newly trained model. It is a what-if overlay on top of the existing borrower rating.
    """
    multiplier = 1.0

    multiplier *= 1 + (income_decline_pct / 100) * 1.20
    multiplier *= 1 + (exposure_increase_pct / 100) * 0.80

    employment_multiplier = {
        "No change": 1.00,
        "Mild instability": 1.15,
        "Job transition / unstable income": 1.35,
        "Unemployed / income interruption": 1.70,
    }

    repayment_multiplier = {
        "No change": 1.00,
        "Mild deterioration": 1.25,
        "Repeated late payments": 1.70,
        "Severe delinquency": 2.40,
    }

    multiplier *= employment_multiplier.get(employment_stress, 1.00)
    multiplier *= repayment_multiplier.get(repayment_stress, 1.00)

    stressed_pd = min(base_pd * multiplier, 0.95)

    return stressed_pd, multiplier


def get_existing_borrower_score(selected_borrower):
    borrower_row_full = data["app_static"][
        data["app_static"]["SK_ID_CURR"] == selected_borrower
    ].copy()

    static_raw = borrower_row_full.drop(
        columns=[c for c in ["SK_ID_CURR", "TARGET"] if c in borrower_row_full.columns]
    )

    static_processed = preprocess_static_row(static_raw, data)

    seq, mask = build_existing_borrower_sequence(selected_borrower, data)
    embedding, attn = get_tcn_embedding(encoder, seq, mask)

    raw_pd, calibrated_pd = score_borrower(
        static_processed,
        embedding,
        xgb_model,
        platt,
        data["emb_cols_v2"],
    )

    return raw_pd, calibrated_pd, attn


def render_profile_card(profile_row: pd.Series):
    age = years_from_negative_days(profile_row.get("DAYS_BIRTH"))
    employment_years = years_from_negative_days(profile_row.get("DAYS_EMPLOYED"))

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            '<div class="section-card"><div class="section-title">Identity & Application</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Borrower ID</div><div class="profile-value">{profile_row.get("SK_ID_CURR", "-")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Contract Type</div><div class="profile-value">{profile_row.get("NAME_CONTRACT_TYPE", "-")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Gender</div><div class="profile-value">{profile_row.get("CODE_GENDER", "-")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Age</div><div class="profile-value">{fmt_num(age, 1)} years</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(
            '<div class="section-card"><div class="section-title">Financial Profile</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Income</div><div class="profile-value">{format_currency(profile_row.get("AMT_INCOME_TOTAL"))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Credit Amount</div><div class="profile-value">{format_currency(profile_row.get("AMT_CREDIT"))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Regular Payment</div><div class="profile-value">{format_currency(profile_row.get("AMT_ANNUITY"))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Goods Price</div><div class="profile-value">{format_currency(profile_row.get("AMT_GOODS_PRICE"))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown(
            '<div class="section-card"><div class="section-title">Household & Stability</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Family Status</div><div class="profile-value">{profile_row.get("NAME_FAMILY_STATUS", "-")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Children</div><div class="profile-value">{profile_row.get("CNT_CHILDREN", "-")}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Own Car</div><div class="profile-value">{flag_to_yes_no(profile_row.get("FLAG_OWN_CAR", "N"))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Own Property</div><div class="profile-value">{flag_to_yes_no(profile_row.get("FLAG_OWN_REALTY", "N"))}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with c4:
        st.markdown(
            '<div class="section-card"><div class="section-title">External Risk Signals</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">External Score 1</div><div class="profile-value">{fmt_num(profile_row.get("EXT_SOURCE_1"), 3)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">External Score 2</div><div class="profile-value">{fmt_num(profile_row.get("EXT_SOURCE_2"), 3)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">External Score 3</div><div class="profile-value">{fmt_num(profile_row.get("EXT_SOURCE_3"), 3)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="profile-label">Employment Length</div><div class="profile-value">{fmt_num(employment_years, 1)} years</div>',
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def render_explanation_block(sk_id):
    st.markdown("### Main Risk Drivers")

    st.markdown(
        """
        <div class="footnote-box">
            This section summarizes the borrower-level factors that most increased or reduced the model's
            estimated default risk. These drivers are explanation support only and should not be interpreted
            as causal proof.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if borrower_explanation_summary.empty:
        st.info("Main risk driver explanation is not available for this deployment artifact.")
        return

    explain_row = borrower_explanation_summary[
        borrower_explanation_summary["SK_ID_CURR"] == sk_id
    ]

    if explain_row.empty:
        st.info(
            "No borrower-level explanation summary was generated for this borrower. "
            "The rating and recommendation are still available, but detailed driver analysis is unavailable."
        )
        return

    explain_row = explain_row.iloc[0]

    e1, e2 = st.columns(2)

    with e1:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Factors Increasing Risk</div>
                <div class="muted">These variables pushed the borrower toward a higher estimated default risk.</div><br>
            """,
            unsafe_allow_html=True,
        )

        found = False
        for col in ["top_1_risk_driver", "top_2_risk_driver", "top_3_risk_driver"]:
            val = explain_row.get(col, None)
            if pd.notna(val) and val is not None:
                found = True
                st.markdown(
                    f'<span class="pill">{humanize_feature_name(val)}</span>',
                    unsafe_allow_html=True,
                )

        if not found:
            st.markdown(
                '<div class="muted">No risk-increasing driver available.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

    with e2:
        st.markdown(
            """
            <div class="section-card">
                <div class="section-title">Factors Reducing Risk</div>
                <div class="muted">These variables helped reduce the borrower's estimated default risk.</div><br>
            """,
            unsafe_allow_html=True,
        )

        found = False
        for col in ["top_1_support_driver", "top_2_support_driver", "top_3_support_driver"]:
            val = explain_row.get(col, None)
            if pd.notna(val) and val is not None:
                found = True
                st.markdown(
                    f'<span class="pill">{humanize_feature_name(val)}</span>',
                    unsafe_allow_html=True,
                )

        if not found:
            st.markdown(
                '<div class="muted">No risk-reducing driver available.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)


def render_baseline_result(raw_pd, calibrated_pd, credit_grade, decision, grade_group, actual_default=None):
    m1, m2, m3, m4, m5 = st.columns(5)

    m1.metric("Model Risk Score", f"{raw_pd:.4f}")
    m2.metric("Estimated Default Risk", f"{calibrated_pd:.2%}")
    m3.metric("Credit Grade", credit_grade)
    m4.metric("Recommendation", decision)
    m5.metric("Risk Segment", grade_group)

    observed_text = ""
    if actual_default is not None:
        observed_text = (
            "<br><br>Observed outcome in test data: "
            f"<b>{'Repayment difficulty' if int(actual_default) == 1 else 'No repayment difficulty'}</b>."
        )

    st.markdown(
        f"""
        <div class="footnote-box">
            <b>How to read the result:</b><br>
            The system estimates this borrower's probability of repayment difficulty and maps it into a credit grade.
            This borrower is assigned to <b>{credit_grade}</b>, categorized as <b>{grade_group}</b>,
            with a recommended action of <b>{decision}</b>.
            {observed_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# Main borrower selector
# ============================================================

borrower_options = borrower_profile_ui["SK_ID_CURR"].tolist()

selected_borrower = st.selectbox(
    "Select borrower ID",
    borrower_options,
    help="Choose an existing borrower from the portfolio.",
)

borrower_profile_row = borrower_profile_ui[
    borrower_profile_ui["SK_ID_CURR"] == selected_borrower
].copy()

if borrower_profile_row.empty:
    st.error("Borrower profile not found.")
    st.stop()

borrower_profile_row = borrower_profile_row.iloc[0]

raw_pd, base_pd, attn = get_existing_borrower_score(selected_borrower)

base_grade = assign_credit_grade_from_summary(base_pd, grade_summary)
base_decision = assign_decision_from_grade(base_grade)
base_group = assign_grade_group(base_grade)

borrower_rank_row = risk_table[risk_table["SK_ID_CURR"] == selected_borrower]
actual_default = (
    borrower_rank_row["actual_default"].iloc[0]
    if not borrower_rank_row.empty and "actual_default" in borrower_rank_row.columns
    else None
)

st.markdown("### Baseline Borrower Rating")

render_baseline_result(
    raw_pd=raw_pd,
    calibrated_pd=base_pd,
    credit_grade=base_grade,
    decision=base_decision,
    grade_group=base_group,
    actual_default=actual_default,
)

st.markdown("### Borrower Profile")
render_profile_card(borrower_profile_row)

render_explanation_block(selected_borrower)


# ============================================================
# Borrower stress scenario
# ============================================================

st.markdown("### Borrower Stress Scenario")

st.markdown(
    """
    <div class="warning-box">
        <b>Scenario logic:</b><br>
        This is not a new-borrower application form. The scenario starts from the selected existing borrower
        and applies stress assumptions such as income decline, higher exposure, unstable employment, or worse repayment behavior.
        It is designed for what-if analysis and decision support.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.form("borrower_stress_form"):
    s1, s2 = st.columns(2)

    income_decline_pct = s1.slider(
        "Income decline",
        min_value=0,
        max_value=80,
        value=20,
        step=5,
        format="%d%%",
        help="Assumed decline in borrower income under stress.",
    )

    exposure_increase_pct = s2.slider(
        "Credit exposure increase",
        min_value=0,
        max_value=100,
        value=10,
        step=5,
        format="%d%%",
        help="Assumed increase in exposure or utilization under stress.",
    )

    employment_stress = s1.selectbox(
        "Employment condition",
        [
            "No change",
            "Mild instability",
            "Job transition / unstable income",
            "Unemployed / income interruption",
        ],
        index=1,
    )

    repayment_stress = s2.selectbox(
        "Repayment behavior scenario",
        [
            "No change",
            "Mild deterioration",
            "Repeated late payments",
            "Severe delinquency",
        ],
        index=1,
    )

    submitted = st.form_submit_button("Apply stress scenario")

if submitted:
    stressed_pd, pd_multiplier = apply_borrower_stress(
        base_pd=base_pd,
        income_decline_pct=income_decline_pct,
        exposure_increase_pct=exposure_increase_pct,
        employment_stress=employment_stress,
        repayment_stress=repayment_stress,
    )

    stressed_grade = assign_credit_grade_from_summary(stressed_pd, grade_summary)
    stressed_decision = assign_decision_from_grade(stressed_grade)
    stressed_group = assign_grade_group(stressed_grade)

    base_lgd = lgd_by_grade(base_grade)
    stressed_lgd = lgd_by_grade(stressed_grade)

    if not portfolio_ecl.empty:
        borrower_ecl_row = portfolio_ecl[portfolio_ecl["SK_ID_CURR"] == selected_borrower]

        if not borrower_ecl_row.empty:
            borrower_ecl_row = borrower_ecl_row.iloc[0]
            base_ead = float(borrower_ecl_row.get("EAD", borrower_profile_row.get("AMT_CREDIT", 0)))
        else:
            base_ead = float(borrower_profile_row.get("AMT_CREDIT", 0))
    else:
        base_ead = float(borrower_profile_row.get("AMT_CREDIT", 0))

    stressed_ead = base_ead * (1 + exposure_increase_pct / 100)

    base_ecl = base_pd * base_lgd * base_ead
    stressed_ecl = stressed_pd * stressed_lgd * stressed_ead
    ecl_change = stressed_ecl - base_ecl
    ecl_change_pct = ecl_change / base_ecl if base_ecl > 0 else 0

    st.markdown("### Stress Scenario Result")

    r1, r2, r3, r4 = st.columns(4)

    r1.metric(
        "Estimated Default Risk",
        f"{stressed_pd:.2%}",
        delta=f"{(stressed_pd - base_pd):.2%}",
    )
    r2.metric("Credit Grade", stressed_grade, delta=f"{base_grade} → {stressed_grade}")
    r3.metric("Recommendation", stressed_decision, delta=f"{base_decision} → {stressed_decision}")
    r4.metric("Risk Multiplier", f"{pd_multiplier:.2f}x")

    st.markdown("### Expected Loss Impact")

    e1, e2, e3, e4 = st.columns(4)

    e1.metric("Baseline Expected Loss", format_currency(base_ecl))
    e2.metric("Stressed Expected Loss", format_currency(stressed_ecl))
    e3.metric("Expected Loss Increase", format_currency(ecl_change))
    e4.metric("Expected Loss Increase %", format_pct(ecl_change_pct, 1))

    st.markdown("### Scenario Interpretation")

    st.markdown(
        f"""
        <div class="footnote-box">
            Under the selected stress scenario, the borrower's estimated default risk changes from
            <b>{base_pd:.2%}</b> to <b>{stressed_pd:.2%}</b>.
            The credit grade migrates from <b>{base_grade}</b> to <b>{stressed_grade}</b>,
            and the recommended action changes from <b>{base_decision}</b> to <b>{stressed_decision}</b>.
            <br><br>
            The expected loss changes from <b>{base_ecl:,.0f}</b> to <b>{stressed_ecl:,.0f}</b>.
            This scenario is a decision-support simulation, not a retrained model prediction.
        </div>
        """,
        unsafe_allow_html=True,
    )

with st.expander("Technical detail: model attention over repayment history"):
    st.caption(
        "This table is mainly for technical review. Higher attention weight means the model focused more on that monthly history step."
    )
    attn_df = pd.DataFrame(
        {
            "History Step": list(range(1, len(attn) + 1)),
            "Model Attention Weight": attn,
        }
    )
    st.dataframe(attn_df, use_container_width=True, hide_index=True)