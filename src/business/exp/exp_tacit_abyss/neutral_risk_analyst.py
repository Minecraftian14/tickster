from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from exp.exp_tacit_abyss.utilities import model_update, outputs, role_prompt

@workflow_node
def neutral_risk_analyst(state: WorkflowState):
    prior = outputs(state, ("trader", "research_manager", "aggressive_risk_analyst", "conservative_risk_analyst"))
    return model_update(state, node_name="neutral_risk_analyst", prompt=role_prompt("Neutral Risk Analyst", "Weigh upside and downside claims, resolve disagreements with evidence quality, and propose risk-aware safeguards.", "Use prior outputs.", prior))
