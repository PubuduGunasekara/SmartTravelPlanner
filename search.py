import heapq
from state import Node
from expansion import expand
from config import *
from datetime import datetime


# def search(start_node, activities, matrix, locations, weekday, ctx):
#     open_set = []
#     heapq.heappush(open_set, start_node)
#     closed_set = set()

#     while open_set:
#         current = heapq.heappop(open_set)
#         path = reconstruct_path(current)
#         #trail = " → ".join(str(n) for n in path)
#         # print(f"[cost={current.cost:.1f} f={current.f:.1f}] {trail}")
#         # print(ctx)
#         # Goal check — home node with no activity
#         if current.activity_id is None and current.location == ctx["end_address"] and current.parent is not None:
#             return reconstruct_path(current)

#         if current in closed_set:
#             continue
#         closed_set.add(current)

#         children = expand(current, activities, matrix, locations, weekday, ctx)
#         for child in children:
#             if child not in closed_set:
#                 heapq.heappush(open_set, child)

#     return None  # no valid path found

def search(start_node, activities, matrix, locations, weekday, ctx):
    weight = ctx.get("weight", 1.0)
    max_weight = 20.0
    max_iterations = 30000

    while weight <= max_weight:
        ctx["weight"] = weight
        open_set = []
        heapq.heappush(open_set, start_node)
        closed_set = set()
        iterations = 0

        print(f"Searching with heuristic weight {weight:.1f}...")

        while open_set:
            iterations += 1
            if iterations > max_iterations:
                print(f"  Hit {max_iterations} iterations, increasing weight...")
                break

            current = heapq.heappop(open_set)
            # path = reconstruct_path(current)
            # trail = " → ".join(str(n) for n in path)
            # print(f"[cost={current.cost:.1f} f={current.f:.1f}] {trail}")

            if current.activity_id is None and current.location == ctx["end_address"] and current.parent is not None:
                print(f"  Found solution in {iterations} iterations (weight={weight:.1f})")
                return reconstruct_path(current)

            if current in closed_set:
                continue
            closed_set.add(current)

            children = expand(current, activities, matrix, locations, weekday, ctx)
            for child in children:
                if child not in closed_set:
                    heapq.heappush(open_set, child)

            if len(open_set) > MAX_HEAP:
                open_set = heapq.nsmallest(MAX_HEAP // 2, open_set)
                heapq.heapify(open_set)

        weight *= 1.2
    return None


def reconstruct_path(node):
    path = []
    while node is not None:
        path.append(node)
        node = node.parent
    path.reverse()
    return path