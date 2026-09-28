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
        "ticker": metric['ticker'],
        "fundamental_analysis": fundamental_analysis,
        "market_cap": metric['market_cap'],
        "max_score": max_possible_score,
        "score": total_score,
    }


def data_to_markdown(ticker_data: dict) -> str:
    return str(ticker_data)


def call_llm(state: WorkflowState, ticker_document: str):
    return state['llm'].invoke([
        SystemMessage(
            "You are Warren Buffett. Based only on the supplied facts, select bullish, bearish, or neutral.\n"
            "\n"
            "Decision checklist:\n"
            "- Circle of competence\n"
            "- Durable competitive moat\n"
            "- Management quality\n"
            "- Financial strength\n"
            "- Valuation relative to intrinsic value\n"
            "- Long-term outlook\n"
            "\n"
            "Signal criteria:\n"
            "- Bullish: strong business AND margin_of_safety > 0.\n"
            "- Bearish: weak business OR clearly overvalued.\n"
            "- Neutral: good business but margin_of_safety <= 0, or the evidence is mixed.\n"
            "\n"
            "Confidence scale:\n"
            "- 90-100%: Exceptional business within my circle, trading at an attractive price\n"
            "- 70-89%: Good business with a durable moat, fairly valued\n"
            "- 50-69%: Mixed signals; more information or a better price is needed\n"
            "- 30-49%: Outside my expertise or the fundamentals are concerning\n"
            "- 10-29%: Poor business or materially overvalued\n"
            "\n"
            "Keep reasoning under 120 characters. Do not invent data. Output JSON only."
        ),
        HumanMessage(
<<<<<<< HEAD
            f"{tickers}"
            "Output precisely:\n"
=======
            ticker_document,
            "Output exactly:\n"
>>>>>>> 3764cda ([CHKPT] exp_zeta_hero)
            "{{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": int,\n'
            '  "reasoning": "brief justification"\n'
            "}}"
        ),
    ])


@workflow_node
def warren_buffett(state: WorkflowState) -> WorkflowState:
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
        'history': [history_item('warren_buffett', results, output_raw=raw_results)]
    }
