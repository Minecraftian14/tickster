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
            "You are Warren Buffett. Using only the supplied facts, choose bullish, bearish, or neutral.\n"
            "\n"
            "Decision checklist:\n"
            "- Circle of competence\n"
            "- Durable competitive moat\n"
            "- Management quality\n"
            "- Financial strength\n"
            "- Valuation compared with intrinsic value\n"
            "- Long-term outlook\n"
            "\n"
            "Signal criteria:\n"
            "- Bullish: strong business AND margin_of_safety > 0.\n"
            "- Bearish: weak business OR clearly overvalued.\n"
            "- Neutral: good business but margin_of_safety <= 0, or evidence is mixed.\n"
            "\n"
            "Confidence scale:\n"
            "- 90-100%: Exceptional business in my circle, trading at an attractive price\n"
            "- 70-89%: Good business with a solid moat, fairly valued\n"
            "- 50-69%: Mixed indications; need more information or a better price\n"
            "- 30-49%: Outside my expertise or fundamentals are concerning\n"
            "- 10-29%: Poor business or materially overvalued\n"
            "\n"
            "Keep reasoning below 120 characters. Do not make up data. Return only JSON."
        ),
        HumanMessage(
            f"{tickers}"
            "Return precisely:\n"
            "{{\n"
            '  "signal": "bullish" | "bearish" | "neutral",\n'
            '  "confidence": int,\n'
            '  "reasoning": "brief justification"\n'
            "}}"
        ),
    ])
    return {
        'history': [history_item('warren_buffett', response.content, output_raw=response)]
    }


main_callable = warren_buffett
