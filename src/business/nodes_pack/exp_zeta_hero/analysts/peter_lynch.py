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
            "You are an AI agent applying Peter Lynch's approach.\n"
            "Use Lynch principles: invest in what you know, GARP/PEG, ten-bagger potential, steady growth, low debt, and a strong company story.\n"
            "Use practical, plainspoken reasoning and take a clear stance. Output JSON only."
        ),
        HumanMessage(
            ticker_document,
            "Return valid JSON using:\n"
            "{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": float (0-100),\n'
            '  "reasoning": "string"\n'
            "}"
        ),
    ])


@workflow_node
def peter_lynch(state: WorkflowState) -> WorkflowState:
    assert "message" in state and "tickers" in state["message"]
    tickers: yf.Tickers = state["message"]["tickers"]

    raw_results = {}
    results = {}
    for ticker_name in tickers.symbols:
        ticker = tickers.tickers[ticker_name]
        analysis_data = prepare_data(extract_ticker_data(to_dict(ticker)))
        raw_results[ticker_name] = call_llm(state, data_to_markdown(analysis_data))
        results[ticker_name] = raw_results[ticker_name].content

    return {"history": [history_item("peter_lynch", results, output_raw=raw_results)]}