from nodes_pack import ExecutionGraph, execution_node
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


@workflow_node
def call_llm_node(state: WorkflowState) -> WorkflowState:
    prompt = state.get("prompt", None)
    if prompt is None: raise ValueError("Prompt was neither given nor present in state.")
    response = state['llm'].invoke(prompt)
    return {
        'history': [history_item('call_llm', response.content, output_raw=response)]
    }


@execution_node
def call_llm(graph: ExecutionGraph) -> ExecutionGraph:
    graph.add_node(call_llm_node, auto_edge=True)
    return graph


main_callable = call_llm
