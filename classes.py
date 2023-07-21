import streamlit as st
import pandas as pd
import uuid
import pickle
from enum import Enum
import calendar

import plotly.express as px
import plotly.graph_objects as go


class FileManager:
    @staticmethod
    def import_df(file_path: str) -> pd.DataFrame:
        with open(file_path, "rb") as f:
            return pickle.load(f)

    @staticmethod
    def export_df(df: pd.DataFrame, file_path: str) -> None:
        with open(file_path, "wb") as f:
            pickle.dump(df, f)


class DataFilterer:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.filtered_data = data

    def reset(self):
        self.filtered_data = self.data

    def filter_data(self, filter_collection: list):
        if not filter_collection:
            return self.data

        df = self.data.copy()

        for filter_data in filter_collection:
            param = filter_data["param"]
            operator = filter_data["operator"]
            value = filter_data["value"]

            if isinstance(value, list) and not value:
                continue

            match operator:
                case "is in":
                    df = df[df[param].isin(value)]
                case "is not in":
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

        self.filtered_data = df

        return df

    def get_performance_df(self, col: str) -> pd.DataFrame:
        col_log = {}
        for key in [col, "Stories & Tasks Worked On", "Defects Discovered"]:
            col_log[key] = []

        for col_item in self.filtered_data[col].unique():
            col_data_df = self.filtered_data[
                (self.filtered_data[col] == col_item)
                & (self.filtered_data["Issue Type"].isin(["Story", "Task"]))
            ].drop_duplicates(subset="Issue Key")
            col_log[col].append(col_item)
            col_log["Stories & Tasks Worked On"].append(len(col_data_df))
            col_log["Defects Discovered"].append(
                len(
                    set(
                        [
                            defect
                            for defects in col_data_df["Defects"].values
                            for defect in defects
                        ]
                    )
                )
            )

        col_df = pd.DataFrame(col_log)
        col_df["Ratio"] = (
            col_df["Defects Discovered"] / col_df["Stories & Tasks Worked On"]
        )
        col_df = (
            col_df[col_df["Stories & Tasks Worked On"] > 0]
            .sort_values(
                by=["Ratio", "Stories & Tasks Worked On"], ascending=[True, False]
            )
            .drop(columns="Ratio")
            .reset_index(drop=True)
        )

        self.filtered_data = col_df
        return col_df

    def group_df(
        self,
        param1_value: str,
        param2_value: str,
        param1_include: list,
        param2_include: list,
    ) -> pd.DataFrame:
        df = self.data.copy()
        if param1_include:
            df = df[df[param1_value].isin(param1_include)]
        if param2_include:
            df = df[df[param2_value].isin(param2_include)]

        self.filtered_data = (
            df.groupby([param1_value, param2_value])
            .size()
            .unstack()
            .fillna(0)
            .astype(int)
        )

        return self.filtered_data

    def get_total_df(self):
        return (
            self.filtered_data.sum(axis=1)
            .to_frame(name="Total")
            .sort_values(by="Total", ascending=False)
        )


class FilterType(Enum):
    CATEGORICAL = ("is in", "is not in")
    NUMERIC = ("==", "!=", ">", "<", ">=", "<=")
    DATETIME = ("since", "until", "on")


class FilterManager:
    def __init__(self, session_state: st.session_state):
        self.filters = session_state["filters"] if "filters" in session_state else []

    def add_filter(self):
        self.filters.append(str(uuid.uuid4()))

    def remove_filter(self, filter_id: str):
        self.filters.remove(filter_id)

    def generate_filter(self, filter_id: str, df: pd.DataFrame):
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
                    value=df[filter_param].min(),
                )

        filter_cols[3].button(
            "🗑",
            on_click=self.remove_filter,
            kwargs={"filter_id": filter_id},
            key=f"{filter_id}_remove",
        )

        return {
            "id": filter_id,
            "param": filter_param,
            "operator": filter_operator,
            "value": pd.to_datetime(filter_value)
            if operator_options == FilterType.DATETIME
            else filter_value,
            "filter_cols": filter_cols,
        }


class PlotManager:
    @staticmethod
    def make_monthly_issues_plot(data: DataFilterer) -> go.Figure:
        try:
            plot_data = data.filtered_data[(data.filtered_data["Started"].notnull())]
            plot_data = plot_data[["Issue Type", "Started"]].reset_index(drop=True)
            plot_data["Month"] = plot_data["Started"].apply(
                lambda x: x.strftime("%Y-%m")
            )
            plot_data = (
                plot_data.groupby(["Month", "Issue Type"])
                .size()
                .reset_index(name="Count")
            )
            plot_data = plot_data.pivot(
                index="Month", columns="Issue Type", values="Count"
            ).fillna(0)

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
                title="Issues Worked On by Month",
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

        except:
            st.error(f"Graph failed.")
            return None

    @staticmethod
    def make_donut(
        data: DataFilterer,
        title: str = None,
        hole: float = 0.5,
    ) -> go.Figure:
        df = data.get_total_df()
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
        fig.update_layout(title=title)
        return fig

    @staticmethod
    def make_stacked_bar(data: DataFilterer, title: str = None) -> go.Figure:
        fig = px.bar(
            data.filtered_data,
            x=data.filtered_data.index,
            y=data.filtered_data.columns,
            title=title,
            barmode="stack",
        )
        return fig

    @staticmethod
    def make_performance_bar(
        data: DataFilterer, col: str, title: str = None
    ) -> go.Figure:
        fig = go.Figure()
        performance_df = data.get_performance_df(col)
        fig.add_trace(
            go.Bar(
                x=performance_df[col],
                y=performance_df["Stories & Tasks Worked On"],
                name="Stories & Tasks Worked On",
                marker_color="limegreen",
            )
        )
        fig.add_trace(
            go.Bar(
                x=performance_df[col],
                y=performance_df["Defects Discovered"],
                name="Defects Discovered",
                marker_color="red",
            )
        )
        fig.update_layout(
            title=title if title else f"{col} Performance",
            xaxis_title=col,
            yaxis_title="Count",
            barmode="group",
            bargap=0.15,
            bargroupgap=0.1,
        )

        if col == "User":
            fig.add_annotation(
                text="* Chart should ideally be by dev team, not individual devs",
                xref="paper",
                yref="paper",
                x=-0.05,
                y=1.2,
                showarrow=False,
                font=dict(size=14),
            )

        return fig
