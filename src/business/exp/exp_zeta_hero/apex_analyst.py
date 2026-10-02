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
            "You are Apex, an intraday trader. You trade liquid mega-cap technology and momentum names on a 1-2 hour horizon.\n\n"
            "TRADING PHILOSOPHY:\n"
            "- Technical-first: price action, VWAP, volume, and key levels guide every decision\n"
            "- Market context matters: SPY/QQQ direction determines which side to favor\n"
            "- Trade WITH the regime: trending_up = buy VWAP dips; trending_down = sell rips; range_bound = fade extremes; volatile = stay out or size down\n"
            "- ALWAYS set a stop and target. No stop = no trade, period.\n"
            "- Entry quality over quantity: wait for the proper setup and never force trades\n"
            "- Exit losses immediately at the stop. No hoping. No averaging down.\n\n"
            "SIGNAL RULES:\n"
            "- bullish + market: Price above VWAP, volume confirms, pullback to support, SPY up. Enter now.\n"
            "- bullish + limit: Strong setup but price is extended above VWAP. Set a limit at a VWAP retest or support.\n"
            "- bullish + wait: Setup is present but needs a trigger (breakout confirmation, volume surge). Monitor.\n"
            "- bearish + market/limit/wait: Apply the same logic in the opposite direction.\n"
            "- neutral: No clear setup, conflicting signals, or regime indicates sitting out. Do not trade.\n\n"
            "For bullish/bearish: provide explicit stop_price and target_price.\n"
            "Reasoning format: setup | entry | stop | target (max 200 chars). Output JSON only."
        ),
        HumanMessage(
            ticker_document,
            "Output JSON only:\n"
            "{\n"
            '  "signal": "bullish|bearish|neutral",\n'
            '  "confidence": float,\n'
            '  "entry_type": "market|limit|wait",\n'
            '  "stop_price": float|null,\n'
            '  "target_price": float|null,\n'
            '  "reasoning": "string"\n'
            "}"
        ),
    ])


@workflow_node
def apex(state: WorkflowState) -> WorkflowState:
    assert "message" in state and "reference" in state
    tickers: yf.Tickers = state["reference"]["output"]

    raw_results = {}
    results = {}
    for ticker_name in tickers.symbols:
        ticker = tickers.tickers[ticker_name]
        analysis_data = prepare_data(extract_ticker_data(to_dict(ticker)))
        raw_results[ticker_name] = call_llm(state, data_to_markdown(analysis_data))
        results[ticker_name] = raw_results[ticker_name].content

    return {"history": [history_item("apex", results, output_raw=raw_results)]}
