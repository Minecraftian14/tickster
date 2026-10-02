from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.rakesh_jhunjhunwala_analyst import rakesh_jhunjhunwala


@execution_node
def rakesh_jhunjhunwala_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(rakesh_jhunjhunwala, auto_edge=True)
    return graph


main_callable = rakesh_jhunjhunwala_node
