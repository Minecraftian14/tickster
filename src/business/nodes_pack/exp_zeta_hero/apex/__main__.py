from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.apex_analyst import apex


@execution_node
def apex_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(apex, auto_edge=True)
    return graph


main_callable = apex_node
