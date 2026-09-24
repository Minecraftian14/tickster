from langchain_core.messages import SystemMessage, HumanMessage

from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


@workflow_node
def warren_buffett(state: WorkflowState) -> WorkflowState:
    assert "message" in state
    assert "tickers" in state["message"]
    tickers = state["message"]
    response = state['llm'].invoke([
        SystemMessage(
            "You are Warren Buffett. Decide bullish, bearish, or neutral using only the provided facts.\n"
            "\n"
            "Checklist for decision:\n"
            "- Circle of competence\n"
            "- Competitive moat\n"
            "- Management quality\n"
            "- Financial strength\n"
            "- Valuation vs intrinsic value\n"
            "- Long-term prospects\n"
            "\n"
            "Signal rules:\n"
            "- Bullish: strong business AND margin_of_safety > 0.\n"
            "- Bearish: poor business OR clearly overvalued.\n"
            "- Neutral: good business but margin_of_safety <= 0, or mixed evidence.\n"
            "\n"
            "Confidence scale:\n"
            "- 90-100%: Exceptional business within my circle, trading at attractive price\n"
            "- 70-89%: Good business with decent moat, fair valuation\n"
            "- 50-69%: Mixed signals, would need more information or better price\n"
            "- 30-49%: Outside my expertise or concerning fundamentals\n"
            "- 10-29%: Poor business or significantly overvalued\n"
            "\n"
            "Keep reasoning under 120 characters. Do not invent data. Return JSON only."
        ),
        HumanMessage(
            f"{tickers}"
            "Return exactly:\n"
            "{{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": int,\n'
            '  "reasoning": "short justification"\n'
            "}}"
        ),
    ])
    return {
        'history': [history_item('warren_buffett', response.content, output_raw=response)]
    }


main_callable = warren_buffett
