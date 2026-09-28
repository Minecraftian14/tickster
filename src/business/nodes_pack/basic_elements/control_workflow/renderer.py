# from collections import deque
#
# from pygame import (
#     QUIT,
#     KEYUP, K_ESCAPE,
#     Surface,
# )
# from pygame.display import get_surface, update
# from pygame.draw import circle as draw_circle
# from pygame.event import get as get_events
# from pygame.math import Vector2
# from pygame.time import Clock
#
# from nodes_pack import ExecutionGraph
# from tickster.workflow.state import WorkflowState
#
# SCREEN = get_surface()
# background = Surface(SCREEN.get_size()).convert()
# background.fill('grey')
# maintain_fps = Clock().tick
# move_to_center = Vector2(SCREEN.get_rect().center).__add__
# RED = (255, 0, 0)
# BLUE = (0, 0, 255)
#
#
# def start_renderer(graph: ExecutionGraph):
#     points = [(0, 0), (90, 0), (90, 90), (0, 90)]
#     points_deque = deque(
#         move_to_center(point)
#         for point in points
#     )
#     points_deque.rotate(1)
#     SCREEN.blit(background, (0, 0))
#     running = True
#     while running:
#         maintain_fps(60)
#         for event in get_events():
#             if event.type == QUIT or (event.type == KEYUP and event.key == K_ESCAPE):
#                 running = False
#         points_deque.rotate(-1)
#         for point in points_deque:
#             draw_circle(SCREEN, BLUE, point, 3)
#         draw_circle(
#             SCREEN,
#             RED,
#             points_deque[0],
#             3,
#         )
#
#         update()


from pygame import Rect
from pygame import draw
from pygame.math import Vector2

BLUE = (70, 130, 220)
RED = (220, 70, 70)
GREY = (70, 70, 70)
WHITE = (235, 235, 235)
DARK = (25, 25, 25)


class Camera:
    def __init__(self, screen):
        self.screen = screen
        self.center = Vector2(screen.get_rect().center)
        self.zoom = 1.0

    def update(self, target_rect, dt):
        target_center = Vector2(target_rect.center)
        padding = 180
        rect = self.screen.get_rect()

        target_zoom = min(
            rect.width / max(target_rect.width + padding, 1),
            rect.height / max(target_rect.height + padding, 1),
            2.0,
        )

        factor = min(dt * 5, 1)
        self.center += (target_center - self.center) * factor
        self.zoom += (target_zoom - self.zoom) * factor

    def world_to_screen(self, point):
        return Vector2(self.screen.get_rect().center) + (
                Vector2(point) - self.center
        ) * self.zoom


def bounds_for(graph, names):
    rects = [graph.nodes[name].rect for name in names if name in graph.nodes]

    if not rects:
        return Rect(0, 0, graph.width, graph.height)

    return rects[0].unionall(rects[1:])


def edge_points(graph, edge):
    source = graph.nodes[edge.source].rect
    target = graph.nodes[edge.target].rect

    start = Vector2(source.midbottom)
    end = Vector2(target.midtop)
    middle_y = (start.y + end.y) / 2

    return [
        start,
        Vector2(start.x, middle_y),
        Vector2(end.x, middle_y),
        end,
    ]


def clean_name(name: str):
    return name.rsplit('-', 1)[0]


def render_graph(screen, graph, camera, font, dt):
    active = graph.active()
    camera.update(bounds_for(graph, active or graph.nodes), dt)

    screen.fill(GREY)

    for edge in graph.edges:
        points = [camera.world_to_screen(p) for p in edge_points(graph, edge)]
        draw.lines(screen, DARK, False, points, max(1, round(2 * camera.zoom)))

        if edge.label:
            label = font.render(edge.label, True, DARK)
            screen.blit(label, label.get_rect(center=points[1]))

    for name, node in graph.nodes.items():
        rect = node.rect
        position = camera.world_to_screen(rect.topleft)
        size = Vector2(rect.size) * camera.zoom
        screen_rect = Rect(position, size)

        draw.rect(screen, RED if name in active else BLUE, screen_rect, border_radius=6)
        draw.rect(screen, DARK, screen_rect, 2, border_radius=6)

        label = font.render(clean_name(name), True, WHITE)
        screen.blit(label, label.get_rect(center=screen_rect.center))
