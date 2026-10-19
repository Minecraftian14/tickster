from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.bull_researcher import bull_researcher


@execution_node
def bull_researcher_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(bull_researcher, auto_edge=True)
    return graph


main_callable = bull_researcher_node
