from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from .utilities import model_update, outputs, role_prompt

@workflow_node
def research_manager(state: WorkflowState):
    prior = outputs(state, ("market_analyst", "fundamentals_analyst", "news_analyst", "sentiment_analyst", "bull_researcher", "bear_researcher"))
    return model_update(state, node_name="research_manager", prompt=role_prompt("Research Manager", "Synthesize the debate into a balanced research plan: thesis, contrary case, confidence, catalysts, invalidation conditions, and evidence gaps.", "Use all completed reports.", prior))
