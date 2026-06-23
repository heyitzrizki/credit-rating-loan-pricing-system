import pandas as pd
import plotly.express as px
import streamlit as st

from utils import format_pct, load_data_objects

st.set_page_config(page_title="High-Risk Watchlist", layout="wide")

data = load_data_objects()
risk_table = data["risk_table"].copy()

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1400px;
        }
        .section-note {
            color: #B9C0CB;
            font-size: 0.97rem;
            margin-top: -0.2rem;
            margin-bottom: 1rem;
        }
        .action-box {
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 16px;
            padding: 1rem 1rem 0.75rem 1rem;
            margin-bottom: 0.8rem;
        }
        .pill {
            display: inline-block;
            padding: 0.36rem 0.7rem;
            border-radius: 999px;
            margin-right: 0.45rem;
            margin-bottom: 0.4rem;
            background: rgba(255,255,255,0.06);
            border: 1px solid rgba(255,255,255,0.08);
            font-size: 0.9rem;
            color: #D9DEE7;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("High-Risk Watchlist")
st.caption(
    "Operational review list for borrowers with elevated estimated repayment risk."
)

required_cols = [
    "SK_ID_CURR",
    "pd_calibrated",
    "actual_default",
    "credit_grade",
    "decision_recommendation",
    "portfolio_percentile",
]

missing_cols = [col for col in required_cols if col not in risk_table.columns]

if missing_cols:
    st.error(
        f"The review list cannot be displayed because the risk table is missing these columns: {missing_cols}. "
        "Please regenerate the notebook artifacts first."
    )
    st.stop()

if "risk_priority_flag" not in risk_table.columns:
    def make_priority(row):
        grade = str(row.get("credit_grade", ""))
        pd_value = row.get("pd_calibrated", 0)

        if grade in ["D", "CC", "C"] or pd_value >= 0.25:
            return "Immediate Review"
        if grade in ["CCC", "B"] or pd_value >= 0.15:
            return "Manual Underwriting"
        if grade in ["BB", "BBB"] or pd_value >= 0.07:
            return "Analyst Review"
        return "Routine Monitoring"

    risk_table["risk_priority_flag"] = risk_table.apply(make_priority, axis=1)

risk_table["credit_grade"] = risk_table["credit_grade"].astype(str)
risk_table["decision_recommendation"] = risk_table["decision_recommendation"].astype(str)
risk_table["risk_priority_flag"] = risk_table["risk_priority_flag"].astype(str)

st.markdown("### Review Filters")
st.caption(
    "Use these filters to narrow the list of borrowers that may require analyst review, manual underwriting, or tighter credit checks."
)

f1, f2, f3, f4 = st.columns(4)

min_risk = f1.slider(
    "Show borrowers with estimated risk above",
    min_value=0.0,
    max_value=1.0,
    value=0.05,
    step=0.01,
    format="%.2f",
    help=(
        "This filter shows borrowers whose estimated probability of repayment difficulty is above the selected level. "
        "For example, 0.10 means borrowers with estimated default risk above 10%."
    ),
)

top_n = f2.slider(
    "Number of borrowers to display",
    min_value=10,
    max_value=300,
    value=50,
    step=10,
)

grade_order = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
available_grades = risk_table["credit_grade"].dropna().astype(str).unique().tolist()
grade_options = [g for g in grade_order if g in available_grades] + [
    g for g in sorted(available_grades) if g not in grade_order
]

selected_grades = f3.multiselect(
    "Credit grade",
    options=grade_options,
    default=grade_options,
)

priority_order = [
    "Immediate Review",
    "Manual Underwriting",
    "Analyst Review",
    "Routine Monitoring",
]

available_priorities = risk_table["risk_priority_flag"].dropna().astype(str).unique().tolist()
priority_options = [p for p in priority_order if p in available_priorities] + [
    p for p in sorted(available_priorities) if p not in priority_order
]

selected_priorities = f4.multiselect(
    "Review priority",
    options=priority_options,
    default=priority_options,
)

show_defaults_only = st.checkbox(
    "Show only borrowers who actually had repayment difficulty in the test data",
    value=False,
)

filtered = risk_table.copy()

filtered = filtered[
    (filtered["pd_calibrated"] >= min_risk)
    & (filtered["credit_grade"].isin(selected_grades))
    & (filtered["risk_priority_flag"].isin(selected_priorities))
]

if show_defaults_only:
    filtered = filtered[filtered["actual_default"] == 1]

filtered = filtered.sort_values("pd_calibrated", ascending=False).reset_index(drop=True)
filtered_display = filtered.head(top_n).copy()

if filtered.empty:
    st.warning("No borrowers match the current filter settings.")
    st.stop()

st.markdown("### Review List Summary")

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Borrowers in Review List", f"{len(filtered):,}")
k2.metric("Avg Estimated Default Risk", format_pct(filtered["pd_calibrated"].mean(), 1))
k3.metric("Observed Difficulty Rate", format_pct(filtered["actual_default"].mean(), 1))
k4.metric("Portfolio Share", format_pct(len(filtered) / len(risk_table), 1))

high_risk_grades = ["B", "CCC", "CC", "C", "D"]
k5.metric(
    "High-Risk Grade Count",
    f"{int(filtered['credit_grade'].isin(high_risk_grades).sum()):,}",
)

c1, c2 = st.columns(2)

with c1:
    st.markdown("### Review List by Credit Grade")
    st.markdown(
        '<div class="section-note">Borrower concentration across credit grades inside the filtered review list.</div>',
        unsafe_allow_html=True,
    )

    grade_dist = (
        filtered.groupby("credit_grade", as_index=False)
        .size()
        .rename(columns={"size": "borrower_count"})
    )

    grade_dist["credit_grade"] = pd.Categorical(
        grade_dist["credit_grade"],
        categories=grade_order,
        ordered=True,
    )
    grade_dist = grade_dist.sort_values("credit_grade")

    fig_grade = px.bar(
        grade_dist,
        x="credit_grade",
        y="borrower_count",
        text="borrower_count",
    )
    fig_grade.update_traces(textposition="outside")
    fig_grade.update_layout(
        xaxis_title="Credit Grade",
        yaxis_title="Borrower Count",
        showlegend=False,
        height=380,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_grade, use_container_width=True)

with c2:
    st.markdown("### Estimated Default Risk Distribution")
    st.markdown(
        '<div class="section-note">Distribution of estimated repayment difficulty risk inside the review list.</div>',
        unsafe_allow_html=True,
    )

    fig_hist = px.histogram(
        filtered,
        x="pd_calibrated",
        nbins=20,
    )
    fig_hist.update_layout(
        xaxis_title="Estimated Default Risk",
        yaxis_title="Borrower Count",
        showlegend=False,
        height=380,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

st.markdown("### Operational Priorities")

priority_counts = (
    filtered.groupby("risk_priority_flag", as_index=False)
    .size()
    .rename(columns={"size": "borrower_count"})
)

priority_count_map = dict(
    zip(priority_counts["risk_priority_flag"], priority_counts["borrower_count"])
)

immediate_count = int(priority_count_map.get("Immediate Review", 0))
manual_count = int(priority_count_map.get("Manual Underwriting", 0))
analyst_count = int(priority_count_map.get("Analyst Review", 0))

a1, a2, a3 = st.columns(3)

with a1:
    st.markdown(
        f"""
        <div class="action-box">
            <b>Immediate Review</b><br><br>
            <span class="pill">Count: {immediate_count:,}</span><br>
            Borrowers in this group should be prioritized for urgent analyst review or additional verification.
        </div>
        """,
        unsafe_allow_html=True,
    )

with a2:
    st.markdown(
        f"""
        <div class="action-box">
            <b>Manual Underwriting</b><br><br>
            <span class="pill">Count: {manual_count:,}</span><br>
            Borrowers in this group may require manual underwriting and tighter credit checks before approval.
        </div>
        """,
        unsafe_allow_html=True,
    )

with a3:
    st.markdown(
        f"""
        <div class="action-box">
            <b>Analyst Review</b><br><br>
            <span class="pill">Count: {analyst_count:,}</span><br>
            Borrowers in this group should be monitored or reviewed depending on supporting documentation.
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("### Borrower Review Table")
st.markdown(
    '<div class="section-note">Filtered borrower list sorted by highest estimated default risk.</div>',
    unsafe_allow_html=True,
)

table_cols = [
    "SK_ID_CURR",
    "pd_calibrated",
    "credit_grade",
    "decision_recommendation",
    "risk_priority_flag",
    "portfolio_percentile",
    "actual_default",
]

available_cols = [col for col in table_cols if col in filtered_display.columns]
watchlist_table = filtered_display[available_cols].copy()

rename_map = {
    "SK_ID_CURR": "Borrower ID",
    "pd_calibrated": "Estimated Default Risk",
    "credit_grade": "Credit Grade",
    "decision_recommendation": "Recommended Action",
    "risk_priority_flag": "Review Priority",
    "portfolio_percentile": "Risk Percentile",
    "actual_default": "Observed Difficulty",
}

watchlist_table = watchlist_table.rename(columns=rename_map)

if "Estimated Default Risk" in watchlist_table.columns:
    watchlist_table["Estimated Default Risk"] = watchlist_table[
        "Estimated Default Risk"
    ].map(lambda x: f"{x:.2%}")

if "Risk Percentile" in watchlist_table.columns:
    watchlist_table["Risk Percentile"] = watchlist_table[
        "Risk Percentile"
    ].map(lambda x: f"{x:.1%}")

if "Observed Difficulty" in watchlist_table.columns:
    watchlist_table["Observed Difficulty"] = watchlist_table[
        "Observed Difficulty"
    ].map(lambda x: "Yes" if int(x) == 1 else "No")

st.dataframe(watchlist_table, use_container_width=True, hide_index=True)

with st.expander("How to interpret this page"):
    st.markdown(
        """
        **Estimated default risk** represents the model's estimated probability that a borrower may face repayment difficulty.

        **Review priority** translates the model output into an operational queue:
        - **Immediate Review**: strongest review priority
        - **Manual Underwriting**: elevated-risk cases that need additional checking
        - **Analyst Review**: cases that may need business or policy review
        - **Routine Monitoring**: lower-priority cases

        **Observed difficulty** is only available because this is a back-testing dataset. In a real deployment, this outcome would not be known at the time of scoring.
        """
    )