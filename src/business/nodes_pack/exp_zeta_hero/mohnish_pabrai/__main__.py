from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.mohnish_pabrai_analyst import mohnish_pabrai


@execution_node
def mohnish_pabrai_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(mohnish_pabrai, auto_edge=True)
    return graph


main_callable = mohnish_pabrai_node
