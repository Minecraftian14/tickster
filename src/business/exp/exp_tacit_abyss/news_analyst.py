from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState
from exp.exp_tacit_abyss.utilities import model_update, render_context, role_prompt

@workflow_node
def news_analyst(state: WorkflowState):
    evidence = render_context(state, record_types=("NewsItem", "CompanyEvent", "CorporateAction", "Filing", "MacroObservation", "MacroRelease"))
    return model_update(state, node_name="news_analyst", prompt=role_prompt("News and Macro Analyst", "Analyze company developments alongside RBI/MOSPI and Indian macro evidence; identify catalysts and risks.", evidence))
