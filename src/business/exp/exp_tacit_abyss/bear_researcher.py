from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from exp.exp_tacit_abyss.utilities import model_update, outputs, role_prompt

@workflow_node
def bear_researcher(state: WorkflowState):
    prior = outputs(state, ("market_analyst", "fundamentals_analyst", "news_analyst", "sentiment_analyst", "bull_researcher"))
    return model_update(state, node_name="bear_researcher", prompt=role_prompt("Bear Researcher", "Build the strongest evidence-grounded bearish case and directly address the latest bullish argument.", "The analyst outputs below are evidence summaries, not facts themselves.", prior))
