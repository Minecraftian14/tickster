from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.trader import trader


@execution_node
def trader_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(trader, auto_edge=True)
    return graph


main_callable = trader_node
