from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.fundamentals_analyst import fundamentals_analyst


@execution_node
def fundamentals_analyst_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(fundamentals_analyst, auto_edge=True)
    return graph


main_callable = fundamentals_analyst_node
