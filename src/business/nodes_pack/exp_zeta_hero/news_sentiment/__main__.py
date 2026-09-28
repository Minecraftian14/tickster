from nodes_pack import execution_node, ExecutionGraph
from nodes_pack.exp_zeta_hero.news_sentiment_analyst import news_sentiment


@execution_node
def news_sentiment_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(news_sentiment, auto_edge=True)
    return graph


main_callable = news_sentiment_node
