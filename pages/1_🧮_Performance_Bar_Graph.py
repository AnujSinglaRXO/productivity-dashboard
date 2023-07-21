import streamlit as st
from classes import FileManager, DataFilterer, FilterManager, PlotManager

st.set_page_config(
    page_title="RXO Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
with open("style/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

if "filters" not in st.session_state:
    st.session_state["filters"] = []
filter_collection = []
fm = FilterManager(st.session_state)

df = FileManager.import_df("data/pr.pickle")
data = DataFilterer(df)

st.title("Performance Bar Graph")
st.button("＋ Filter", on_click=fm.add_filter)

if st.session_state["filters"]:
    st.subheader("Filters")
for filter_id in st.session_state["filters"]:
    filter_data = fm.generate_filter(filter_id, df)
    filter_collection.append(filter_data)
data.filter_data(filter_collection)


st.subheader("Color Column")
color_column = st.selectbox(
    "Color Column", ("Repository", "User"), label_visibility="collapsed"
)


st.subheader("Graph")
st.plotly_chart(
    PlotManager.make_performance_bar(data, color_column), use_container_width=True
)


st.subheader("Data Preview")
st.dataframe(data.filtered_data, use_container_width=True)
