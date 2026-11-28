"""Product contract, validated JSON ingestion and reproducible teaching data."""

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Union


@dataclass(frozen=True)
class Product:
    id: str
    title: str
    description: str
    category: str
    price: int  # Whole INR; compare integers rather than floating-point amounts.
    stock: int
    version: int

    def __post_init__(self) -> None:
        for name in ("id", "title", "description", "category"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        for name in ("price", "stock", "version"):
            value = getattr(self, name)
            if type(value) is not int:
                raise ValueError(f"{name} must be an integer")
        if self.price < 0 or self.stock < 0 or self.version < 1:
            raise ValueError("price/stock must be nonnegative; version must be positive")


def load_catalogue(path: Union[str, Path]) -> list[Product]:
    """Load a JSON array, rejecting invalid records and duplicate product IDs."""
    with Path(path).open(encoding="utf-8") as stream:
        raw = json.load(stream)
    if not isinstance(raw, list):
        raise ValueError("catalogue must be a JSON array")
    products: list[Product] = []
    seen: set[str] = set()
    for position, row in enumerate(raw, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"record {position} must be an object")
        try:
            product = Product(**row)
        except (TypeError, ValueError) as error:
            raise ValueError(f"record {position}: {error}") from error
        if product.id in seen:
            raise ValueError(f"duplicate product ID: {product.id}")
        seen.add(product.id)
        products.append(product)
    return products


def save_catalogue(products: list[Product], path: Union[str, Path]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps([asdict(product) for product in products], indent=2) + "\n",
        encoding="utf-8",
    )


def expand_catalogue(fixture: list[Product], size: int) -> list[Product]:
    """Repeat the fixture's attribute mix, assigning unique IDs after the first copy.

    No random seed is needed: identical inputs always yield identical products.
    This intentionally fixes selectivity; it is not a realistic marketplace sample.
    """
    if type(size) is not int or size < 0:
        raise ValueError("size must be a nonnegative integer")
    if not fixture:
        if size == 0:
            return []
        raise ValueError("a nonempty fixture is required")
    products = []
    for index in range(size):
        block, offset = divmod(index, len(fixture))
        original = fixture[offset]
        identifier = original.id if block == 0 else f"{original.id}_R{block:04d}"
        products.append(replace(original, id=identifier))
    if len({product.id for product in products}) != len(products):
        raise ValueError("fixture IDs conflict with generated repetition suffixes")
    return products
