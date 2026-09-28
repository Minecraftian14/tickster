from nodes_pack import execution_node, ExecutionGraph
from nodes_pack.exp_zeta_hero.analysts import warren_buffett as warren_buffett_node


@execution_node
def warren_buffett(graph: ExecutionGraph) -> ExecutionGraph:
    graph.add_node(warren_buffett_node, auto_edge=True)
    return graph


main_callable = warren_buffett
