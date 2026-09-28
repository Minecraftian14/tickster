from nodes_pack import execution_node, ExecutionGraph
from nodes_pack.exp_zeta_hero.warren_buffett_analyst import warren_buffett


@execution_node
def warren_buffett_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(warren_buffett, auto_edge=True)
    return graph


main_callable = warren_buffett_node
