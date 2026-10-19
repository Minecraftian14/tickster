from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.research_manager import research_manager


@execution_node
def research_manager_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(research_manager, auto_edge=True)
    return graph


main_callable = research_manager_node
