from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from exp.exp_tacit_abyss.utilities import model_update, outputs, role_prompt

@workflow_node
def conservative_risk_analyst(state: WorkflowState):
    prior = outputs(state, ("trader", "research_manager", "aggressive_risk_analyst", "neutral_risk_analyst"))
    return model_update(state, node_name="conservative_risk_analyst", prompt=role_prompt("Conservative Risk Analyst", "Stress-test the proposal for downside, liquidity, concentration, data-quality, and macro risks; challenge excessive optimism.", "Use prior outputs.", prior))
