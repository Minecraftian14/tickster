from nodes_pack import execution_node, ExecutionGraph
from nodes_pack.exp_zeta_hero.michael_burry_analyst import michael_burry


@execution_node
def michael_burry_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(michael_burry, auto_edge=True)
    return graph


main_callable = michael_burry_node
