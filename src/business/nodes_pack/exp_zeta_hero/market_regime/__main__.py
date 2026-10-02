from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.market_regime_analyst import market_regime


@execution_node
def market_regime_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(market_regime, auto_edge=True)
    return graph


main_callable = market_regime_node
