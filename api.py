# api.py
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from state import Node
from search import search, reconstruct_path
from travel_matrix import load_matrix, get_travel_time, ensure_matrix
from config import MEAL_POINTS
import config
import json
import os

from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Load activities
with open("activities/seattle.json") as f:
    data = json.load(f)
    activities_list = data if isinstance(data, list) else data.get("activities", [])
    activities = {a["id"]: a for a in activities_list}

# Matrix and coords loaded lazily on first request
matrix = None
locations = None
coord_lookup = {}


def detect_food(activity, arrival, departure, weekday):
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


def get_coords(address):
    coords = coord_lookup.get(address)
    if coords:
        return coords[0], coords[1]
    return None, None

@app.route("/activities", methods=["GET"])
def get_activities():
    items = []
    for aid, a in activities.items():
        items.append({
            "id": aid,
            "name": a["name"],
            "type": a.get("type"),
            "rating": a.get("rating"),
            "cost": a.get("estimated_cost_usd") or 0,
            "description": a.get("description", ""),
        })
    items.sort(key=lambda x: x["id"])
    return jsonify({"activities": items})

@app.route("/plan", methods=["POST"])
def plan():
    global coord_lookup, matrix, locations

    body = request.json

    must_visit_ids = set(body.get("must_visit", []))
    for aid in activities:
        activities[aid]["must_visit"] = aid in must_visit_ids

        
    start_time = datetime.fromisoformat(body["start_time"])
    ate_breakfast = body.get("ate_breakfast", False)

    start_node = Node(
        time=start_time,
        location=body["start_address"],
        fullness=config.FULLNESS_START if ate_breakfast else 0,
    )

    weekday = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"][start_node.time.weekday()]

    ctx = {
        "budget": body.get("budget", 200),
        "end_address": body["end_address"],
        "return_by": datetime.fromisoformat(body["end_time"]),
        "start_time": start_time,
        "weight": 1.1
    }

    matrix, locations = ensure_matrix(
        "activities/seattle.json",
        "activities/seattle_matrix.json",
        extra_addresses=[body["start_address"], body["end_address"]],
        profile="foot"
    )

    with open("activities/seattle_matrix.json") as f:
        coord_lookup = json.load(f).get("coordinates", {})

    path = search(start_node, activities, matrix, locations, weekday, ctx)

    if path is None:
        return jsonify({"error": "No valid itinerary found"}), 404

    itinerary = []
    for node in path:
        if node.activity_id is None:
            lat, lng = get_coords(node.location)
            itinerary.append({
                "name": "Start / End",
                "type": "home",
                "arrival": node.arrival_time.isoformat() if node.arrival_time else node.time.isoformat(),
                "departure": node.time.isoformat(),
                "address": node.location,
                "end_address": None,
                "cost": 0,
                "food": None,
                "must_visit": False,
                "rating": None,
                "lat": lat,
                "lng": lng,
            })
        else:
            activity = activities[node.activity_id]
            arrival = node.arrival_time if node.arrival_time else node.time
            food = detect_food(activity, arrival, node.time, weekday)
            addr = activity["start_location"]
            lat, lng = get_coords(addr)

            itinerary.append({
                "name": activity["name"],
                "type": activity.get("type"),
                "arrival": arrival.isoformat(),
                "departure": node.time.isoformat(),
                "address": addr,
                "end_address": activity.get("end_location"),
                "cost": activity.get("estimated_cost_usd") or 0,
                "food": food["meal"] if food else None,
                "must_visit": activity.get("must_visit", False),
                "rating": activity.get("rating"),
                "lat": lat,
                "lng": lng,
            })

    return jsonify({"itinerary": itinerary})

if __name__ == "__main__":
    app.run(debug=True, port=5000)