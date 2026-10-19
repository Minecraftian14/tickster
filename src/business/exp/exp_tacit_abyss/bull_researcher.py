from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from .utilities import model_update, outputs, role_prompt

@workflow_node
def bull_researcher(state: WorkflowState):
    prior = outputs(state, ("market_analyst", "fundamentals_analyst", "news_analyst", "sentiment_analyst", "bear_researcher"))
    return model_update(state, node_name="bull_researcher", prompt=role_prompt("Bull Researcher", "Build the strongest evidence-grounded bullish case and directly address the latest bearish objections.", "The analyst outputs below are evidence summaries, not facts themselves.", prior))
