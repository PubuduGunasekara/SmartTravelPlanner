from datetime import datetime
import json



# Trip parameters
START_ADDRESS = "18607 Bothell Way NE, Bothell, WA 98011"
# END_ADDRESS = "18607 Bothell Way NE, Bothell, WA 98011"
END_ADDRESS = "17801 International Blvd, SeaTac, WA 98158"
START_TIME = 1#datetime(2026, 5, 1, 9, 0)
RETURN_BY = 1# datetime(2026, 5, 1, 2, 0)
WEEKDAY = "fri"
BUDGET = 1#120
AP = "activities/seattle.json"
BEST_RATING = 4.5


TRAVEL_BUFFER = 7


# Fullness system
FULLNESS_MAX = 5
FULLNESS_MIN = 0
FULLNESS_DECAY_HOURS = 2
FULLNESS_START = 3  # ate at hotel
RETURN_MIN_FULLNESS = 3

# Meal points
MEAL_POINTS = {
    "breakfast": 3,
    "lunch": 3,
    "dinner": 4,
    "snacks": 1,
}

# Cost tuning
OVERTIME_PENALTY_WEIGHT = 5.0
TIME_INCREMENT_MINUTES = 15


MAX_HEAP = 100000000

# activities

def load_activities(path: str) -> dict[int, dict]:
    with open(path) as f:
        data = json.load(f)
    activities = data if isinstance(data, list) else data.get("activities", [])
    return {a["id"]: a for a in activities}


# ACTIVITIES = load_activities(AP)
# MATRIX, LOCATIONS = load_matrix("activities/seattle_matrix2.json")

