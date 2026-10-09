from typing import Any

import pandas as pd
from diskcache import Cache

from nodes_pack import make_key, ONE_DAY

cache = Cache("temp/exp_zet_hero_cache")


def _calc_growth_rate(current, previous):
    """Calculate relative growth when a valid prior value is available."""
    if current is not None and previous is not None and previous != 0:
        return (current - previous) / abs(previous)
    return None


def _coerce_number(value):
    """Convert a value to float, returning None for missing or invalid input."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _divide_if_valid(numerator, denominator):
    """Perform division only when both operands are usable and the divisor is nonzero."""
    if numerator is not None and denominator is not None and denominator != 0:
        return numerator / denominator
    return None


def _read_statement_pair(frame, *candidate_rows):
    """Read the latest and preceding values from a financial-statement DataFrame."""
    if frame is None or frame.empty:
        return None, None

    for row_name in candidate_rows:
        if row_name in frame.index:
            series = frame.loc[row_name]
            latest_value = _coerce_number(series.iloc[0])
            prior_value = _coerce_number(series.iloc[1]) if len(series) > 1 else None
            return latest_value, prior_value

    return None, None


@make_key(cache, lambda *args, **kwargs: args[0]["ticker"], expire=ONE_DAY)
def extract_ticker_data(ticker: dict) -> dict:
    """Collect market and accounting data for a security."""
    overview = ticker["info"]

    # Gather the annual statements used by the derived metrics.
    try:
        income_statement = ticker["income_statement"]
        balance_statement = ticker["balance_statement"]
        cash_statement = ticker["cash_statement"]
    except Exception:
        income_statement = balance_statement = cash_statement = None

    # Pull the latest and previous statement values needed for calculations.
    sales_now, sales_before = _read_statement_pair(
        income_statement, "Total Revenue", "Revenue"
    )
    cost_now, _ = _read_statement_pair(
        income_statement, "Cost Of Revenue", "Cost Of Goods Sold"
    )
    ebit_now, _ = _read_statement_pair(
        income_statement, "EBIT", "Operating Income"
    )
    net_profit_now, net_profit_before = _read_statement_pair(
        income_statement, "Net Income", "Net Income Common Stockholders"
    )
    interest_now, _ = _read_statement_pair(
        income_statement, "Interest Expense", "Interest Expense Non Operating"
    )
    operating_profit_now, operating_profit_before = _read_statement_pair(
        income_statement, "Operating Income", "EBIT"
    )
    ebitda_now, ebitda_before = _read_statement_pair(
        income_statement, "EBITDA", "Normalized EBITDA"
    )

    assets_now, _ = _read_statement_pair(balance_statement, "Total Assets")
    current_assets_now, _ = _read_statement_pair(balance_statement, "Current Assets")
    current_liabilities_now, _ = _read_statement_pair(
        balance_statement, "Current Liabilities"
    )
    inventory_now, _ = _read_statement_pair(balance_statement, "Inventory")
    receivables_now, _ = _read_statement_pair(
        balance_statement, "Accounts Receivable", "Net Receivables"
    )
    cash_now, _ = _read_statement_pair(
        balance_statement, "Cash And Cash Equivalents", "Cash"
    )
    debt_now, _ = _read_statement_pair(
        balance_statement, "Total Debt", "Long Term Debt"
    )
    equity_now, equity_before = _read_statement_pair(
        balance_statement, "Stockholders Equity", "Total Stockholder Equity"
    )

    operating_cash_now, _ = _read_statement_pair(
        cash_statement, "Operating Cash Flow", "Total Cash From Operating Activities"
    )
    free_cash_now, free_cash_before = _read_statement_pair(
        cash_statement, "Free Cash Flow"
    )

    # Derive per-share earnings information.
    earnings_per_share_now = _coerce_number(overview.get("trailingEps"))
    shares_outstanding = _coerce_number(overview.get("sharesOutstanding"))
    earnings_per_share_before = (
        _divide_if_valid(net_profit_before, shares_outstanding)
        if net_profit_before and shares_outstanding
        else None
    )

    # Derive book-value history.
    book_value_now = _coerce_number(overview.get("bookValue"))
    book_value_before = (
        _divide_if_valid(equity_before, shares_outstanding)
        if equity_before and shares_outstanding
        else None
    )

    # Calculate operating and liquidity ratios from the statements.
    invested_capital_return = (
        _divide_if_valid(ebit_now, (assets_now - current_liabilities_now))
        if assets_now and current_liabilities_now
        else None
    )
    asset_efficiency = _divide_if_valid(sales_now, assets_now)
    inventory_efficiency = _divide_if_valid(cost_now, inventory_now)
    collection_efficiency = _divide_if_valid(sales_now, receivables_now)
    collection_days = (
        _divide_if_valid(365.0, collection_efficiency)
        if collection_efficiency
        else None
    )
    inventory_days = (
        _divide_if_valid(365.0, inventory_efficiency)
        if inventory_efficiency
        else None
    )
    cash_conversion_cycle = (
        inventory_days + collection_days
        if inventory_days is not None and collection_days is not None
        else None
    )
    working_capital = (
        current_assets_now - current_liabilities_now
        if current_assets_now and current_liabilities_now
        else None
    )
    working_capital_efficiency = (
        _divide_if_valid(sales_now, working_capital)
        if working_capital and working_capital != 0
        else None
    )
    cash_coverage = _divide_if_valid(cash_now, current_liabilities_now)
    operating_cash_liquidity = _divide_if_valid(
        operating_cash_now, current_liabilities_now
    )
    asset_leverage = _divide_if_valid(debt_now, assets_now)
    interest_service_coverage = (
        _divide_if_valid(ebit_now, abs(interest_now))
        if interest_now and interest_now != 0
        else None
    )

    # Build growth measures.
    sales_growth = overview.get("revenueGrowth") or _calc_growth_rate(
        sales_now, sales_before
    )
    profit_growth = overview.get("earningsGrowth") or _calc_growth_rate(
        net_profit_now, net_profit_before
    )
    book_equity_growth = _calc_growth_rate(book_value_now, book_value_before)
    profit_per_share_growth = _calc_growth_rate(
        earnings_per_share_now, earnings_per_share_before
    )
    free_cash_growth = _calc_growth_rate(free_cash_now, free_cash_before)
    operating_profit_growth = _calc_growth_rate(
        operating_profit_now, operating_profit_before
    )
    operating_ebitda_growth = _calc_growth_rate(ebitda_now, ebitda_before)

    # Assemble the normalized metrics payload.
    snapshot = {
        "ticker": ticker["ticker"],
        "asset_efficiency": asset_efficiency,
        "book_equity_growth": book_equity_growth,
        "equity_value_per_share": book_value_now,
        "cash_coverage": cash_coverage,
        "quote_currency": overview.get("currency", "USD"),
        "liquidity_ratio": overview.get("currentRatio"),
        "collection_days": collection_days,
        "asset_leverage": asset_leverage,
        "leverage_ratio": overview.get("debtToEquity"),
        "profit_growth": profit_growth,
        "profit_per_share": earnings_per_share_now,
        "profit_per_share_growth": profit_per_share_growth,
        "operating_ebitda_growth": operating_ebitda_growth,
        "business_value": overview.get("enterpriseValue"),
        "business_value_to_ebitda": overview.get("enterpriseToEbitda"),
        "business_value_to_revenue": overview.get("enterpriseToRevenue"),
        "free_cash_growth": free_cash_growth,
        "cash_flow_per_share": _divide_if_valid(
            overview.get("freeCashflow"), shares_outstanding
        ),
        "cash_flow_yield": _divide_if_valid(
            overview.get("freeCashflow"), overview.get("marketCap")
        ),
        "gross_profit_margin": overview.get("grossMargins"),
        "interest_service_coverage": interest_service_coverage,
        "inventory_efficiency": inventory_efficiency,
        "market_cap": overview.get("marketCap"),
        "net_profit_margin": overview.get("profitMargins"),
        "operating_cash_liquidity": operating_cash_liquidity,
        "cash_conversion_cycle": cash_conversion_cycle,
        "operating_profit_growth": operating_profit_growth,
        "operating_profit_margin": overview.get("operatingMargins"),
        "dividend_payout": overview.get("payoutRatio"),
        "growth_adjusted_pe": overview.get("pegRatio"),
        "valuation_period": "ttm",
        "book_multiple": overview.get("priceToBook"),
        "earnings_multiple": overview.get("trailingPE"),
        "sales_multiple": overview.get("priceToSalesTrailing12Months"),
        "acid_test_ratio": overview.get("quickRatio"),
        "collection_efficiency": collection_efficiency,
        "statement_period": None,
        "asset_return": overview.get("returnOnAssets"),
        "equity_return": overview.get("returnOnEquity"),
        "invested_capital_return": invested_capital_return,
        "sales_growth": sales_growth,
        "working_capital_efficiency": working_capital_efficiency,
    }

    return snapshot


def analyze_fundamentals(metric: dict[str, Any]) -> dict[str, Any]:
    """Evaluate the company snapshot using a small set of quality checks."""
    if not metric:
        return {"quality_score": 0, "analysis_notes": "Insufficient fundamental data"}

    score = 0
    reasoning = []

    # Evaluate return on equity.
    if metric["equity_return"] and metric["equity_return"] > 0.15:
        score += 2
        reasoning.append(f"Strong ROE of {metric['equity_return']:.1%}")
    elif metric["equity_return"]:
        reasoning.append(f"Weak ROE of {metric['equity_return']:.1%}")
    else:
        reasoning.append("ROE data not available")

    # Evaluate leverage.
    if metric["leverage_ratio"] and metric["leverage_ratio"] < 0.5:
        score += 2
        reasoning.append("Conservative debt levels")
    elif metric["leverage_ratio"]:
        reasoning.append(
            f"High debt to equity ratio of {metric['leverage_ratio']:.1f}"
        )
    else:
        reasoning.append("Debt to equity data not available")

    # Evaluate operating profitability.
    if metric["operating_profit_margin"] and metric["operating_profit_margin"] > 0.15:
        score += 2
        reasoning.append("Strong operating margins")
    elif metric["operating_profit_margin"]:
        reasoning.append(
            f"Weak operating margin of {metric['operating_profit_margin']:.1%}"
        )
    else:
        reasoning.append("Operating margin data not available")

    # Evaluate short-term liquidity.
    if metric["liquidity_ratio"] and metric["liquidity_ratio"] > 1.5:
        score += 1
        reasoning.append("Good liquidity position")
    elif metric["liquidity_ratio"]:
        reasoning.append(
            f"Weak liquidity with current ratio of {metric['liquidity_ratio']:.1f}"
        )
    else:
        reasoning.append("Current ratio data not available")

    return {
        "score": score,
        "details": "; ".join(reasoning),
        "metrics": str(metric),
    }


def compose_ticker_report(ticker: dict) -> str:
    """Placeholder for turning a ticker payload into a report string."""
    pass
