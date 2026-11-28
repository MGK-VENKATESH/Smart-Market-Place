"""Reusable storefront components and cached catalogue loading."""
from html import escape
from pathlib import Path
import streamlit as st
from .catalogue import load_catalogue
from .storefront import CATEGORY_NAMES, product_description

ROOT = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = ROOT / "data/products_20.json"


@st.cache_data(max_entries=2, ttl=300, show_spinner=False)
def load_store_catalogue(modified_ns):
    return load_catalogue(CATALOGUE_PATH)


def get_products():
    return load_store_catalogue(CATALOGUE_PATH.stat().st_mtime_ns)


def initialize_state():
    st.session_state.setdefault("saved_products", set())
    st.session_state.setdefault("browse_category", "All categories")


def toggle_saved(identifier):
    saved = set(st.session_state.saved_products)
    if identifier in saved:
        saved.remove(identifier)
    else:
        saved.add(identifier)
    st.session_state.saved_products = saved


def browse_category(category):
    st.session_state["pending_category"] = category


def stock_label(product):
    if product.stock == 0:
        st.markdown(":gray-badge[Out of stock]")
    elif product.stock <= 3:
        st.markdown(f":orange-badge[Only {product.stock} left]")
    else:
        st.markdown(":green-badge[In stock]")


def save_button(product, context):
    saved = product.id in st.session_state.saved_products
    st.button("Saved" if saved else "Save", icon=":material/bookmark:" if saved else ":material/bookmark_add:",
              key=f"save_{context}_{product.id}", on_click=toggle_saved, args=(product.id,),
              type="primary" if saved else "secondary", width="stretch")


@st.dialog("Product details", width="medium", on_dismiss="rerun")
def show_product(product):
    st.caption(f"{CATEGORY_NAMES[product.category]}  /  {product.id}")
    st.subheader(product.title, anchor=False)
    st.markdown(f"### ₹{product.price:,}")
    stock_label(product)
    st.write(product_description(product))
    st.caption(f"Product ID: {product.id} · Available quantity: {product.stock}")
    save_button(product, "details")


def product_grid(products, context="browse"):
    for offset in range(0, len(products), 2):
        columns = st.columns(2)
        for column, product in zip(columns, products[offset:offset + 2]):
            with column, st.container(border=True, key=f"card_{context}_{product.id}"):
                st.html(f"""
                <div class="product-meta"><span>{escape(CATEGORY_NAMES[product.category])}</span>
                    <code>{escape(product.id)}</code></div>
                <div class="product-line"><h3>{escape(product.title)}</h3><b>₹{product.price:,}</b></div>
                """)
                stock_label(product)
                details, save = st.columns(2)
                with details:
                    if st.button("View details", key=f"details_{context}_{product.id}", width="stretch"):
                        show_product(product)
                with save:
                    save_button(product, context)
