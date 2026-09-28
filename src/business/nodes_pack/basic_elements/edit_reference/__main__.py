from nodes_pack import ExecutionGraph, execution_node
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState, history_item


@execution_node
def edit_reference(graph: ExecutionGraph = None, reference: str = "") -> ExecutionGraph:
    @workflow_node
    def edit_reference_node(state: WorkflowState) -> WorkflowState:
        state['reference'] = history_item('edit_reference', reference)
        return state

    graph.add_node(edit_reference_node, auto_edge=True)
    return graph


main_callable = edit_reference
