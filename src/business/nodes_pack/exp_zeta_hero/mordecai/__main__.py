from nodes_pack import execution_node, ExecutionGraph
from nodes_pack.exp_zeta_hero.mordecai_analyst import mordecai


@execution_node
def mordecai_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(mordecai, auto_edge=True)
    return graph


main_callable = mordecai_node
