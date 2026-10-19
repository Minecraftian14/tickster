from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from .utilities import PortfolioRecommendation, model_update, outputs, role_prompt

@workflow_node
def portfolio_manager(state: WorkflowState):
    prior = outputs(state, ("research_manager", "trader", "aggressive_risk_analyst", "conservative_risk_analyst", "neutral_risk_analyst"))
    prompt = role_prompt("Portfolio Manager", "Return JSON with rating exactly Buy, Overweight, Hold, Underweight, or Sell; executive_summary; investment_thesis; and key_risks. This is a research recommendation only and must not execute a trade.", "Use the proposal and risk debate.", prior)
    return model_update(state, node_name="portfolio_manager", prompt=prompt, schema=PortfolioRecommendation)
