from datetime import datetime
from state import Node
from expansion import expand
from config import *
from search import search



test_node = Node(
    time=START_TIME,
    location=START_ADDRESS,
    visited=frozenset(),
    fullness=3,
    money_spent=0.0,
)

path = search(test_node, ACTIVITIES, MATRIX, LOCATIONS, WEEKDAY)
print(path)

for node in path:
    name = ACTIVITIES[node.activity_id]['name'] if node.activity_id else "HOME"
    arr = node.arrival_time.strftime('%H:%M') if node.arrival_time else node.time.strftime('%H:%M')

    food_str = ""
    if node.activity_id and node.parent:
        activity = ACTIVITIES[node.activity_id]
        food = activity.get("food")
        if food:
            for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
                meal = food.get(meal_type)
                if not meal or not meal.get(WEEKDAY):
                    continue
                meal_start = datetime.combine(node.arrival_time.date(), datetime.strptime(meal[WEEKDAY]["start"], "%H:%M").time())
                meal_end = datetime.combine(node.arrival_time.date(), datetime.strptime(meal[WEEKDAY]["end"], "%H:%M").time())
                if node.arrival_time < meal_end and node.time > meal_start:
                    food_str = f" ate {meal_type} (+{MEAL_POINTS[meal_type]})"
                    break

    print(f"{name:<35} arr={arr} dep={node.time.strftime('%H:%M')} fullness={node.fullness} ${node.money_spent:.0f}{food_str}")