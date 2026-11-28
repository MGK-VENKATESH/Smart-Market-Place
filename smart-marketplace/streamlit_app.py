"""Run the inventory workspace with python -m streamlit run streamlit_app.py."""
import streamlit as st

from marketplace.dashboard import ROOT, initialize_state

st.set_page_config(page_title="Smart Marketplace", page_icon="◈", layout="wide")
initialize_state()
st.html(ROOT / "assets/workspace.css")

pages = [
    st.Page("app_pages/overview.py", title="Overview", icon=":material/space_dashboard:"),
    st.Page("app_pages/catalogue.py", title="Product catalogue", icon=":material/inventory_2:"),
    st.Page("app_pages/saved.py", title="Saved products", icon=":material/bookmarks:"),
    st.Page("app_pages/insights.py", title="Inventory insights", icon=":material/insert_chart:"),
]
current = st.navigation(pages, position="hidden")
with st.sidebar:
    st.html('<div class="brand"><span class="brand-mark" aria-hidden="true">◈</span><span>Smart<br>Marketplace</span></div>')
    with st.container(key="workspace_nav"):
        for page in pages:
            st.page_link(page, width="stretch")
    st.divider()
    st.caption("Sample catalogue · INR")

# Project identity is shown consistently above every page.
st.html("""
<header class="project-heading">
  <h1>Smart Marketplace Search and Real Time Analytics System</h1>
</header>
""")

current.run()
