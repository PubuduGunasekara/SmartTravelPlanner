
# 📍 Travel Day Scheduler using Weighted A*

## 📌 Overview

This project implements a **Travel Day Scheduling system** using the **Weighted A*** search algorithm to generate an optimized itinerary for a single day of travel.

The goal is to maximize overall enjoyment while respecting time constraints such as:

* Operating hours
* Travel time between locations
* Total available time in a day

---

## 🧠 Approach

We model the problem as a **graph search problem**:

* **Nodes** → Locations with time states
* **Edges** → Travel + visit transitions
* **Objective** → Find the best path that maximizes value while minimizing cost

We use **Weighted A***:

```
f(n) = g(n) + (1 + ε) * h(n)
```

Where:

* `g(n)` = accumulated cost
* `h(n)` = heuristic estimate of remaining cost
* `ε` = weight controlling speed vs optimality

---

## ⚙️ Cost Function

We define cost based on both **enjoyment and travel efficiency**:

```
Cost = cv × (5 - V) + ca × TravelTime
```

Where:

* `V = rating × (actual_time / ideal_time)`
* `cv` = weight for visit quality
* `ca` = weight for travel time

---

## 🔍 Heuristic

The heuristic estimates the remaining cost using:

* Remaining time
* Optimistic assumption of visiting high-rated locations
* Minimum travel overhead

This keeps the search efficient while guiding toward high-quality solutions.

---

## 📂 Project Structure

```
.
├── algorithms/
│   └── weighted_astar.py
├── data/
│   └── sample_locations.json
├── main.py
├── README.md
└── report/
    └── travel_day_scheduler_writeup.md.pdf
```

---

## 🚀 How to Run

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <your-repo-name>
```

### 2. Run the program

```bash
python algorithms/weighted_astar.py
```

---

## 📥 Input Format

Each attraction should include:

```json
{
  "name": "Museum",
  "x": 1,
  "y": 2,
  "rating": 4.5,
  "ideal_time": 2
}
```

---

## 📤 Output

* Ordered list of selected attractions
* Total computed value (enjoyment score)

Example:

```
Best Itinerary:
- Park
- Museum
- Gallery

Total Value: 13.9
```

---

## ⚡ Features

* Weighted A* search implementation
* Time-constrained itinerary planning
* Distance-based travel modeling
* Configurable heuristic weighting (ε)
* Custom cost function balancing enjoyment and travel time
* Avoids revisiting locations

---

## 🧪 Example Scenario

Given:

* A set of tourist attractions
* A starting location (e.g., hotel)
* A fixed time window (e.g., 8 hours)

The system finds a sequence of visits that:

* Maximizes total enjoyment
* Minimizes unnecessary travel
* Respects time constraints

---

## 📊 Complexity

* Worst-case time complexity:

  ```
  O(b^d)
  ```

  Where:

  * `b` = branching factor
  * `d` = depth of search

* Weighted A* improves practical performance by guiding the search toward promising paths.

---

## 📌 Future Improvements

* Incorporate real map distances (Google Maps API)
* Add user preferences / personalization
* Support multiple-day itineraries
* Add GUI for visualization
* Improve heuristic accuracy

---

