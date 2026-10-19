from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from exp.exp_tacit_abyss.utilities import model_update, render_context, role_prompt

@workflow_node
def sentiment_analyst(state: WorkflowState):
    evidence = render_context(state, record_types=("NewsItem", "SocialPost"))
    task = "Assess India-market news and Reddit/forum sentiment. X evidence is intentionally unavailable in this migration; explicitly disclose that limitation and never infer X sentiment."
    return model_update(state, node_name="sentiment_analyst", prompt=role_prompt("Sentiment Analyst", task, evidence))
