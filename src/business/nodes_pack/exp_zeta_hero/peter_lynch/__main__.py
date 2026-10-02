from nodes_pack import execution_node, ExecutionGraph
from exp.exp_zeta_hero.peter_lynch_analyst import peter_lynch


@execution_node
def peter_lynch_node(graph: ExecutionGraph = None) -> ExecutionGraph:
    graph.add_node(peter_lynch, auto_edge=True)
    return graph


main_callable = peter_lynch_node
