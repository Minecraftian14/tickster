from nodes_pack import ExecutionGraph, execution_node
from tickster.workflow.helpers import workflow_node
from tickster.workflow.state import WorkflowState


@execution_node
def edit_prompt(graph: ExecutionGraph, prompt: str = "") -> ExecutionGraph:
    @workflow_node
    def edit_prompt_node(state: WorkflowState) -> WorkflowState:
        state['prompt'] = prompt
        return state

    graph.add_node(edit_prompt_node, auto_edge=True)
    return graph


main_callable = edit_prompt
