from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from .utilities import TradeProposal, model_update, outputs, role_prompt

@workflow_node
def trader(state: WorkflowState):
    prior = outputs(state, ("research_manager", "market_analyst"))
    prompt = role_prompt("Trader", "Create an indicative, non-executable India-equity proposal. Return JSON with action (Buy/Hold/Sell), rationale, optional absolute INR entry_price/stop_loss/target_price, and optional allocation_percent. Do not create an order or quantity.", "Use research and technical reports.", prior)
    return model_update(state, node_name="trader", prompt=prompt, schema=TradeProposal)
