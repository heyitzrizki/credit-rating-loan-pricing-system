LGD_BY_GRADE = {
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


def lgd_from_grade(grade: str) -> float:
    return LGD_BY_GRADE.get(str(grade), 0.55)


def calculate_loan_pricing(
    loan_amount: float,
    term_months: int,
    offered_rate: float,
    pd_value: float,
    lgd: float,
    funding_cost_rate: float,
    operating_cost_rate: float,
    target_margin_rate: float,
    capital_cost_rate: float,
    collection_cost_rate: float,
    tail_risk_multiplier: float,
    pricing_tolerance: float = 0.01,
    max_allowed_rate: float = 0.30,
) -> dict:
    """Risk-based loan pricing layer using calibrated PD from the credit model."""
    term_years = term_months / 12
    ead = loan_amount

    expected_loss = pd_value * lgd * ead
    lifetime_el_rate = pd_value * lgd
    annualized_el_rate = lifetime_el_rate / term_years

    required_rate = (
        funding_cost_rate
        + operating_cost_rate
        + annualized_el_rate
        + target_margin_rate
    )
    required_rate_capped = min(required_rate, max_allowed_rate)
    pricing_gap = offered_rate - required_rate

    if pricing_gap < -pricing_tolerance:
        pricing_status = "Underpriced"
    elif pricing_gap <= pricing_tolerance:
        pricing_status = "Fairly Priced"
    else:
        pricing_status = "Overpriced"

    interest_income = ead * offered_rate * term_years
    funding_cost = ead * funding_cost_rate * term_years
    operating_cost = ead * operating_cost_rate * term_years
    expected_profit = interest_income - funding_cost - operating_cost - expected_loss

    capital_requirement = ead * pd_value * lgd
    capital_charge = capital_requirement * capital_cost_rate * term_years
    collection_cost = expected_loss * collection_cost_rate
    tail_risk_penalty = ead * (pd_value**2) * lgd * tail_risk_multiplier
    economic_profit = (
        expected_profit - capital_charge - collection_cost - tail_risk_penalty
    )
    economic_return = economic_profit / ead if ead else 0

    repriced_interest_income = ead * required_rate_capped * term_years
    repriced_expected_profit = (
        repriced_interest_income - funding_cost - operating_cost - expected_loss
    )
    repriced_economic_profit = (
        repriced_expected_profit - capital_charge - collection_cost - tail_risk_penalty
    )
    repriced_economic_return = repriced_economic_profit / ead if ead else 0

    if economic_profit >= 0 and required_rate <= max_allowed_rate:
        decision = "Approve"
    elif repriced_economic_profit >= 0 and required_rate <= max_allowed_rate:
        decision = "Approve if Repriced"
    elif required_rate > max_allowed_rate and pd_value < 0.25:
        decision = "Manual Review"
    else:
        decision = "Reject"

    return {
        "loan_amount": loan_amount,
        "term_months": term_months,
        "term_years": term_years,
        "pd": pd_value,
        "lgd": lgd,
        "ead": ead,
        "offered_rate": offered_rate,
        "required_rate": required_rate,
        "required_rate_capped": required_rate_capped,
        "pricing_gap": pricing_gap,
        "pricing_status": pricing_status,
        "expected_loss": expected_loss,
        "lifetime_el_rate": lifetime_el_rate,
        "annualized_el_rate": annualized_el_rate,
        "interest_income": interest_income,
        "funding_cost": funding_cost,
        "operating_cost": operating_cost,
        "expected_profit": expected_profit,
        "capital_requirement": capital_requirement,
        "capital_charge": capital_charge,
        "collection_cost": collection_cost,
        "tail_risk_penalty": tail_risk_penalty,
        "economic_profit": economic_profit,
        "economic_return": economic_return,
        "repriced_expected_profit": repriced_expected_profit,
        "repriced_economic_profit": repriced_economic_profit,
        "repriced_economic_return": repriced_economic_return,
        "decision": decision,
    }


def apply_borrower_stress(
    base_pd: float,
    base_ead: float,
    income_decline_pct: float,
    exposure_increase_pct: float,
    repayment_stress: str,
) -> dict:
    """Scenario overlay for borrower-level what-if analysis."""
    multiplier = 1.0
    multiplier *= 1 + (income_decline_pct / 100) * 1.20
    multiplier *= 1 + (exposure_increase_pct / 100) * 0.80

    repayment_multiplier = {
        "No change": 1.00,
        "Mild deterioration": 1.25,
        "Repeated late payments": 1.70,
        "Severe delinquency": 2.40,
    }
    multiplier *= repayment_multiplier.get(repayment_stress, 1.00)

    stressed_pd = min(base_pd * multiplier, 0.95)
    stressed_ead = base_ead * (1 + exposure_increase_pct / 100)

    return {
        "stressed_pd": stressed_pd,
        "stressed_ead": stressed_ead,
        "pd_multiplier": multiplier,
    }


def safe_float(value, fallback=0.0) -> float:
    if value is None:
        return fallback

    try:
        if bool(value != value):
            return fallback
    except Exception:
        if str(value).strip().lower() in {"", "nan", "none", "<na>"}:
            return fallback

    return float(value)
