import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage

from exp.exp_zeta_hero.utilities import analyze_fundamentals, extract_ticker_data
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
            "You are Charlie Munger. Using only the provided facts, choose bullish, bearish, or neutral. "
            "Output JSON only and keep the reasoning below 120 characters."
        ),
        HumanMessage(
            ticker_document,
            "Output exactly:\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": float,\n'
            '  "reasoning": "short justification"\n'
            "}"
        ),
    ])


@workflow_node
def charlie_munger(state: WorkflowState) -> WorkflowState:
    assert "message" in state and "reference" in state
    tickers: yf.Tickers = state["reference"]["output"]

    raw_results = {}
    results = {}
    for ticker_name in tickers.symbols:
        ticker = tickers.tickers[ticker_name]
        analysis_data = prepare_data(extract_ticker_data(to_dict(ticker)))
        raw_results[ticker_name] = call_llm(state, data_to_markdown(analysis_data))
        results[ticker_name] = raw_results[ticker_name].content

    return {"history": [history_item("charlie_munger", results, output_raw=raw_results)]}
