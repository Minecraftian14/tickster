from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.neutral_risk_analyst import neutral_risk_analyst


@execution_node
def neutral_risk_analyst_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(neutral_risk_analyst, auto_edge=True)
    return graph


main_callable = neutral_risk_analyst_node
