from dataclasses import dataclass, field
from datetime import datetime
from config import *

@dataclass
class Node:
    time: datetime
    location: str
    visited: frozenset[int] = field(default_factory=frozenset)
    fullness: int = 0
    money_spent: float = 0.0
    cost: float = 0.0
    heuristic: float = 0.0
    parent: "Node | None" = None
    activity_id: int | None = None  # activity just completed to reach this node
    arrival_time: datetime = None

    @property
    def f(self) -> float:
        return self.cost + self.heuristic

    def __lt__(self, other: "Node") -> bool:
        return self.f < other.f

    def __hash__(self) -> int:
        return hash((self.time, self.location, self.visited, self.fullness, self.money_spent))

    def __eq__(self, other) -> bool:
        return (self.time, self.location, self.visited, self.fullness, self.money_spent) == \
               (other.time, other.location, other.visited, other.fullness, other.money_spent)
    
    def __repr__(self):
        if self.activity_id is None:
            return f"<HOME {self.time.strftime('%H:%M')}>"
        dur = (self.time - self.arrival_time).total_seconds() / 60
        return f"<{ACTIVITIES[self.activity_id]['name'][:20]} arr={self.arrival_time.strftime('%H:%M')} dep={self.time.strftime('%H:%M')} {dur:.0f}min>"