import heapq
from state import Node
from expansion import expand
from config import *
from datetime import datetime


def search(start_node, activities, matrix, locations, weekday):
    open_set = []
    heapq.heappush(open_set, start_node)
    closed_set = set()

    while open_set:
        current = heapq.heappop(open_set)
        path = reconstruct_path(current)
        # trail = " → ".join(str(n) for n in path)
        # print(f"[cost={current.cost:.1f} f={current.f:.1f}] {trail}")

        # Goal check — home node with no activity
        if current.activity_id is None and current.location == END_ADDRESS and current.parent is not None:
            return reconstruct_path(current)

        if current in closed_set:
            continue
        closed_set.add(current)

        children = expand(current, activities, matrix, locations, weekday)
        for child in children:
            if child not in closed_set:
                heapq.heappush(open_set, child)

    return None  # no valid path found


def reconstruct_path(node):
    path = []
    while node is not None:
        path.append(node)
        node = node.parent
    path.reverse()
    return path