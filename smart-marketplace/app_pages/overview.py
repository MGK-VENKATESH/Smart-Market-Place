import streamlit as st

from marketplace.dashboard import browse_category, get_products, product_grid
from marketplace.storefront import CATEGORY_NAMES, inventory_summary

products = get_products()
summary = inventory_summary(products)
total = summary["products"]
available = summary["available"]
low = summary["low_stock"]
out = summary["out_of_stock"]
categories = summary["categories"]

st.title("Inventory overview", anchor=False)
st.write("Availability, stock levels and category coverage across your catalogue.")

metrics = [
    ("Listed products", total, "Across all categories", "inventory_2", "lilac"),
    ("Units on hand", summary["units"], "Total physical stock", "layers", "blue"),
    ("Low stock", low, "1–3 units remaining", "warning", "amber"),
    ("Out of stock", out, "Listings with zero units", "block", "rose"),
]

with st.container(key="overview_metrics"):
    for column, (label, value, detail, icon, color) in zip(st.columns(4), metrics):
        with column, st.container(border=True):
            st.markdown(f":material/{icon}: **{label}**")
            st.html(f'<div class="metric-value {color}">{value}</div><div class="metric-note">{detail}</div>')

stock_col, mix_col = st.columns([1, 1.08], gap="medium")
with stock_col:
    percent = 100 * available / total if total else 0
    healthy_percent = 100 * (available - low) / total if total else 0
    legend = "".join(
        f'<div class="stock-row"><span class="legend-dot {color}"></span><span>{label}</span><b>{value}</b></div>'
        for label, value, color in [
            ("Healthy stock", available - low, "healthy"),
            ("Low stock", low, "low"),
            ("Out of stock", out, "empty"),
        ]
    )
    st.html(f"""
    <section class="availability" aria-label="Stock availability">
        <h2>Stock availability</h2>
        <div class="ring" role="img" aria-label="{percent:.0f}% of listings in stock"
             style="--healthy:{healthy_percent:.3f}%; --available:{percent:.3f}%">
            <div><strong>{percent:.0f}%</strong><span>in stock</span></div>
        </div>
        <div class="stock-legend">{legend}</div>
    </section>
    """)
with mix_col, st.container(border=True, key="category_mix"):
    st.subheader("Category mix", anchor=False)
    st.caption("Select a category to explore its products.")
    ordered = sorted(categories, key=lambda cat: -categories[cat])
    for category in ordered:
        count = categories[category]
        # Each row is a native, keyboard-accessible drill-down control.
        name = CATEGORY_NAMES[category]
        share = 100 * count / total
        with st.container(key=f"mix_{category}"):
            if st.button(f"{name} · {count}", key=f"category_{category}", width="stretch",
                         on_click=browse_category, args=(category,)):
                st.switch_page("app_pages/catalogue.py")
            st.html(f'<div class="mix-track" aria-hidden="true"><i style="width:{share:.2f}%"></i></div>')

st.subheader("Product spotlight", anchor=False)
st.caption("The most-stocked product in each available category.")
picks = {}
for product in products:
    if product.stock and (product.category not in picks or product.stock > picks[product.category].stock):
        picks[product.category] = product
product_grid(list(picks.values()), "featured")
