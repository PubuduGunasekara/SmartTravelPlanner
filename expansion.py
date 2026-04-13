from state import Node
from config import *
from travel_matrix import get_travel_time
from datetime import timedelta
from datetime import datetime, timedelta

def can_expand(node: Node, ctx) -> bool:
    """Check if this node is allowed to expand at all."""
    if node.fullness < FULLNESS_MIN:
        return False
    if node.fullness > FULLNESS_MAX:
        return False
    if node.money_spent > ctx["budget"]:
        return False
    return True

def get_reachable(node, activities, matrix, locations, weekday, ctx):
    reachable = []

    # Collect exclusions from all visited activities
    excluded = set()
    for vid in node.visited:
        excluded.update(activities[vid].get("exclusions", []))

    for aid, activity in activities.items():
        if aid in node.visited:
            continue
        if aid in excluded:
            continue

        arrive_after = activity.get("arrive_after")
        if arrive_after and arrive_after.get(weekday) is None:
            continue

        travel = get_travel_time(matrix, locations, node.location, activity["start_location"])
        if travel is None:
            continue

        earliest_arrival = node.time + timedelta(minutes=travel)

        # Events: can we make at least one start time?
        event_times = activity.get("event_start_times")
        if event_times and event_times.get(weekday):
            last_start = max(
                datetime.combine(node.time.date(), datetime.strptime(t, "%H:%M").time())
                for t in event_times[weekday]
            )
            if earliest_arrival > last_start:
                continue

        # Flexible: can we arrive with enough time for minimum_duration?
        elif activity.get("leave_before") and activity["leave_before"].get(weekday):
            closes = datetime.combine(node.time.date(), datetime.strptime(activity["leave_before"][weekday], "%H:%M").time())
            min_dur = activity.get("minimum_duration") or 0
            if earliest_arrival > closes - timedelta(minutes=min_dur):
                continue

        # Can we afford it?
        cost = activity.get("estimated_cost_usd") or 0
        if node.money_spent + cost > ctx["budget"]:
            continue

        # Survived all filters — it's reachable
        reachable.append(aid)

    return reachable
    
def make_child(node, activity, aid, arrival, departure, travel_minutes, weekday, matrix, locations, ctx):
    # Decay based on total hours since start of day
    hours_since_start = (departure - ctx["start_time"]).total_seconds() / 3600
    parent_hours = (node.time - ctx["start_time"]).total_seconds() / 3600
    decay = int(hours_since_start // FULLNESS_DECAY_HOURS) - int(parent_hours // FULLNESS_DECAY_HOURS)

    food_gained = 0
    food = activity.get("food")
    if food:
        for meal_type in ["dinner", "lunch", "breakfast", "snacks"]:
            meal = food.get(meal_type)
            if not meal or not meal.get(weekday):
                continue
            meal_start = datetime.combine(arrival.date(), datetime.strptime(meal[weekday]["start"], "%H:%M").time())
            meal_end = datetime.combine(arrival.date(), datetime.strptime(meal[weekday]["end"], "%H:%M").time())
            if arrival < meal_end and departure > meal_start:
                food_gained = MEAL_POINTS[meal_type]
                break

    location = activity.get("end_location") or activity["start_location"]

    child = Node(
        time=departure,
        location=location,
        visited=node.visited | {aid},
        fullness=node.fullness - decay + food_gained,
        money_spent=node.money_spent + (activity.get("estimated_cost_usd") or 0),
        cost=0.0,
        heuristic=0.0,
        parent=node,
        activity_id=aid,
        arrival_time=arrival,
    )
    child.cost = node.cost + compute_cost(node, child, activity, travel_minutes, ctx)
    child.heuristic = compute_heuristic(child, matrix, locations, ctx)
    return child

def generate_children(node, reachable, activities, matrix, locations, weekday, ctx):
    children = []

    for aid in reachable:
        activity = activities[aid]
        travel = get_travel_time(matrix, locations, node.location, activity["start_location"])
        earliest_arrival = node.time + timedelta(minutes=travel)

        event_times = activity.get("event_start_times")
        if event_times and event_times.get(weekday):
            #events
            min_dur = activity.get("minimum_duration") or 0
            for t in event_times[weekday]:
                start = datetime.combine(node.time.date(), datetime.strptime(t, "%H:%M").time())
                if start < earliest_arrival:
                    continue
                departure = start + timedelta(minutes=min_dur)
                children.append(make_child(node, activity, aid, start, departure, travel, weekday, matrix, locations, ctx))
            
        else:
            # Flexible — vary stay duration from minimum to optimal in 10min increments
            arrive_after = activity.get("arrive_after")
            if arrive_after and arrive_after.get(weekday):
                opens = datetime.combine(node.time.date(), datetime.strptime(arrive_after[weekday], "%H:%M").time())
                arrival = max(earliest_arrival, opens)
            else:
                arrival = earliest_arrival

            leave_before = activity.get("leave_before")
            if leave_before and leave_before.get(weekday):
                closes = datetime.combine(node.time.date(), datetime.strptime(leave_before[weekday], "%H:%M").time())
            else:
                closes = None

            min_dur = activity.get("minimum_duration") or 10
            opt_dur = activity.get("optimal_duration") or min_dur

            for stay in range(min_dur, opt_dur + 1, 10):
                departure = arrival + timedelta(minutes=stay)
                if closes and departure > closes:
                    break
                children.append(make_child(node, activity, aid, arrival, departure, travel, weekday, matrix, locations, ctx))

            # Always include optimal if it didn't land on an increment
            if opt_dur % 10 != min_dur % 10:
                departure = arrival + timedelta(minutes=opt_dur)
                if not (closes and departure > closes):
                    children.append(make_child(node, activity, aid, arrival, departure, travel, weekday, matrix, locations, ctx))
            
    #can we go to our destination?
    
    travel_home = get_travel_time(matrix, locations, node.location, ctx["end_address"])
    if travel_home is not None:
        arrival_home = node.time + timedelta(minutes=travel_home)

        # Fullness after travel
        hours_since_start = (arrival_home - ctx["start_time"]).total_seconds() / 3600
        parent_hours = (node.time - ctx["start_time"]).total_seconds() / 3600
        decay = int(hours_since_start // FULLNESS_DECAY_HOURS) - int(parent_hours // FULLNESS_DECAY_HOURS)
        final_fullness = node.fullness - decay
        # All must_visits completed?
        must_visit_ids = {aid for aid, a in activities.items() if a.get("must_visit")}
        all_must_visited = must_visit_ids.issubset(node.visited)

        if final_fullness >= RETURN_MIN_FULLNESS and all_must_visited:
            home_node = Node(
                time=arrival_home,
                location=ctx["end_address"],
                visited=node.visited,
                fullness=final_fullness,
                money_spent=node.money_spent,
                cost=0.0,
                heuristic=0.0,
                parent=node,
                activity_id=None,
                arrival_time=arrival_home,
            )
            home_node.cost = node.cost + compute_cost(node, home_node, None, travel_home, ctx)
            children.append(home_node)

    return children

def compute_heuristic(node, matrix, locations, ctx):
    travel_home = get_travel_time(matrix, locations, node.location, ctx["end_address"]) or 0
    remaining = (ctx["return_by"] - node.time).total_seconds() / 60 - travel_home

    if remaining <= 0:
        return travel_home

    estimated_dead = remaining * (5 - BEST_RATING) / 5

    return (travel_home + estimated_dead) * ctx["weight"]

def compute_cost(parent, child, activity, travel_minutes, ctx):
    if activity is None:
        # Going home — remaining day is wasted
        remaining = (ctx["return_by"] - child.time).total_seconds() / 60
        return travel_minutes + max(0, remaining)


    opt_dur = activity.get("optimal_duration") or 0
    min_dur = activity.get("minimum_duration") or 0
    rating = activity.get("rating", 0)

    time_at = (child.time - child.arrival_time).total_seconds() / 60

    earliest = parent.time + timedelta(minutes=travel_minutes)
    wait_time = (child.arrival_time - earliest).total_seconds() / 60

    excess = max(0, time_at - opt_dur)

    # Travel and waiting are fully dead
    dead = travel_minutes + wait_time + excess

    # Time at activity (up to optimal) is partially dead based on rating
    useful_time = min(time_at, opt_dur)
    if time_at < min_dur:
        dead += useful_time  # didn't meet minimum, all wasted
    else:
        dead += useful_time * (5 - rating) / 5

    return dead


def expand(node, activities, matrix, locations, weekday, ctx):
    if not can_expand(node, ctx):
        return []
 
    reachable = get_reachable(node, activities, matrix, locations, weekday, ctx)
    return generate_children(node, reachable, activities, matrix, locations, weekday, ctx)