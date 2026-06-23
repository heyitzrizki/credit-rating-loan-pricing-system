import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_currency, format_pct, format_pd, load_data_objects

st.set_page_config(page_title="ECL & Macro Stress Testing", layout="wide")

data = load_data_objects()

portfolio_ecl = data.get("portfolio_ecl_base", pd.DataFrame()).copy()
ecl_grade_summary = data.get("ecl_grade_summary", pd.DataFrame()).copy()
macro_stress_summary = data.get("macro_stress_summary", pd.DataFrame()).copy()
severe_portfolio = data.get("portfolio_ecl_severe_downturn", pd.DataFrame()).copy()

st.title("ECL & Macro Stress Testing")
st.caption(
    "Expected Credit Loss simulation using calibrated PD, rating-based LGD, EAD proxy, and macroeconomic stress scenarios"
)

if portfolio_ecl.empty or macro_stress_summary.empty:
    st.error(
        "ECL artifacts are missing. Please rerun the notebook section "
        "'Expected Credit Loss and Macro Stress Testing Layer' and regenerate artifacts."
    )
    st.stop()

st.markdown(
    """
    <style>
        .section-note {
            color: #B9C0CB;
            font-size: 0.97rem;
            margin-top: -0.2rem;
            margin-bottom: 1rem;
        }
        .insight-box {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 1rem 1rem 0.75rem 1rem;
            margin-bottom: 0.8rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Base Portfolio KPIs

base_total_ead = portfolio_ecl["EAD"].sum()
base_total_ecl = portfolio_ecl["ECL_base"].sum()
base_avg_pd = portfolio_ecl["pd_calibrated"].mean()
base_avg_lgd = portfolio_ecl["LGD"].mean()
base_ecl_ratio = base_total_ecl / base_total_ead if base_total_ead > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Total EAD", format_currency(base_total_ead, 0))
k2.metric("Base ECL", format_currency(base_total_ecl, 0))
k3.metric("Avg PD", format_pd(base_avg_pd, 4))
k4.metric("Avg LGD", format_pct(base_avg_lgd, 1))
k5.metric("ECL / EAD", format_pct(base_ecl_ratio, 2))

st.markdown("")

# Scenario Selector

st.markdown("### Macro Scenario Analysis")
st.markdown(
    '<div class="section-note">Compare portfolio-level Expected Credit Loss under baseline and stressed macroeconomic assumptions.</div>',
    unsafe_allow_html=True,
)

scenario_options = macro_stress_summary["scenario"].astype(str).tolist()

selected_scenario = st.selectbox(
    "Select macro scenario",
    options=scenario_options,
    index=scenario_options.index("Severe Downturn") if "Severe Downturn" in scenario_options else 0,
)

selected_row = macro_stress_summary[
    macro_stress_summary["scenario"].astype(str) == selected_scenario
].iloc[0]

s1, s2, s3, s4 = st.columns(4)

s1.metric("Scenario Total ECL", format_currency(selected_row["total_ecl"], 0))
s2.metric("ECL Uplift", format_currency(selected_row["ecl_uplift"], 0))
s3.metric("ECL Uplift %", format_pct(selected_row["ecl_uplift_pct"], 1))
s4.metric("Scenario Avg PD", format_pd(selected_row["avg_pd"], 4))

# Scenario Charts

chart_df = macro_stress_summary.copy()
chart_df["scenario"] = chart_df["scenario"].astype(str)

c1, c2 = st.columns((1.15, 1))

with c1:
    st.markdown("### Total ECL by Scenario")

    fig_ecl = px.bar(
        chart_df,
        x="scenario",
        y="total_ecl",
        text="total_ecl",
    )
    fig_ecl.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_ecl.update_layout(
        xaxis_title="Scenario",
        yaxis_title="Total Expected Credit Loss",
        showlegend=False,
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_ecl, use_container_width=True)

with c2:
    st.markdown("### ECL Uplift by Scenario")

    uplift_df = chart_df[chart_df["scenario"] != "Baseline"].copy()

    fig_uplift = px.bar(
        uplift_df,
        x="scenario",
        y="ecl_uplift_pct",
        text="ecl_uplift_pct",
    )
    fig_uplift.update_traces(texttemplate="%{text:.1%}", textposition="outside")
    fig_uplift.update_layout(
        xaxis_title="Scenario",
        yaxis_title="ECL Uplift (%)",
        showlegend=False,
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_uplift, use_container_width=True)

# ECL by Credit Grade

st.markdown("### Base ECL by Credit Grade")
st.markdown(
    '<div class="section-note">Rating-level decomposition of exposure and expected credit loss.</div>',
    unsafe_allow_html=True,
)

if not ecl_grade_summary.empty:
    grade_df = ecl_grade_summary.copy()
    grade_df["credit_grade"] = grade_df["credit_grade"].astype(str)

    g1, g2 = st.columns(2)

    with g1:
        fig_grade_ecl = px.bar(
            grade_df,
            x="credit_grade",
            y="total_ecl",
            text="total_ecl",
        )
        fig_grade_ecl.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig_grade_ecl.update_layout(
            xaxis_title="Credit Grade",
            yaxis_title="Total ECL",
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False,
        )
        st.plotly_chart(fig_grade_ecl, use_container_width=True)

    with g2:
        fig_grade_share = px.pie(
            grade_df,
            names="credit_grade",
            values="ecl_share",
            hole=0.55,
        )
        fig_grade_share.update_layout(
            height=400,
            margin=dict(l=20, r=20, t=20, b=20),
            legend_title_text="Credit Grade",
        )
        st.plotly_chart(fig_grade_share, use_container_width=True)

    display_grade = grade_df.copy()

    for col in ["avg_pd", "avg_lgd", "ead_share", "ecl_share"]:
        if col in display_grade.columns:
            display_grade[col] = display_grade[col].map(lambda x: f"{x:.2%}")

    for col in ["total_ead", "total_ecl", "avg_ecl"]:
        if col in display_grade.columns:
            display_grade[col] = display_grade[col].map(lambda x: f"{x:,.0f}")

    with st.expander("View ECL summary by credit grade"):
        st.dataframe(display_grade, use_container_width=True, hide_index=True)

else:
    st.info("ECL grade summary artifact is not available.")

# Stress Testing Interpretation

st.markdown("### Stress Testing Interpretation")

baseline_rows = chart_df[chart_df["scenario"] == "Baseline"]
baseline_ecl = baseline_rows["total_ecl"].iloc[0] if not baseline_rows.empty else base_total_ecl
worst_row = chart_df.sort_values("total_ecl", ascending=False).iloc[0]

i1, i2, i3 = st.columns(3)

with i1:
    st.markdown(
        f"""
        <div class="insight-box">
            <b>Base loss expectation</b><br><br>
            Under the baseline condition, the portfolio generates an estimated ECL of
            <b>{baseline_ecl:,.0f}</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

with i2:
    st.markdown(
        f"""
        <div class="insight-box">
            <b>Most severe scenario</b><br><br>
            The highest loss estimate appears under <b>{worst_row['scenario']}</b>,
            with total ECL of <b>{worst_row['total_ecl']:,.0f}</b>.
        </div>
        """,
        unsafe_allow_html=True,
    )

with i3:
    st.markdown(
        f"""
        <div class="insight-box">
            <b>Stress uplift</b><br><br>
            In the selected scenario, ECL increases by
            <b>{selected_row['ecl_uplift_pct']:.1%}</b> compared with baseline.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Methodology

with st.expander("Methodology note"):
    st.markdown(
        """
        **ECL framework:**  
        Expected Credit Loss is calculated as:

        `ECL = PD × LGD × EAD`

        **PD:** calibrated probability of default from the credit rating model.  

        **LGD:** rating-based assumption because actual recovery, write-off, and collateral liquidation outcomes are not available in the Home Credit dataset.  

        **EAD:** proxy based on approved credit exposure.  

        **Macro stress testing:** scenario-based adjustment using literature-informed sensitivity coefficients. These coefficients are not estimated from the Home Credit dataset and should be interpreted as simulation assumptions.
        """
    )

# Borrower-Level Table

with st.expander("View borrower-level base ECL table"):
    table_cols = [
        "SK_ID_CURR",
        "pd_calibrated",
        "credit_grade",
        "LGD",
        "EAD",
        "ECL_base",
    ]

    available_cols = [c for c in table_cols if c in portfolio_ecl.columns]
    table_df = portfolio_ecl[available_cols].head(500).copy()

    if "pd_calibrated" in table_df.columns:
        table_df["pd_calibrated"] = table_df["pd_calibrated"].map(lambda x: f"{x:.4f}")

    if "LGD" in table_df.columns:
        table_df["LGD"] = table_df["LGD"].map(lambda x: f"{x:.1%}")

    for col in ["EAD", "ECL_base"]:
        if col in table_df.columns:
            table_df[col] = table_df[col].map(lambda x: f"{x:,.0f}")

    st.dataframe(table_df, use_container_width=True, hide_index=True)