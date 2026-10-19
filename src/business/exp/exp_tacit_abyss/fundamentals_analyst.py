from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from .utilities import model_update, render_context, role_prompt

@workflow_node
def fundamentals_analyst(state: WorkflowState):
    evidence = render_context(state, record_types=("Instrument", "FundamentalSnapshot", "Filing", "ShareholdingSnapshot", "InsiderTransaction", "LargeDeal"))
    return model_update(state, node_name="fundamentals_analyst", prompt=role_prompt("Fundamentals Analyst", "Assess financial quality, valuation, filings, ownership signals, and fundamental risks for the Indian issuer.", evidence))
