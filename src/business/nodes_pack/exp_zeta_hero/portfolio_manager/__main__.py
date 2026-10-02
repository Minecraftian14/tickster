from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.portfolio_manager_analyst import portfolio_manager


@execution_node
def portfolio_manager_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(portfolio_manager, auto_edge=True)
    return graph


main_callable = portfolio_manager_node
