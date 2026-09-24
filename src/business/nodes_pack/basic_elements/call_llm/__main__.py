from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


@workflow_node
def call_llm(state: WorkflowState) -> WorkflowState:
    prompt = state.get("prompt", None)
    if prompt is None: raise ValueError("Prompt was neither given nor present in state.")
    response = state['llm'].invoke(prompt)
    return {
        'history': [history_item('call_llm', response.content, output_raw=response)]
    }


main_callable = call_llm
