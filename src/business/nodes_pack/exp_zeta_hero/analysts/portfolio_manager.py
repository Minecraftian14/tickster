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
            "You are a portfolio manager.\n"
            "Choose one action and quantity for each ticker.\n"
            "Keep reasoning concise (max 100 chars). Do not do cash or margin math. Output JSON only.\n"
            "For a strong buy/sell thesis, you may include bracket fields: stop_price/take_profit."
        ),
        HumanMessage(
            ticker_document,
            "Output JSON:\n"
            "{\n"
            '  "decisions": {\n'
            '    "TICKER": {"action":"...","quantity":int,"confidence":int,"reasoning":"...",'
            '"order_type":"market","stop_price":null,"take_profit":null,"limit_price":null}\n'
            "  }\n"
            "}"
        ),
    ])


@workflow_node
def portfolio_manager(state: WorkflowState) -> WorkflowState:
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
        "history": [history_item("portfolio_manager", results, output_raw=raw_results)]
    }