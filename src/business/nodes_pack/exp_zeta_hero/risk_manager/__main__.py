from exp.exp_zeta_hero.risk_manager import risk_manager
from nodes_pack import execution_node, ExecutionGraph


@execution_node
def risk_manager_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(risk_manager, auto_edge=True)
    return graph


main_callable = risk_manager_node
