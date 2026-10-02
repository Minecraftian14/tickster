from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.aswath_damodaran_analyst import aswath_damodaran


@execution_node
def aswath_damodaran_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(aswath_damodaran, auto_edge=True)
    return graph


main_callable = aswath_damodaran_node
