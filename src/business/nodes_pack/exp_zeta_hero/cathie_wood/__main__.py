from nodes_pack import execution_node, ExecutionGraph
from nodes_pack.exp_zeta_hero.cathie_wood_analyst import cathie_wood


@execution_node
def cathie_wood_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(cathie_wood, auto_edge=True)
    return graph


main_callable = cathie_wood_node
