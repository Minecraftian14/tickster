from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from exp.exp_tacit_abyss.utilities import model_update, render_context, role_prompt

@workflow_node
def market_analyst(state: WorkflowState):
    evidence = render_context(state, record_types=("Instrument", "PriceBar", "IndexSnapshot", "IndexPriceBar"))
    return model_update(state, node_name="market_analyst", prompt=role_prompt("Market Analyst", "Analyze India-market price action, trend, liquidity, volatility, RSI/MACD, and NSE index context. Produce a technical report, not a trade instruction.", evidence))
