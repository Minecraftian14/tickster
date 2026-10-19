from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.bear_researcher import bear_researcher


@execution_node
def bear_researcher_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(bear_researcher, auto_edge=True)
    return graph


main_callable = bear_researcher_node
