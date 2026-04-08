# api.py
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from state import Node
from search import search, reconstruct_path
from travel_matrix import load_matrix, get_travel_time
from config import MEAL_POINTS
import config
import json

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load data once at startup
matrix, locations = load_matrix("activities/seattle_matrix2.json")
with open("activities/seattle.json") as f:
    data = json.load(f)
    activities_list = data if isinstance(data, list) else data.get("activities", [])
    activities = {a["id"]: a for a in activities_list}


def detect_food(activity, arrival, departure, weekday):
    """Check what food was consumed during this visit."""
    food = activity.get("food")
    if not food:
        return None
    for meal_type in ["dinner", "lunch", "breakfast", "snacks"]:
        meal = food.get(meal_type)
        if not meal or not meal.get(weekday):
            continue
        meal_start = datetime.combine(arrival.date(), datetime.strptime(meal[weekday]["start"], "%H:%M").time())
        meal_end = datetime.combine(arrival.date(), datetime.strptime(meal[weekday]["end"], "%H:%M").time())
        if arrival < meal_end and departure > meal_start:
            return {"meal": meal_type, "points": MEAL_POINTS[meal_type]}
    return None


@app.route("/plan", methods=["POST"])
def plan():
    body = request.json

    start_time = datetime.fromisoformat(body["start_time"])
    ate_breakfast = body.get("ate_breakfast", False)
    budget = body.get("budget", config.BUDGET)

    config.START_ADDRESS = body["start_address"]
    config.END_ADDRESS = body["end_address"]
    config.RETURN_BY = datetime.fromisoformat(body["end_time"])
    config.BUDGET = budget

    start_node = Node(
        time=start_time,
        location=body["start_address"],
        fullness=config.FULLNESS_START if ate_breakfast else 0,
    )

    weekday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][start_node.time.weekday()]

    path = search(start_node, activities, matrix, locations, weekday)

    if path is None:
        return jsonify({"error": "No valid itinerary found"}), 404

    itinerary = []
    for node in path:
        if node.activity_id is None:
            itinerary.append({
                "name": "start/end",
                "type": "start/end",
                "arrival": node.arrival_time.isoformat() if node.arrival_time else node.time.isoformat(),
                "departure": node.time.isoformat(),
                "address": node.location,
                "end_address": None,
                "cost": 0,
                "food": None,
                "must_visit": False,
                "rating": None,
            })
        else:
            activity = activities[node.activity_id]
            arrival = node.arrival_time if node.arrival_time else node.time
            food = detect_food(activity, arrival, node.time, weekday)

            itinerary.append({
                "name": activity["name"],
                "type": activity.get("type"),
                "arrival": arrival.isoformat(),
                "departure": node.time.isoformat(),
                "address": activity["start_location"],
                "end_address": activity.get("end_location"),
                "cost": activity.get("estimated_cost_usd") or 0,
                "food": food["meal"] if food else None,
                "must_visit": activity.get("must_visit", False),
                "rating": activity.get("rating"),
            })

    return jsonify({"itinerary": itinerary})

if __name__ == "__main__":
    app.run(debug=True, port=5000)