from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.bill_ackman_analyst import bill_ackman


@execution_node
def bill_ackman_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(bill_ackman, auto_edge=True)
    return graph


main_callable = bill_ackman_node
