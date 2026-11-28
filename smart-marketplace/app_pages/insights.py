import altair as alt
import pandas as pd
import streamlit as st
from marketplace.dashboard import get_products
from marketplace.duplicates import find_duplicates
from marketplace.storefront import CATEGORY_NAMES, inventory_summary, product_description

st.title("Inventory insights", anchor=False)
st.write("Monitor availability, category coverage and stock that needs attention.")
products = get_products()
summary = inventory_summary(products)
with st.container(horizontal=True):
    st.metric("Products", summary["products"], border=True)
    st.metric("In stock", summary["available"], border=True)
    st.metric("Low stock", summary["low_stock"], border=True, help="Products with one to three units remaining.")
    st.metric("Total units", summary["units"], border=True)
left, right = st.columns(2)
with left, st.container(border=True):
    st.subheader("Products by category", anchor=False)
    chart_data = pd.DataFrame([{"Category": CATEGORY_NAMES[category], "Products": count}
                               for category, count in summary["categories"].items()])
    st.bar_chart(chart_data, x="Category", y="Products", horizontal=True, height=260)
with right, st.container(border=True):
    st.subheader("Price and availability", anchor=False)
    points = pd.DataFrame([{"Product": p.title, "Price (INR)": p.price, "Units in stock": p.stock,
                            "Category": CATEGORY_NAMES[p.category]} for p in products])
    chart = alt.Chart(points).mark_circle(size=100).encode(
        x=alt.X("Price (INR):Q"), y=alt.Y("Units in stock:Q"), color="Category:N",
        tooltip=["Product", "Price (INR)", "Units in stock"]).properties(height=260)
    st.altair_chart(chart)
st.subheader("Stock watch", anchor=False)
attention = [{"Product": p.title, "Category": CATEGORY_NAMES[p.category], "Price (INR)": p.price,
              "Units": p.stock, "Availability": "Out of stock" if p.stock == 0 else "Low stock"}
             for p in products if p.stock <= 3]
st.dataframe(attention, hide_index=True)
duplicates = find_duplicates(products)["duplicate_of"]
with st.expander("Catalogue quality"):
    st.write(f"{len({p.id for p in products})} unique product IDs · {len(duplicates)} repeated descriptions")
    if duplicates:
        st.dataframe([{"Product ID": key, "Matching description": value} for key, value in duplicates.items()],
                     hide_index=True)
    else:
        st.success("Every product has a unique ID and description.")
with st.expander("View the full inventory"):
    rows = [{"ID": p.id, "Product": p.title, "Category": CATEGORY_NAMES[p.category],
             "Price (INR)": p.price, "Stock": p.stock, "Description": product_description(p)} for p in products]
    st.dataframe(rows, hide_index=True)
