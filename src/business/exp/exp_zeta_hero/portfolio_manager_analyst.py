from langchain_core.messages import SystemMessage, HumanMessage

from exp.exp_zeta_hero.utilities import analyze_fundamentals
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
    assert "reference" in state

    references = state["reference"]
    ticker_document = data_to_markdown(references)
    raw_result = call_llm(state, ticker_document)

    return {
        "history": [history_item("portfolio_manager", raw_result.content, output_raw=raw_result)]
    }
