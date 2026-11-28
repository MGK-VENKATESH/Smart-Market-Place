"""Independent correctness oracle. SQLite is bundled with Python.

The oracle is deliberately outside the search implementation and timed region.
The fixed manual expected list supplies an additional check on query semantics.
"""

from contextlib import closing
import sqlite3
from .catalogue import Product
from .search import validate_query


def reference_search(
    products: list[Product], category: str = "laptop", max_price: int = 60_000
) -> list[str]:
    validate_query(category, max_price)
    # A sqlite connection's own context manager manages transactions, not closing.
    with closing(sqlite3.connect(":memory:")) as database:
        database.execute(
            "CREATE TABLE products (ordinal INTEGER, id TEXT, category TEXT, "
            "price INTEGER, stock INTEGER)"
        )
        database.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?)",
            [(i, p.id, p.category, p.price, p.stock) for i, p in enumerate(products)],
        )
        rows = database.execute(
            "SELECT id FROM products "
            "WHERE price < ? AND stock > 0 AND category = ? ORDER BY ordinal",
            (max_price, category),
        ).fetchall()
    return [row[0] for row in rows]
