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

st.title("Performance: Defects Caused")

st.sidebar.info(
    """
"Defects Discovered" is calculated from QA testing of the stories/tasks by each repository/user.
"""
)

st.button("＋ Filter", on_click=fm.add_filter)
if st.session_state["filters"]:
    st.subheader("Filters")
for filter_id in st.session_state["filters"]:
    filter_data = fm.generate_filter(filter_id, df, ["Defects", "Sub tasks"])
    filter_collection.append(filter_data)
data.filter_data(filter_collection)


st.subheader("Parameter")
param_cols = st.columns(4)
param_value = param_cols[0].selectbox(
    "Parameter", ("Repository", "User"), label_visibility="collapsed", key="param1"
)
param_rel = param_cols[1].selectbox(
    "Relationship",
    ("with at least", "with at most"),
    label_visibility="collapsed",
    key="param2",
)
param_rel_var = param_cols[3].selectbox(
    "Variable",
    ("Stories & Tasks Worked On", "Defects Discovered"),
    label_visibility="collapsed",
    key="param4",
)
param_rel_value = param_cols[2].number_input(
    "Value",
    min_value=1,
    max_value=data.get_performance_df(param_value, inplace=False)[param_rel_var].max(),
    value=1,
    label_visibility="collapsed",
    key="param3",
)


st.subheader("Graph")
st.plotly_chart(
    PlotManager.make_performance_bar(
        data, param_value, (param_rel, param_rel_value, param_rel_var)
    ),
    use_container_width=True,
)


st.subheader("Data Preview")
st.dataframe(data.filtered_data, use_container_width=True)
