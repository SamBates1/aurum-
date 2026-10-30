"""Entry point for the online dashboard (Streamlit Community Cloud).

Opens straight onto the pages that matter for decisions; the research home page (app.py) trains models and is too
heavy for the free server. Run locally with `python -m streamlit run app.py` as before.
Paper trading only: nothing here places an order.
"""

import streamlit as st

pages = [
    st.Page("pages/1_Live_Analysis.py", title="Live Analysis", icon="📈", default=True),
    st.Page("pages/6_Market_Overview.py", title="Market Overview", icon="🗺️"),
    st.Page("pages/7_Portfolio.py", title="Portfolio", icon="💼"),
    st.Page("pages/0_Decision_Board.py", title="Decision Board", icon="🎯"),
    st.Page("pages/3_Paper_Strategies.py", title="Paper Strategies", icon="🧾"),
    st.Page("pages/4_Strategy_Registry.py", title="Strategy Registry", icon="📚"),
]
st.navigation(pages).run()
