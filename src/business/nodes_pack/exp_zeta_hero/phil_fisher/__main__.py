from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.phil_fisher_analyst import phil_fisher


@execution_node
def phil_fisher_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(phil_fisher, auto_edge=True)
    return graph


main_callable = phil_fisher_node
