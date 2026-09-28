from nodes_pack import execution_node, ExecutionGraph
from nodes_pack.exp_zeta_hero.ben_graham_analyst import ben_graham


@execution_node
def ben_graham_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(ben_graham, auto_edge=True)
    return graph


main_callable = ben_graham_node
