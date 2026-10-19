from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.portfolio_manager import portfolio_manager


@execution_node
def portfolio_manager_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(portfolio_manager, auto_edge=True)
    return graph


main_callable = portfolio_manager_node
