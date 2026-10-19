from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.market_analyst import market_analyst


@execution_node
def market_analyst_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(market_analyst, auto_edge=True)
    return graph


main_callable = market_analyst_node
