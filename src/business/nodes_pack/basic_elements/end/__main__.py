from nodes_pack import ExecutionGraph, execution_node
from tickster.workflow.state import create_state


@execution_node
def end(graph: ExecutionGraph) -> ExecutionGraph:
    workflow = graph.create_langgraph_workflow()
    workflow.invoke(create_state())
    return graph


main_callable = end
