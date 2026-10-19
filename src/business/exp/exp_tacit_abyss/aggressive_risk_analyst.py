from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from exp.exp_tacit_abyss.utilities import model_update, outputs, role_prompt

@workflow_node
def aggressive_risk_analyst(state: WorkflowState):
    prior = outputs(state, ("trader", "research_manager", "conservative_risk_analyst", "neutral_risk_analyst"))
    return model_update(state, node_name="aggressive_risk_analyst", prompt=role_prompt("Aggressive Risk Analyst", "Stress-test the proposal from an upside-seeking perspective; challenge excessive caution while naming downside limits.", "Use prior outputs.", prior))
