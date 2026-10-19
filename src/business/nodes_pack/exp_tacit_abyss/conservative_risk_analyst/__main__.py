from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.conservative_risk_analyst import conservative_risk_analyst


@execution_node
def conservative_risk_analyst_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(conservative_risk_analyst, auto_edge=True)
    return graph


main_callable = conservative_risk_analyst_node
