import streamlit as st

import pickle
import uuid
from enum import Enum
import calendar

import pandas as pd
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)

import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go


class FilterType(Enum):
    CATEGORICAL = ("is in", "is not in")
    NUMERIC = ("==", "!=", ">", "<", ">=", "<=")
    DATETIME = ("since", "until", "on")


if "filters" not in st.session_state:
    st.session_state.filters = []
filter_collection = []

st.set_page_config(layout="wide", initial_sidebar_state="expanded")

with open("style/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def export_df(df: pd.DataFrame, file_path: str) -> None:
    with open(file_path, "wb") as f:
        pickle.dump(df, f)


def import_df(file_path: str) -> pd.DataFrame:
    with open(file_path, "rb") as f:
        return pickle.load(f)


def get_grouped_df(
    col1, col2, df, include_col1=None, include_col2=None
) -> pd.DataFrame:
    if include_col1:
        df = df[df[col1].isin(include_col1)]
    if include_col2:
        df = df[df[col2].isin(include_col2)]
    return df.groupby([col1, col2]).size().unstack().fillna(0).astype(int)


def get_total_df(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sum(axis=1).to_frame(name="Total").sort_values(by="Total", ascending=False)
    )


def make_donut(
    df: pd.DataFrame,
    title: str = None,
    hole: float = 0.5,
    width: int = 800,
    height: int = 600,
) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            labels=df.index,
            values=df["Total"],
            hole=hole,
            hoverinfo="label+percent",
            textinfo="value",
            textfont_size=20,
            textposition="inside",
        )
    )
    fig.update_layout(
        title=title,
        width=width,
        height=height,
    )
    return fig


def make_bar(
    df: pd.DataFrame, title: str = None, width: int = 800, height: int = 600
) -> go.Figure:
    fig = px.bar(
        df,
        x=df.index,
        y=df.columns,
        title=title,
        width=width,
        height=height,
    )
    fig.update_layout(
        barmode="stack",
    )
    return fig


def make_monthly_issues_plot(df: pd.DataFrame) -> plt.figure:
    # try:
    plot_data = df[(df["Started"].notnull())]
    plot_data = plot_data[["Issue Type", "Started"]].reset_index(drop=True)
    plot_data["Month"] = plot_data["Started"].apply(lambda x: x.strftime("%Y-%m"))
    plot_data = (
        plot_data.groupby(["Month", "Issue Type"]).size().reset_index(name="Count")
    )
    plot_data = plot_data.pivot(
        index="Month", columns="Issue Type", values="Count"
    ).fillna(0)

    # st.dataframe(plot_data)

    fig = go.Figure()

    bar_width = 1000000000
    if "Story" in plot_data.columns:
        fig.add_bar(
            x=plot_data.index,
            y=plot_data["Story"],
            name="Story",
            marker_color="limegreen",
            width=bar_width,
            offset=-bar_width,
        )
    if "Task" in plot_data.columns:
        fig.add_bar(
            x=plot_data.index,
            y=plot_data["Task"],
            name="Task",
            marker_color="deepskyblue",
            width=bar_width,
            offset=-bar_width,
            base=plot_data["Story"] if "Story" in plot_data.columns else None,
        )
    if "Defect (Standard)" in plot_data.columns:
        fig.add_bar(
            y=plot_data["Defect (Standard)"],
            x=plot_data.index,
            name="Defect (Standard)",
            marker_color="darkgrey",
            width=bar_width,
            offset=0,
        )
    if "Bug" in plot_data.columns:
        fig.add_bar(
            x=plot_data.index,
            y=plot_data["Bug"],
            name="Bug",
            marker_color="red",
            width=bar_width,
            offset=0,
            base=plot_data["Defect (Standard)"]
            if "Defect (Standard)" in plot_data.columns
            else None,
        )

    fig.update_layout(
        title="Issue Counts by Month",
        xaxis_title="Month Started (Moved Away from 'Open' Status)",
        yaxis_title="Count",
        xaxis_tickangle=0,
        legend_title="Issue Type",
        xaxis_ticktext=[
            f"{calendar.month_abbr[int(x.split('-')[1])]} {x.split('-')[0][-2:]}"
            for x in plot_data.index
        ],
        xaxis_tickvals=plot_data.index,
    )

    return fig


# except Exception:
#     st.error(f"Graph failed.")
#     return None

# params = (
#     "Repository",
#     "User",
#     "Merger",
#     # "Title",
#     # "Body",
#     "Changed Files",
#     "Deletions",
#     "Comments",
#     "Created",
#     'Closed',
#     'Merged',
#     'Updated',
#     "Issue Key",
#     "Issue Type",
#     "Sub tasks",
#     "Defects"
# )


def add_filter():
    filter_id = str(uuid.uuid4())
    st.session_state.filters.append(filter_id)


def remove_filter(filter_id):
    st.session_state.filters.remove(filter_id)


def generate_filter(filter_id, df):
    # filter_cols = st.sidebar.columns((2, 1, 3, 1))
    filter_cols = st.columns((2, 1, 3, 1))
    filter_param = filter_cols[0].selectbox(
        "Parameter",
        options=df.columns,
        key=f"{filter_id}_param",
        label_visibility="collapsed",
    )

    match df[filter_param].dtype.name:
        case "datetime64[ns]":
            operator_options = FilterType.DATETIME
        case "int64":
            operator_options = FilterType.NUMERIC
        case _:
            operator_options = FilterType.CATEGORICAL

    filter_operator = filter_cols[1].selectbox(
        "Operator",
        options=operator_options.value,
        key=f"{filter_id}_operator",
        label_visibility="collapsed",
    )

    match operator_options:
        case FilterType.CATEGORICAL:
            filter_value = filter_cols[2].multiselect(
                "Value",
                options=df[filter_param].unique(),
                key=f"{filter_id}_value",
                label_visibility="collapsed",
            )
        case FilterType.NUMERIC:
            filter_value = filter_cols[2].number_input(
                "Value",
                key=f"{filter_id}_value",
                label_visibility="collapsed",
                min_value=df[filter_param].min(),
                max_value=df[filter_param].max(),
            )
        case FilterType.DATETIME:
            filter_value = filter_cols[2].date_input(
                "Value",
                key=f"{filter_id}_value",
                label_visibility="collapsed",
                min_value=df[filter_param].min(),
                max_value=df[filter_param].max(),
                value=df[filter_param].max(),
            )

    filter_cols[3].button(
        "🗑",
        on_click=remove_filter,
        kwargs={"filter_id": filter_id},
        key=f"{filter_id}_remove",
    )

    return {
        "param": filter_param,
        "operator": filter_operator,
        "value": filter_value,
    }


def filter_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for filter_data in filter_collection:
        param = filter_data["param"]
        operator = filter_data["operator"]
        value = filter_data["value"]

        match operator:
            case "is in" if value:
                df = df[df[param].isin(value)]
            case "is not in" if value:
                df = df[~df[param].isin(value)]
            case "==":
                df = df[df[param] == value]
            case "!=":
                df = df[df[param] != value]
            case ">":
                df = df[df[param] > value]
            case ">=" | "since":
                df = df[df[param] >= value]
            case "<":
                df = df[df[param] < value]
            case "<=" | "until":
                df = df[df[param] <= value]

    return df


# st.sidebar.header("RXO Productivity Dashboard")
# st.sidebar.button("＋ Filter", on_click=add_filter)
st.header("RXO Productivity Dashboard")
st.button("＋ Filter", on_click=add_filter)

df = import_df("data/pr.pickle")
for map_col in ["Sub tasks", "Defects"]:
    df[map_col] = df[map_col].map(len)

for filter_id in st.session_state.filters:
    filter_data = generate_filter(filter_id, df)
    filter_collection.append(filter_data)

st.markdown("### Graphs")
monthly_issues_plot = make_monthly_issues_plot(filter_df(df))
if monthly_issues_plot:
    st.plotly_chart(monthly_issues_plot, use_container_width=True)


st.markdown("### Data Preview")
st.dataframe(filter_df(df))

# for filter_id in st.session_state.filters:
#     filter_data = generate_filter(filter_id, df)
#     filter_collection.append(filter_data)
