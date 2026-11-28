"""Exact, stable-order linear filtering and its separately instrumented version."""

from dataclasses import dataclass
from .catalogue import Product


def validate_query(category: str, max_price: int) -> None:
    if not isinstance(category, str) or not category.strip():
        raise ValueError("category must be a nonempty string")
    if type(max_price) is not int or max_price < 0:
        raise ValueError("max_price must be a nonnegative integer in whole INR")


def linear_search(
    products: list[Product], category: str = "laptop", max_price: int = 60_000
) -> list[str]:
    """Return IDs in input order: exact category, positive stock, price < limit.

    This function is the timing baseline. No file I/O, counters or tracing occurs
    inside the loop. Title and description do not affect this structured filter.
    """
    validate_query(category, max_price)
    matches = []
    for product in products:
        if product.category == category and product.stock > 0 and product.price < max_price:
            matches.append(product.id)
    return matches


@dataclass
class ScanCounts:
    records_visited: int = 0
    category_comparisons: int = 0
    stock_comparisons: int = 0
    price_comparisons: int = 0
    output_appends: int = 0

    @property
    def predicate_comparisons(self) -> int:
        return self.category_comparisons + self.stock_comparisons + self.price_comparisons

    @property
    def counted_operations(self) -> int:
        """One per visit, evaluated comparison and append; not CPU instructions."""
        return self.records_visited + self.predicate_comparisons + self.output_appends


def instrumented_search(
    products: list[Product], category: str = "laptop", max_price: int = 60_000
) -> tuple[list[str], ScanCounts]:
    validate_query(category, max_price)
    counts = ScanCounts()
    matches = []
    for product in products:
        counts.records_visited += 1
        counts.category_comparisons += 1
        if product.category != category:
            continue
        counts.stock_comparisons += 1
        if product.stock <= 0:
            continue
        counts.price_comparisons += 1
        if product.price >= max_price:
            continue
        matches.append(product.id)
        counts.output_appends += 1
    return matches, counts
