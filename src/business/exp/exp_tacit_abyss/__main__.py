"""Optional demonstration wiring; production orchestration is outside this package."""

from langgraph.graph import END, START, StateGraph

from exp.exp_tacit_abyss.aggressive_risk_analyst import aggressive_risk_analyst
from exp.exp_tacit_abyss.bear_researcher import bear_researcher
from exp.exp_tacit_abyss.bull_researcher import bull_researcher
from exp.exp_tacit_abyss.conservative_risk_analyst import conservative_risk_analyst
from exp.exp_tacit_abyss.fundamentals_analyst import fundamentals_analyst
from exp.exp_tacit_abyss.market_analyst import market_analyst
from exp.exp_tacit_abyss.neutral_risk_analyst import neutral_risk_analyst
from exp.exp_tacit_abyss.news_analyst import news_analyst
from exp.exp_tacit_abyss.portfolio_manager import portfolio_manager
from exp.exp_tacit_abyss.research_manager import research_manager
from exp.exp_tacit_abyss.sentiment_analyst import sentiment_analyst
from exp.exp_tacit_abyss.trader import trader
from tickster.workflow.state import WorkflowState, history_item


def _context_ready(state: WorkflowState):
    """Seed reference before parallel nodes so workflow wrappers do not race on it."""
    return {"reference": state.get("reference") or history_item("context_ready", "Shared context is available through message['context']")}


def build_demo_graph(*, research_rounds: int = 1, risk_rounds: int = 1):
    """Build the source-inspired graph without adding persistent state or execution."""
    if research_rounds < 1 or risk_rounds < 1:
        raise ValueError("research_rounds and risk_rounds must be at least one")
    graph = StateGraph(WorkflowState)
    graph.add_node("context_ready", _context_ready)
    graph.add_edge(START, "context_ready")
    analysts = (market_analyst, fundamentals_analyst, news_analyst, sentiment_analyst)
    for node in analysts:
        graph.add_node(node.__name__, node)
        graph.add_edge("context_ready", node.__name__)
    previous = [node.__name__ for node in analysts]
    for index in range(research_rounds):
        bull_name, bear_name = f"bull_{index}", f"bear_{index}"
        graph.add_node(bull_name, bull_researcher)
        graph.add_node(bear_name, bear_researcher)
        graph.add_edge(previous, bull_name)
        graph.add_edge(bull_name, bear_name)
        previous = bear_name
    graph.add_node("research_manager", research_manager)
    graph.add_node("trader", trader)
    graph.add_edge(previous, "research_manager")
    graph.add_edge("research_manager", "trader")
    previous = "trader"
    for index in range(risk_rounds):
        aggressive, conservative, neutral = f"aggressive_{index}", f"conservative_{index}", f"neutral_{index}"
        graph.add_node(aggressive, aggressive_risk_analyst)
        graph.add_node(conservative, conservative_risk_analyst)
        graph.add_node(neutral, neutral_risk_analyst)
        graph.add_edge(previous, aggressive)
        graph.add_edge(aggressive, conservative)
        graph.add_edge(conservative, neutral)
        previous = neutral
    graph.add_node("portfolio_manager", portfolio_manager)
    graph.add_edge(previous, "portfolio_manager")
    graph.add_edge("portfolio_manager", END)
    return graph.compile()


if __name__ == "__main__":
    print("Start")
    from nodes_pack.data_elements.collect_data.__main__ import collect_data

    data = collect_data("PINELABS", scale='HIG')
    dataset = data['dataset']['PINE LABS LIMITED']
    from tickster.workflow.state import create_state

    state = create_state(model='liquid/lfm-2.5-2.6b:free')
    state['message'] = {"context": dataset}
    state: WorkflowState = build_demo_graph().invoke(state)
    print(state['history'][-1]['output'])
