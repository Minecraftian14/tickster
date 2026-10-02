from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.stanley_druckenmiller_analyst import stanley_druckenmiller


@execution_node
def stanley_druckenmiller_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(stanley_druckenmiller, auto_edge=True)
    return graph


main_callable = stanley_druckenmiller_node
