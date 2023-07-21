import streamlit as st
from classes import FileManager, DataFilterer, PlotManager

st.set_page_config(
    page_title="RXO Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
with open("style/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

df = FileManager.import_df("data/pr.pickle")
data = DataFilterer(df)
params = ("Repository", "User", "Issue Type")

st.title("Compare Two Parameters")

st.subheader("Parameter 1")
param1_cols = st.columns(2)
param1_value = param1_cols[0].selectbox(
    "Choose a value:", params, index=0, key="param1_value"
)
param1_include = param1_cols[1].multiselect(
    "Include:",
    [val for val in data.data[param1_value].unique() if val == val],
    key="param1_include",
)

st.subheader("Parameter 2")
param2_cols = st.columns(2)
param2_value = param2_cols[0].selectbox(
    "Choose a value:", params, index=2, key="param2_value"
)
param2_include = param2_cols[1].multiselect(
    "Include:",
    [val for val in data.data[param2_value].unique() if val == val],
    key="param2_include",
)

data.group_df(param1_value, param2_value, param1_include, param2_include)

# chart_type = st.sidebar.selectbox(
#     "Choose Chart Type:", ("Donut", "Bar"), key="chart_type"
# )

st.write("<br>", unsafe_allow_html=True)
graph_cols = st.columns(5)
graph_cols[0].subheader("Graph")
chart_type = graph_cols[1].selectbox(
    "Chart Type:",
    ("Donut", "Bar"),
    key="chart_type",
)

if param1_value == param2_value:
    st.error("Please choose two different parameters.")
else:
    if chart_type == "Donut":
        st.plotly_chart(
            PlotManager.make_donut(
                data,
                title=f"{param1_value} - {param2_value} Totals",
            ),
            use_container_width=True,
        )
    elif chart_type == "Bar":
        st.plotly_chart(
            PlotManager.make_stacked_bar(
                data,
                title=f"{param1_value} - {param2_value}",
            ),
            use_container_width=True,
        )


st.markdown("### Data Preview")
st.dataframe(data.filtered_data, use_container_width=True)
