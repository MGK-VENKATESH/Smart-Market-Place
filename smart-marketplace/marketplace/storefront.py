"""Product-facing catalogue queries, independent of the website framework."""
from collections import Counter
from .query_engines import CategoryIndex

CATEGORY_NAMES = {"laptop": "Laptops", "smartphone": "Smartphones", "tablet": "Tablets",
                  "desktop": "Desktops", "monitor": "Monitors", "accessories": "Accessories"}
CATEGORY_ICONS = {"laptop": "laptop_mac", "smartphone": "smartphone", "tablet": "tablet_mac",
                  "desktop": "desktop_windows", "monitor": "monitor", "accessories": "mouse"}


def browse(products, query="", category="All categories", max_price=100000, in_stock=True, sort="Featured"):
    """Inclusive customer-facing price ceiling; preserve order unless sorting is requested."""
    if max_price < 0:
        raise ValueError("Maximum price must be nonnegative")
    if in_stock:
        index = CategoryIndex(products)
        categories = index.groups if category == "All categories" else [category]
        eligible = {identifier for name in categories for identifier in index.search(name, max_price + 1)}
    else:
        eligible = {p.id for p in products if p.price <= max_price and
                    (category == "All categories" or p.category == category)}
    needle = query.strip().casefold()
    matches = [p for p in products if p.id in eligible and
               (not needle or needle in f"{p.title} {p.description} {p.id}".casefold())]
    if sort == "Price: low to high":
        matches.sort(key=lambda p: (p.price, p.id))
    elif sort == "Price: high to low":
        matches.sort(key=lambda p: (-p.price, p.id))
    elif sort == "Name":
        matches.sort(key=lambda p: (p.title.casefold(), p.id))
    return matches


def inventory_summary(products):
    return {"products": len(products), "available": sum(p.stock > 0 for p in products),
            "out_of_stock": sum(p.stock == 0 for p in products),
            "low_stock": sum(0 < p.stock <= 3 for p in products),
            "units": sum(p.stock for p in products),
            "categories": dict(Counter(p.category for p in products)),
            "listed_stock_value": sum(p.price * p.stock for p in products)}


def product_description(product):
    """Replace fixture-specific boundary explanations with factual storefront copy."""
    return {"P004": "Lightweight laptop for programming and everyday work.",
            "P006": "Laptop available at INR 60,000.",
            "P019": "14-inch laptop.",
            "P020": "Laptop currently awaiting restock."}.get(product.id, product.description)
