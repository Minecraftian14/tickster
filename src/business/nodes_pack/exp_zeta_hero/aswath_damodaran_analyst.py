import yfinance as yf
from langchain_core.messages import SystemMessage, HumanMessage

from nodes_pack.exp_zeta_hero.utilities import analyze_fundamentals, extract_ticker_data
from nodes_pack.yfinance_nodes import to_dict
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


def prepare_data(metric: dict):
    fundamental_analysis = analyze_fundamentals(metric)

    total_score = fundamental_analysis["score"]
    max_possible_score = 10

    return {
        "ticker": metric["ticker"],
        "fundamental_analysis": fundamental_analysis,
        "market_cap": metric["market_cap"],
        "max_score": max_possible_score,
        "score": total_score,
    }


def data_to_markdown(ticker_data: dict) -> str:
    return str(ticker_data)


def call_llm(state: WorkflowState, ticker_document: str):
    return state["llm"].invoke([
        SystemMessage(
            "You are Aswath Damodaran, Professor of Finance at NYU Stern.\n"
            "Apply your valuation framework to generate trading signals on US equities.\n"
            "\n"
            "Use your normal clear, data-driven style:\n"
            '- Begin with the company "story" qualitatively\n'
            "- Link that story to the key numerical drivers: revenue growth, margins, reinvestment, and risk\n"
            "- Finish with value: your FCFF DCF estimate, margin of safety, and relative-valuation sanity checks\n"
            "- Call out major uncertainties and explain how they influence value\n"
            "Output ONLY the JSON specified below."
        ),
        HumanMessage(
            ticker_document,
            "Respond in EXACTLY this JSON schema:\n"
            "{{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": float (0-100),\n'
            '  "reasoning": "string"\n'
            "}}"
        ),
    ])


@workflow_node
def aswath_damodaran(state: WorkflowState) -> WorkflowState:
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
        "history": [history_item("aswath_damodaran", results, output_raw=raw_results)]
    }
