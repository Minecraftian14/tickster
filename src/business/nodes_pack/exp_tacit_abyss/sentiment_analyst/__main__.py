from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.sentiment_analyst import sentiment_analyst


@execution_node
def sentiment_analyst_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(sentiment_analyst, auto_edge=True)
    return graph


main_callable = sentiment_analyst_node
