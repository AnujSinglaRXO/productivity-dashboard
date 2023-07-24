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
for map_col in ["Sub tasks", "Defects"]:
    df[map_col] = df[map_col].map(len)
data = DataFilterer(df)

st.title("Monthly Issues")
st.button("＋ Filter", on_click=fm.add_filter)

if st.session_state["filters"]:
    st.subheader("Filters")
for filter_id in st.session_state["filters"]:
    filter_data = fm.generate_filter(filter_id, df)
    filter_collection.append(filter_data)
data.filter_data(filter_collection)

st.subheader("Graph")
monthly_issues_plot = PlotManager.make_monthly_issues_plot(data)
if monthly_issues_plot:
    st.plotly_chart(monthly_issues_plot, use_container_width=True)


st.subheader("Data Preview")
st.dataframe(data.filtered_data, use_container_width=True)


st.sidebar.info(
    """
"Started" calculated from the date that the Jira ticket was moved away from the "Open" status.
"""
)
