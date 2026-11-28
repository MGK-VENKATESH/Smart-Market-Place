import streamlit as st
from marketplace.dashboard import get_products, product_grid
from marketplace.storefront import CATEGORY_NAMES, browse

st.title("Product catalogue", anchor=False)
st.write("Search listings by name or ID, then filter by category, price and availability.")
products = get_products()
if "pending_category" in st.session_state:
    st.session_state["browse_category"] = st.session_state.pop("pending_category")
with st.container(border=True):
    query = st.text_input("Search products", placeholder="Search by name, description or product ID", key="product_query")
    a, b, c = st.columns(3)
    category = a.selectbox("Category", ["All categories", *CATEGORY_NAMES],
                           format_func=lambda name: CATEGORY_NAMES.get(name, name), key="browse_category")
    max_price = b.number_input("Maximum price (INR)", min_value=0, max_value=1000000, value=100000,
                               step=1000, key="maximum_price")
    order = c.selectbox("Sort by", ["Featured", "Price: low to high", "Price: high to low", "Name"], key="product_sort")
    available_only = st.checkbox("In stock only", value=True, key="available_only")
matches = browse(products, query, category, max_price, available_only, order)
st.caption(f"{len(matches)} {'product' if len(matches) == 1 else 'products'} found")
if matches:
    product_grid(matches)
else:
    with st.container(border=True):
        st.subheader("No products found", anchor=False)
        st.write("Try another search, choose a different category or increase your maximum price.")
