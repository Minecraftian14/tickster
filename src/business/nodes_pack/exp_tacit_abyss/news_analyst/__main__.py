from nodes_pack import execution_node, ExecutionGraph
from exp.exp_tacit_abyss.news_analyst import news_analyst


@execution_node
def news_analyst_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(news_analyst, auto_edge=True)
    return graph


main_callable = news_analyst_node
