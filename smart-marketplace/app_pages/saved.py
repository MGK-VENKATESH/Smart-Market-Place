import streamlit as st
from marketplace.dashboard import get_products, product_grid

st.title("Saved products", anchor=False)
st.write("Products bookmarked during this browser connection.")
saved = [product for product in get_products() if product.id in st.session_state.saved_products]
if saved:
    st.caption(f"{len(saved)} saved {'product' if len(saved) == 1 else 'products'}")
    product_grid(saved, "saved")
else:
    with st.container(border=True):
        st.subheader("Make room for your favourites", anchor=False)
        st.write("Select Save on any product to keep it here.")
        if st.button("Explore products", type="primary", key="saved_browse"):
            st.switch_page("app_pages/catalogue.py")
