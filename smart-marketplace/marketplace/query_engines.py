"""Session 6: exact alternatives with a frozen result-order contract."""

from .search import linear_search, validate_query


class CategoryIndex:
    """Hash lookup of category, then scan its members in original order.

    Build O(n), O(n) extra references; expected O(1)+O(n_category) per query.
    A price limit is a range predicate: hashing cannot make this entire query O(1).
    Immutable Product instances form a snapshot; rebuild the index after updates.
    """
    def __init__(self, products):
        self.groups = {}
        for product in products:
            self.groups.setdefault(product.category, []).append(product)

    def search(self, category="laptop", max_price=60000):
        validate_query(category, max_price)
        return [p.id for p in self.groups.get(category, ()) if p.stock > 0 and p.price < max_price]


def repeated_scan(products, queries):
    return [linear_search(products, category, limit) for category, limit in queries]


def batched_scan(products, queries):
    """One catalogue traversal, q predicates per record: still O(n*q) worst case."""
    for category, limit in queries:
        validate_query(category, limit)
    result = [[] for _ in queries]
    for product in products:
        for index, (category, limit) in enumerate(queries):
            if product.category == category and product.stock > 0 and product.price < limit:
                result[index].append(product.id)
    return result
