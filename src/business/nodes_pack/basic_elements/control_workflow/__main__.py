# from tickster.workflow.state import WorkflowState
# from .renderer import start_renderer
# from ... import ExecutionGraph
#
#
# def control_workflow(graph: ExecutionGraph) -> WorkflowState:
#     start_renderer(graph)
#     # width, height = 100, 100
#     # surface = Surface((width, height)).convert()
#     # surface.fill('white')
#     # centerx, centery = surface.get_rect().center
#     # draw.rect(surface, 'blue', Rect(0, 0, 50, 50))
#     return None
#
#
# # def control_workflow(graph: ExecutionGraph) -> WorkflowState:
# #     graph = # Overwrite with a dummy instance with at least 7 nodes
# #     callback = # Our graph implementation, which also acts as communication between execution and renderer
# #     start_execution(graph, callback) # A dummy function which emulates graph execution
# #     start_renderer(graph, callback) # Strictly blocking, so we cannot use return anything
# #     return None
#
# main_callable = control_workflow
# control_workflow.dismiss_exec_time_tracking = True


from pygame import QUIT, KEYUP, K_ESCAPE
from pygame.display import get_surface, update
from pygame.event import get as get_events
from pygame.font import Font
from pygame.time import Clock

from tickster.workflow.state import WorkflowState
from .execution import start_execution
from .layout import layout_graph
from .renderer import Camera, render_graph
from .structure import create_graph_state
from ... import ExecutionGraph
from ...execution_graph import Edge

SCREEN = get_surface()
CLOCK = Clock()


def start_renderer(graph):
    camera = Camera(SCREEN)
    font = Font(None, 22)
    running = True
    finishing_time = 5.0

    while running:
        dt = CLOCK.tick(60) / 1000

        for event in get_events():
            if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
                running = False

        if graph.result is not None:
            finishing_time -= dt
        if finishing_time <= 0:
            running = False

        render_graph(SCREEN, graph, camera, font, dt)
        update()


def create_dummy_graph():
    return ExecutionGraph(
        nodes={name: lambda: None for name in "ABCDEFG"},
        edges=[
            Edge(source="A", target="B"),
            Edge(source="A", target="C"),
            Edge(source="B", target="D"),
            Edge(source="C", target="E"),
            Edge(source="D", target="F"),
            Edge(source="E", target="F"),
            Edge(source="F", target="G"),
        ],
        start="A",
        last="G",
    )


def control_workflow(graph: ExecutionGraph) -> WorkflowState:
    # graph = create_dummy_graph()
    state = create_graph_state(graph)
    layout_graph(state)

    start_execution(graph, state)
    start_renderer(state)

    return state.result


main_callable = control_workflow
control_workflow.dismiss_exec_time_tracking = True
