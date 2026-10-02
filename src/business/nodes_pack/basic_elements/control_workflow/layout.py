# from collections import defaultdict, deque
#
# from pygame import Rect
#
# from .models import GraphState
# from .structure import adjacency
#
#
# def layout_graph(
#     graph: GraphState,
#     box_width: int = 140,
#     box_height: int = 60,
#     horizontal_spacing: int = 80,
#     vertical_spacing: int = 100,
# ):
#     outgoing, incoming = adjacency(graph)
#     layers = defaultdict(list)
#     visited = set()
#     queue = deque([(graph.start, 0)]) if graph.start in graph.nodes else deque()
#
#     while queue:
#         name, depth = queue.popleft()
#
#         if name in visited:
#             continue
#
#         visited.add(name)
#         layers[depth].append(name)
#
#         for child in outgoing[name]:
#             if child not in visited:
#                 queue.append((child, depth + 1))
#
#     remaining = [name for name in graph.nodes if name not in visited]
#
#     if remaining:
#         depth = max(layers, default=-1) + 1
#         layers[depth].extend(remaining)
#
#     ordered = []
#
#     for depth in sorted(layers):
#         layer = layers[depth]
#         layer.sort(key=lambda name: sum(ordered.index(parent) for parent in incoming[name] if parent in ordered))
#         ordered.append(*layer)
#
#     max_width = max(map(len, layers.values()), default=1)
#     max_depth = max(layers, default=0)
#
#     graph.width = max_width * box_width + (max_width - 1) * horizontal_spacing
#     graph.height = (max_depth + 1) * box_height + max_depth * vertical_spacing
#
#     for depth, layer in layers.items():
#         layer_width = len(layer) * box_width + (len(layer) - 1) * horizontal_spacing
#         x = (graph.width - layer_width) // 2
#
#         for name in layer:
#             graph.nodes[name].rect = Rect(x, depth * (box_height + vertical_spacing), box_width, box_height)
#             x += box_width + horizontal_spacing
#
#     for node in graph.nodes.values():
#         node.rect.move_ip(0, 0)
#
#     return graph


from collections import defaultdict, deque

from pygame import Rect

from .models import GraphState
from .structure import adjacency


def layout_graph(
        state: GraphState,
        box_width: int = 140,
        box_height: int = 30,
        horizontal_spacing: int = 35,
        vertical_spacing: int = 15,
):
    outgoing, incoming = adjacency(state)
    layers = defaultdict(list)
    visited = set()
    queue = deque([(state.start, 0)]) if state.start in state.nodes else deque()

    while queue:
        name, depth = queue.popleft()

        if name in visited:
            continue

        visited.add(name)
        layers[depth].append(name)
        queue.extend((child, depth + 1) for child in outgoing[name] if child not in visited)

    remaining = [name for name in state.nodes if name not in visited]

    if remaining:
        layers[max(layers, default=-1) + 1].extend(remaining)

    positions = {}

    for depth in sorted(layers):
        layer = layers[depth]
        layer.sort(key=lambda name: sum(positions[parent][0] for parent in incoming[name] if parent in positions))
        width = len(layer) * box_width + (len(layer) - 1) * horizontal_spacing
        x = (max(width, box_width) - width) / 2

        for name in layer:
            positions[name] = (x, depth)
            x += box_width + horizontal_spacing

    state.width = max(
        (len(layer) * box_width + (len(layer) - 1) * horizontal_spacing for layer in layers.values()),
        default=box_width,
    )
    state.height = (max(layers, default=0) + 1) * box_height + max(layers, default=0) * vertical_spacing

    for name, (x, depth) in positions.items():
        state.nodes[name].rect = Rect(round(x), round(depth * (box_height + vertical_spacing)), box_width, box_height)

    return state
