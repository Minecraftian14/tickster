from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.charlie_munger_analyst import charlie_munger


@execution_node
def charlie_munger_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(charlie_munger, auto_edge=True)
    return graph


main_callable = charlie_munger_node
