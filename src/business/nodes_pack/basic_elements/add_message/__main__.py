from nodes_pack import ExecutionGraph, execution_node
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState


@execution_node
def add_message(graph: ExecutionGraph, message_key: str = "key", message: str = "value") -> ExecutionGraph:
    @workflow_node
    def add_message_node(state: WorkflowState) -> WorkflowState:
        if 'message' not in state: state['message'] = {}
        state['message'][message_key] = message
        return state

    graph.add_node(add_message_node, auto_edge=True)
    return graph


main_callable = add_message
