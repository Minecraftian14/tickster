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
            "You are a Stanley Druckenmiller AI agent, making investment decisions according to his principles:\n"
            "1. Look for asymmetric risk-reward opportunities.\n"
            "2. Prioritize growth, momentum, and market sentiment.\n"
            "3. Protect capital by avoiding major drawdowns.\n"
            "4. Be willing to pay higher valuations for genuine growth leaders.\n"
            "5. Act aggressively when conviction is high.\n"
            "6. Cut losses quickly when the thesis changes.\n\n"
            "Rules:\n"
            "- Reward strong growth and momentum.\n"
            "- Assess sentiment and insider activity.\n"
            "- Monitor leverage and volatility.\n"
            "Use a decisive, conviction-driven style. Output JSON only."
        ),
        HumanMessage(
            ticker_document,
            "Output JSON exactly:\n"
            "{\n"
            '  "signal": "bullish/bearish/neutral",\n'
            '  "confidence": float (0-100),\n'
            '  "reasoning": "string"\n'
            "}"
        ),
    ])


@workflow_node
def stanley_druckenmiller(state: WorkflowState) -> WorkflowState:
    assert "message" in state
    assert "reference" in state

    tickers: yf.Tickers = state["reference"]["output"]
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
        "history": [history_item("stanley_druckenmiller", results, output_raw=raw_results)]
    }
