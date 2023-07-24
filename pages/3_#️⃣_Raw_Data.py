import streamlit as st
from classes import FileManager, DataFilterer

st.set_page_config(
    page_title="RXO Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
with open("style/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

data = DataFilterer(FileManager.import_df("data/pr.pickle"))

st.title("Raw Data")
st.subheader("Data Preview")
st.dataframe(data.data, use_container_width=True)
