import sqlite3
import pandas as pd

from typing import TypedDict
from textwrap import dedent, indent
from pydantic import BaseModel, Field

from dotenv import load_dotenv
load_dotenv()

from gai_providers import OPENROUTER_CONFIG

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_openrouter import ChatOpenRouter
import yfinance as yf


class State(TypedDict):
    message: str
    response: str
    data: str


llm = ChatOpenRouter(
    model="openrouter/free",
    temperature=0,
    api_key=OPENROUTER_CONFIG["default"],
)

def clean(message):
    return dedent(message).strip()

def message(state):
    return '' if 'message' not in state else f'Additional Notes:\n{indent(state['message'], " " * 8)}'

def parse_list(content):
    return list(map(str.strip, content.split(",")))

def collect_stock_data(ticker: yf.Ticker) -> dict:
    info = ticker.info
    fast = ticker.fast_info
    history = ticker.history(period="1y", auto_adjust=False)
    price = fast.get("last_price")
    market_cap = fast.get("market_cap")
    if price is None and not history.empty:
        price = history["Close"].iloc[-1]
    return_1y = None
    volatility = None
    if len(history) > 1:
        first_price = history["Close"].iloc[0]
        last_price = history["Close"].iloc[-1]
        return_1y = (last_price / first_price) - 1
        volatility = history["Close"].pct_change().std() * (252 ** 0.5)
    income = ticker.income_stmt
    cashflow = ticker.cashflow
    balance = ticker.balance_sheet
    def latest(df, field):
        try:
            if field in df.index and not df.empty:
                value = df.loc[field].iloc[0]
                return None if pd.isna(value) else value
        except Exception:
            pass
        return None
    revenue = latest(income, "Total Revenue")
    operating_income = latest(income, "Operating Income")
    net_income = latest(income, "Net Income")
    diluted_eps = latest(income, "Diluted EPS")
    gross_profit = latest(income, "Gross Profit")
    cash = latest(balance, "Cash Cash Equivalents And Short Term Investments")
    if cash is None:
        cash = latest(balance, "Cash And Cash Equivalents")
    debt = latest(balance, "Total Debt")
    operating_cashflow = latest(cashflow, "Operating Cash Flow")
    capex = latest(cashflow, "Capital Expenditure")
    free_cash_flow = None
    if operating_cashflow is not None and capex is not None:
        free_cash_flow = operating_cashflow + capex
        # Yahoo usually reports CapEx as a negative number.
    def growth(df, field):
        try:
            if field in df.index:
                values = df.loc[field].dropna()
                if len(values) >= 2:
                    current = values.iloc[0]
                    previous = values.iloc[1]
                    if previous != 0:
                        return (current / previous) - 1
        except Exception:
            pass

        return None
    revenue_growth = growth(income, "Total Revenue")
    eps_growth = growth(income, "Diluted EPS")
    fcf_growth = None
    try:
        ocf = cashflow.loc["Operating Cash Flow"].dropna()
        cap = cashflow.loc["Capital Expenditure"].dropna()
        if len(ocf) >= 2 and len(cap) >= 2:
            fcf_current = ocf.iloc[0] + cap.iloc[0]
            fcf_previous = ocf.iloc[1] + cap.iloc[1]

            if fcf_previous != 0:
                fcf_growth = (fcf_current / fcf_previous) - 1
    except Exception:
        pass
    gross_margin = ( gross_profit / revenue if gross_profit is not None and revenue else None )
    operating_margin = ( operating_income / revenue if operating_income is not None and revenue else None )
    net_margin = ( net_income / revenue if net_income is not None and revenue else None )
    net_cash = None
    if cash is not None and debt is not None: net_cash = cash - debt
    valuation = {
        "pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "ev_ebitda": info.get("enterpriseToEbitda"),
    }
    return {
        "company": info.get("longName") or info.get("shortName"),
        "ticker": info.get("symbol"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "price": price,
        "market_cap": market_cap,
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "revenue_growth": revenue_growth,
        "eps_growth": eps_growth,
        "fcf_growth": fcf_growth,
        "gross_margin": gross_margin,
        "operating_margin": operating_margin,
        "net_margin": net_margin,
        "cash": cash,
        "debt": debt,
        "free_cash_flow": free_cash_flow,
        "net_cash": net_cash,
        **valuation,
        "return_1y": return_1y,
        "volatility": volatility,
        "analyst_target": ticker.analyst_price_targets,
        "recommendations": ticker.recommendations_summary,
        "news": ticker.news[:3] if ticker.news else [],
    }

def stock_to_markdown(data: dict) -> str:
    def money(value):
        if value is None: return "N/A"
        abs_value = abs(value)
        if abs_value >= 1e12: return f"${value / 1e12:.2f}T"
        if abs_value >= 1e9:  return f"${value / 1e9:.2f}B"
        if abs_value >= 1e6:  return f"${value / 1e6:.2f}M"
        return f"${value:,.0f}"
    def pct(value):
        return "N/A" if value is None else f"{value:.1%}"
    def number(value):
        return "N/A" if value is None else f"{value:.2f}"
    md = clean(f"""
        # {data['company']} ({data['ticker']})

        **Sector:** {data['sector'] or 'N/A'}  
        **Industry:** {data['industry'] or 'N/A'}

        ## Snapshot

        | Metric | Value |
        |---|---:|
        | Price | {money(data['price'])} |
        | Market Cap | {money(data['market_cap'])} |
        | 52-week High | {money(data['52w_high'])} |
        | 52-week Low | {money(data['52w_low'])} |
        | 1-year Return | {pct(data['return_1y'])} |
        | Annualized Volatility | {pct(data['volatility'])} |

        ## Growth

        | Metric | Value |
        |---|---:|
        | Revenue Growth | {pct(data['revenue_growth'])} |
        | EPS Growth | {pct(data['eps_growth'])} |
        | FCF Growth | {pct(data['fcf_growth'])} |

        ## Profitability

        | Metric | Value |
        |---|---:|
        | Gross Margin | {pct(data['gross_margin'])} |
        | Operating Margin | {pct(data['operating_margin'])} |
        | Net Margin | {pct(data['net_margin'])} |

        ## Financial Health

        | Metric | Value |
        |---|---:|
        | Cash | {money(data['cash'])} |
        | Debt | {money(data['debt'])} |
        | Free Cash Flow | {money(data['free_cash_flow'])} |
        | Net Cash / (Debt) | {money(data['net_cash'])} |

        ## Valuation

        | Metric | Value |
        |---|---:|
        | P/E | {number(data['pe'])} |
        | Forward P/E | {number(data['forward_pe'])} |
        | EV / EBITDA | {number(data['ev_ebitda'])} |

    """)

    if data["analyst_target"] is not None:
        target = data["analyst_target"]
        md += "## Analyst Expectations\n\n"
        for key in ("current", "low", "high", "mean", "median"):
            if key in target:
                md += f"| {key.title()} Target | {money(target[key])} |\n"
        md += "\n"

    if data["news"] and len(data["news"]) > 0:
        md += "## Recent Developments\n\n"
        for item in data["news"]:
            title = item.get("title")
            if title:
                md += f"- {title}\n"
        md += "\n"

    return md

def agent_1_shortlist(state: State):
    company_data = None
    if 'data' in state and isinstance(state['data'], pd.DataFrame):
        company_data = state['data']
        state['data'] = None
    else:
        company_data = yf.Sector("technology", region="IN").top_companies
    response = llm.invoke(clean(f'''
        You are a market specialist.
        You will be given a table of top growing companies.
        You need to make a shortlist of one, few or all the companies given.
        Your output should be strictly be of the format of a comma separated list of the 'symbol' from the table.
        {message(state)}
        Top Growing Companies:
        {str(company_data)}
    '''))
    symbols = parse_list(response.content)
    symbols = [s for s in symbols if s in company_data.index]
    return { "response": response.content, "data": symbols }


class CompanySpec(BaseModel):
    symbol: str = Field(description="The company symbol.")
    potential: float = Field(description="A score from 0 to 3 indicating how much potential profits does investing in this company hold.")
    risk: float = Field(description="A score from 0 to 3 indicating the risk factor.")
    stability: float = Field(description="A score from 0 to 3 hinting towards how stable its future is going to be.")
    factor: float = Field(description="A weight factor between 0 to 1 to define if we invest in this company, how much of the whole capital should be allocated to this company stocks.")


class CompanySpecs(BaseModel):
    specs: list[CompanySpec] = Field(description="List of company spec (symbol, potential, risk, stability, factor).")


company_specs_llm = llm.with_structured_output(CompanySpecs, include_raw=True)


def agent_2_analysis(state: State):
    if 'data' not in state or not isinstance(state['data'], list) or len(state['data']) == 0:
        raise ValueError("No company symbold provided!")
    tickers = yf.Tickers(" ".join(state['data']))
    ticker_reports = []
    for symbol in tickers.symbols:
        ticker = tickers.tickers[symbol]
        ticker_reports.append(stock_to_markdown(collect_stock_data(ticker)))
    result = company_specs_llm.invoke(clean(f'''
        You are a market analyst.
        You will be given a series of companies and related metrics.
        Please generate the response as described.
        {message(state['data'])}
        Companies Reports:\n\n{indent("\n\n".join(ticker_reports), " " * 8)}
    '''))
    try:
        specs = result['parsed']
        factor_sum = sum(s.factor for s in specs.specs)
        for s in specs.specs: s.factor /= factor_sum
        return { "data": specs }
    except Exception as e:
        print("RESULT")
        print(result)
        raise e


class GTTTrade(BaseModel):
    symbol: str = Field(description="The company symbol.")
    quantity: int = Field(description="Number of shares to buy or sell.")
    entry_price: float = Field(description="Price at or below which the entry order should be triggered.")
    stop_loss: float = Field(description="Price at which the position should be sold to limit the loss.")
    target_sell: float = Field(description="Price at which the position should be sold to take the target profit.")


class GTTTrades(BaseModel):
    trades: list[GTTTrade] = Field(description="List of company spec.")


gtt_trades_llm = llm.with_structured_output(GTTTrades)


def agent_3_generation(state: State):
    if 'data' not in state or not isinstance(state['data'], CompanySpecs):
        raise ValueError("No company specs provided!")
    result = gtt_trades_llm.invoke(clean(f'''
        You are a trading specialist.
        You will be given a series of chosen companies, each populated with a bunch of useful metrics.
        These metrics include:
        * potential: A score from 0 to 3 indicating how much potential profits does investing in this company hold.
        * risk: A score from 0 to 3 indicating the risk factor.
        * stability: A score from 0 to 3 hinting towards how stable its future is going to be.
        * factor: A weight factor between 0 to 1 to define if we invest in this company, how much of the whole capital should be allocated to this company stocks.
        Your task is to allocate a budget of 10000 into the given companies, while generating whole GTT trade configs for each company.
        {message(state)}
        Companie Specs:
        {state['data'].model_dump_json()}
    '''))
    return { "data": result }

def test_gai_prototype_2():
    graph_builder = StateGraph(State)

    graph_builder.add_node("shortlist", agent_1_shortlist)
    graph_builder.add_node("analysis", agent_2_analysis)
    graph_builder.add_node("generation", agent_3_generation)

    graph_builder.add_edge(START, "shortlist")
    graph_builder.add_edge("shortlist", "analysis")
    graph_builder.add_edge("analysis", "generation")
    graph_builder.add_edge("generation", END)

    conn = sqlite3.connect("temp/checkpoints.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    graph = graph_builder.compile(checkpointer=checkpointer)

    state = {}
    state = graph.invoke(state, config={
        "configurable": {
            "thread_id": "test_gai_prototype_2"
        }
    })
    trades = state['data'].trades
    print()
    for trade in trades:
        print("# Company", trade.symbol)
        print("* Quantity", trade.quantity)
        print("* Target Entry Price", trade.entry_price)
        print("* Stop Loss", trade.stop_loss)
        print("* Target Sell", trade.target_sell)
