from nodes_pack import ExecutionGraph, execution_node
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


@execution_node
def add_message(graph: ExecutionGraph = None, message_key: str = "key", message: str = "value") -> ExecutionGraph:
    @workflow_node
    def add_message_node(state: WorkflowState) -> WorkflowState:
        return {"history": [history_item('add_message', message)], 'reference': state.get('reference', None), 'message': {message_key: message}}

    graph.add_node(add_message_node, auto_edge=True)
    return graph


main_callable = add_message
