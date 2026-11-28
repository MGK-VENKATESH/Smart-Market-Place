"""Session 3: event contract and explicit doubling storage (no hidden list append)."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Event:
    timestamp_ms: int
    user_id: str
    kind: str
    product_id: Optional[str] = None
    query: Optional[str] = None

    def __post_init__(self):
        if type(self.timestamp_ms) is not int or self.timestamp_ms < 0 or not self.user_id:
            raise ValueError("Events require a nonnegative integer timestamp and anonymous user ID")
        if self.kind not in ("search", "view", "purchase"):
            raise ValueError("Unknown event kind")
        if self.kind == "search" and not self.query:
            raise ValueError("Search events require a query")
        if self.kind != "search" and not self.product_id:
            raise ValueError("View/purchase events require a product ID")


class DoublingBuffer:
    """Starts empty, then capacities 1,2,4,8,...; records element-copy costs.

    Cost model: one unit for a stored element and each copied element. Allocation
    and initialization of empty slots are excluded; including them changes the
    constant but preserves O(1) amortized insertion.
    """
    def __init__(self):
        self._data = []
        self.size = 0
        self.total_copies = 0
        self.total_actual = 0

    @property
    def capacity(self):
        return len(self._data)

    @property
    def potential(self):
        return 2 * self.size - self.capacity

    def append(self, item):
        before_capacity, before_potential = self.capacity, self.potential
        copied = 0
        if self.size == self.capacity:
            target = [None] * max(1, 2 * self.capacity)
            for index in range(self.size):
                target[index] = self._data[index]
                copied += 1
            self._data = target
        self._data[self.size] = item
        self.size += 1
        actual = copied + 1
        self.total_copies += copied
        self.total_actual += actual
        return {
            "append": self.size, "capacity_before": before_capacity, "capacity": self.capacity,
            "copies": copied, "actual_cost": actual, "total_copies": self.total_copies,
            "potential_before": before_potential, "potential": self.potential,
            "amortized_cost": actual + self.potential - before_potential,
            "accounting_credit": 3 * self.size - self.total_actual,
        }

    def __iter__(self):
        for index in range(self.size):
            yield self._data[index]

    def __len__(self):
        return self.size


def synthetic_events(products, size):
    for index in range(size):
        yield Event(1_800_000_000_000 + index * 1000, f"anon-{index % 97:03d}",
                    "view", products[index % len(products)].id)
