import heapq
import math

# ----------------------------
# Distance (Euclidean)
# ----------------------------
def distance(a, b):
    return math.sqrt((a["x"] - b["x"])**2 + (a["y"] - b["y"])**2)


# ----------------------------
# Visit Value (from report)
# V = Rating * (ActualTime / IdealTime)
# ----------------------------
def visit_value(attraction):
    actual_time = attraction["ideal_time"]  # assume full visit
    return attraction["rating"] * (actual_time / attraction["ideal_time"])


# ----------------------------
# Cost Function (from report)
# Cost = cv*(5 - V) + ca*(TravelTime)
# ----------------------------
def compute_cost(current, next_attr, cv=1.0, ca=1.0, speed=1.0):
    travel_time = distance(current, next_attr) / speed
    V = visit_value(next_attr)
    cost = cv * (5 - V) + ca * travel_time
    return cost, travel_time


# ----------------------------
# Heuristic Function
# (optimistic: assume best rating ahead)
# ----------------------------
def heuristic(remaining_time):
    # Best case: rating = 5 everywhere
    return 0.1 * remaining_time  # small optimistic estimate


# ----------------------------
# Node Class
# ----------------------------
class Node:
    def __init__(self, location, time_spent, cost, path, visited):
        self.location = location
        self.time_spent = time_spent
        self.cost = cost
        self.path = path
        self.visited = visited

    def __lt__(self, other):
        return self.cost < other.cost


# ----------------------------
# Weighted A* Algorithm
# ----------------------------
def weighted_astar(start, attractions, time_limit, epsilon=0.5, speed=1.0):

    open_set = []
    start_node = Node(start, 0, 0, [], set())

    heapq.heappush(open_set, (0, start_node))

    best_path = []
    best_value = 0

    while open_set:
        _, current = heapq.heappop(open_set)

        # Compute total value of current path
        total_value = sum(visit_value(a) for a in current.path)

        if total_value > best_value:
            best_value = total_value
            best_path = current.path

        for attr in attractions:
            if attr["name"] in current.visited:
                continue

            cost, travel_time = compute_cost(current.location, attr, speed=speed)

            new_time = current.time_spent + travel_time + attr["ideal_time"]

            if new_time > time_limit:
                continue

            new_cost = current.cost + cost

            new_node = Node(
                attr,
                new_time,
                new_cost,
                current.path + [attr],
                current.visited | {attr["name"]}
            )

            h = heuristic(time_limit - new_time)

            # Weighted A* formula
            f = new_cost + (1 + epsilon) * h

            heapq.heappush(open_set, (f, new_node))

    return best_path, best_value


# ----------------------------
# Example Run
# ----------------------------
if __name__ == "__main__":

    start = {"name": "Hotel", "x": 0, "y": 0}

    attractions = [
        {"name": "Museum", "x": 1, "y": 2, "rating": 4.5, "ideal_time": 2},
        {"name": "Park", "x": 2, "y": 1, "rating": 4.8, "ideal_time": 1},
        {"name": "Tower", "x": 4, "y": 3, "rating": 4.7, "ideal_time": 3},
        {"name": "Gallery", "x": 3, "y": 1, "rating": 4.6, "ideal_time": 2},
    ]

    time_limit = 6

    path, value = weighted_astar(start, attractions, time_limit, epsilon=0.5)

    print("Best Itinerary:")
    for p in path:
        print("-", p["name"])

    print("Total Value:", round(value, 2))