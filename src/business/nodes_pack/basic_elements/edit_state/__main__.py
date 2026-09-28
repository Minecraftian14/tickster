from typing import Optional

from nodes_pack import ExecutionGraph, execution_node
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState


@execution_node
def edit_state(graph: ExecutionGraph, prompt: Optional[str] = None, message_key: Optional[str] = None, message: Optional[str] = None) -> ExecutionGraph:
    @workflow_node
    def edit_state_node(state: WorkflowState) -> WorkflowState:
        if prompt is not None: state['prompt'] = prompt
        if message_key is not None: state['message'] = {message_key: message}
        return state

    graph.add_node(edit_state_node, auto_edge=True)
    return graph


main_callable = edit_state
