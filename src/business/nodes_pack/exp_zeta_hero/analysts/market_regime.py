import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage

from nodes_pack.exp_zeta_hero import analyze_fundamentals, extract_ticker_data
from nodes_pack.yfinance_nodes import to_dict
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


def prepare_data(metric: dict):
    fundamental_analysis = analyze_fundamentals(metric)
    return {
        "ticker": metric["ticker"],
        "fundamental_analysis": fundamental_analysis,
        "market_cap": metric["market_cap"],
        "score": fundamental_analysis["score"],
        "max_score": 10,
    }


def data_to_markdown(ticker_data: dict) -> str:
    return str(ticker_data)


def call_llm(state: WorkflowState, ticker_document: str):
    return state["llm"].invoke([
        SystemMessage(
            "You are a market regime classifier for intraday trading.\n"
            "Choose exactly one: trending_up, trending_down, range_bound, volatile.\n\n"
            "SPY direction criteria:\n"
            "- up: SPY > +0.3% and above VWAP\n"
            "- down: SPY < -0.3% and below VWAP\n"
            "- flat: otherwise\n\n"
            "Be decisive. Keep reasoning to 150 chars max and strategy_bias to 100 chars max. Output JSON only."
        ),
        HumanMessage(
            ticker_document,
            "Output JSON only:\n"
            "{\n"
            '  "regime": "trending_up|trending_down|range_bound|volatile",\n'
            '  "spy_direction": "up|down|flat",\n'
            '  "confidence": float,\n'
            '  "vix_level": "low|elevated|high|extreme|null",\n'
            '  "strategy_bias": "string",\n'
            '  "reasoning": "string"\n'
            "}"
        ),
    ])


@workflow_node
def market_regime(state: WorkflowState) -> WorkflowState:
    assert "message" in state
    assert "tickers" in state["message"]

    tickers: yf.Tickers = state["message"]["tickers"]
    raw_results = {}
    results = {}
    for ticker_name in tickers.symbols:
        ticker = tickers.tickers[ticker_name]
        ticker_data = extract_ticker_data(to_dict(ticker))
        analysis_data = prepare_data(ticker_data)
        ticker_document = data_to_markdown(analysis_data)
        raw_results[ticker_name] = call_llm(state, ticker_document)
        results[ticker_name] = raw_results[ticker_name].content

    return {
        "history": [history_item("market_regime", results, output_raw=raw_results)]
    }