import logging

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from wakatime_tracker.database.manager import DatabaseManager

logger = logging.getLogger(__name__)

# Настройка страницы
st.set_page_config(page_title="WakaTime dashboard", page_icon="⏱️", layout="wide")


# Инициализация
@st.cache_resource
def get_db():
    return DatabaseManager()


def seconds_to_hms(seconds):
    """Конвертировать секунды в формат 'Xh Ym Zs'"""
    if pd.isna(seconds) or seconds == 0:
        return "0s"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:  # Показываем секунды если нет часов и минут
        parts.append(f"{secs}s")

    return " ".join(parts)


def seconds_to_hms_short(seconds):
    """Короткий формат для метрик"""
    if pd.isna(seconds) or seconds == 0:
        return "0s"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}h {minutes}m"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def format_metric_value(seconds):
    """Форматирование значений для метрик Streamlit"""
    return seconds_to_hms_short(seconds)


db = get_db()


def main():
    st.title("⏱️ WakaTime analytics dashboard")

    # Сайдбар с фильтрами
    st.sidebar.header("Filters")

    # Выбор дат
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=30)

    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("Start date", start_date)
    with col2:
        end_date = st.date_input("End date", end_date)

    # Выбор проектов
    projects = db.get_unique_projects()
    selected_projects = st.sidebar.multiselect("Select projects", projects, default=[])

    # Получение данных
    data = db.get_project_stats(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

    if not data:
        st.warning("No data found for selected period")
        return

    df = pd.DataFrame(data)

    # Фильтрация по выбранным проектам
    if selected_projects:
        df = df[df["project_name"].isin(selected_projects)]

    # Вкладки
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Time analysis", "Project details", "Raw data"])

    with tab1:
        show_overview(df, start_date, end_date)

    with tab2:
        show_time_analysis(df, start_date, end_date)

    with tab3:
        show_project_details(df, start_date, end_date)

    with tab4:
        show_raw_data(df)


def show_overview(df, start_date, end_date):
    st.header("Overview")

    # Ключевые метрики
    col1, col2, col3, col4 = st.columns(4)

    total_seconds = df["total_seconds"].sum()
    days_count = (end_date - start_date).days + 1
    avg_daily_seconds = total_seconds / days_count if days_count > 0 else total_seconds
    unique_projects = df["project_name"].nunique()
    total_days = df["date"].nunique()

    col1.metric("Total time", format_metric_value(total_seconds))
    col2.metric("Daily average", format_metric_value(avg_daily_seconds))
    col3.metric("Projects", unique_projects)
    col4.metric("Days tracked", total_days)

    # Топ проектов по времени
    st.subheader("Top projects by time")
    project_totals = df.groupby("project_name")["total_seconds"].sum().sort_values(ascending=False)

    # Создаем DataFrame для графика с отформатированными метками
    plot_data = pd.DataFrame(
        {
            "project": project_totals.index,
            "seconds": project_totals.values,
            "time_display": [seconds_to_hms(sec) for sec in project_totals.values],
        }
    )

    fig = px.bar(
        plot_data,
        x="project",
        y="seconds",
        labels={"project": "Project", "seconds": "Time"},
        title="Total time by project",
        custom_data=["time_display"],  # Добавляем отформатированное время для tooltip
    )

    # Настраиваем отображение времени в tooltip
    fig.update_traces(hovertemplate="<b>%{x}</b><br>Time: %{customdata[0]}<extra></extra>")

    # Настраиваем ось Y для отображения времени
    fig.update_layout(xaxis_tickangle=-45, yaxis_title="Time (seconds)", xaxis_title="Project", hovermode="x unified")

    # Форматируем ось Y для показа времени
    fig.update_yaxes(
        tickformat=",",  # Формат чисел с разделителями
        tickvals=[3600, 7200, 10800, 14400, 18000],  # 1h, 2h, 3h, 4h, 5h
        ticktext=["1h", "2h", "3h", "4h", "5h"],
    )

    st.plotly_chart(fig, use_container_width=True)

    # Распределение времени по дням недели
    st.subheader("Time distribution by day of week")
    df_copy = df.copy()
    df_copy["date"] = pd.to_datetime(df_copy["date"])
    df_copy["day_of_week"] = df_copy["date"].dt.day_name()

    day_totals = (
        df_copy.groupby("day_of_week")["total_seconds"]
        .sum()
        .reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    )

    # Создаем данные для графика с отформатированными метками
    day_plot_data = pd.DataFrame(
        {
            "day": day_totals.index,
            "seconds": day_totals.values,
            "time_display": [seconds_to_hms(sec) for sec in day_totals.values],
        }
    )

    fig = px.bar(
        day_plot_data,
        x="day",
        y="seconds",
        labels={"day": "Day of week", "seconds": "Time"},
        title="Total time by day of week",
        custom_data=["time_display"],
    )

    fig.update_traces(hovertemplate="<b>%{x}</b><br>Time: %{customdata[0]}<extra></extra>")

    fig.update_yaxes(
        tickformat=",", tickvals=[3600, 7200, 10800, 14400, 18000], ticktext=["1h", "2h", "3h", "4h", "5h"]
    )

    st.plotly_chart(fig, use_container_width=True)


def show_time_analysis(df, start_date, end_date):
    st.header("Time analysis")

    # Ежедневная активность
    daily_totals = df.groupby("date")["total_seconds"].sum().reset_index()
    daily_totals["date"] = pd.to_datetime(daily_totals["date"])

    # Добавляем отформатированное время для tooltip
    daily_totals["time_display"] = daily_totals["total_seconds"].apply(seconds_to_hms)

    fig = px.line(
        daily_totals,
        x="date",
        y="total_seconds",
        title="Daily coding activity",
        labels={"total_seconds": "Time", "date": "Date"},
        custom_data=["time_display"],
    )

    fig.update_traces(hovertemplate="<b>%{x}</b><br>Time: %{customdata[0]}<extra></extra>", mode="lines+markers")

    fig.update_yaxes(
        title_text="Time",
        tickformat=",",
        tickvals=[3600, 7200, 10800, 14400, 18000, 21600, 25200, 28800],  # до 8 часов
        ticktext=["1h", "2h", "3h", "4h", "5h", "6h", "7h", "8h"],
    )

    st.plotly_chart(fig, use_container_width=True)

    # Heatmap по дням недели и неделям
    st.subheader("Activity heatmap")

    df_copy = df.copy()
    df_copy["date"] = pd.to_datetime(df_copy["date"])
    df_copy["day_of_week"] = df_copy["date"].dt.day_name()
    df_copy["week"] = df_copy["date"].dt.isocalendar().week
    df_copy["year"] = df_copy["date"].dt.year

    # Создаем полную сетку дат
    all_dates = pd.date_range(start=start_date, end=end_date, freq="D")
    all_days_df = pd.DataFrame(
        {
            "date": all_dates,
            "day_of_week": all_dates.day_name(),
            "week": all_dates.isocalendar().week,
            "year": all_dates.year,
        }
    )

    # Объединяем с данными
    heatmap_data = all_days_df.merge(
        df_copy.groupby("date")["total_seconds"].sum().reset_index(), on="date", how="left"
    ).fillna(0)

    # Создаем pivot таблицу для heatmap
    pivot_data = heatmap_data.pivot_table(
        index="day_of_week",
        columns=heatmap_data["date"].dt.strftime("%Y-%m-%d"),
        values="total_seconds",
        aggfunc="sum",
        fill_value=0,
    )

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot_data = pivot_data.reindex(days_order)

    fig = px.imshow(
        pivot_data,
        title="Activity heatmap by day of week",
        aspect="auto",
        color_continuous_scale="Blues",
        labels=dict(x="Date", y="Day of week", color="Time (seconds)"),
    )

    # Форматируем цветовую шкалу
    fig.update_coloraxes(colorbar=dict(tickvals=[0, 3600, 7200, 10800, 14400], ticktext=["0", "1h", "2h", "3h", "4h"]))

    st.plotly_chart(fig, use_container_width=True)

    # Тренды по неделям
    st.subheader("Weekly trends")
    weekly_totals = df_copy.groupby(["year", "week"])["total_seconds"].sum().reset_index()
    weekly_totals["week_label"] = weekly_totals["year"].astype(str) + "-W" + weekly_totals["week"].astype(str)
    weekly_totals["time_display"] = weekly_totals["total_seconds"].apply(seconds_to_hms)

    fig = px.bar(
        weekly_totals,
        x="week_label",
        y="total_seconds",
        title="Weekly coding activity",
        labels={"total_seconds": "Time", "week_label": "Week"},
        custom_data=["time_display"],
    )

    fig.update_traces(hovertemplate="<b>%{x}</b><br>Time: %{customdata[0]}<extra></extra>")

    fig.update_layout(xaxis_tickangle=-45)
    fig.update_yaxes(
        tickformat=",",
        tickvals=[0, 18000, 36000, 54000, 72000],  # до 20 часов в неделю
        ticktext=["0", "5h", "10h", "15h", "20h"],
    )

    st.plotly_chart(fig, use_container_width=True)


def show_project_details(df, start_date, end_date):
    st.header("Project details")

    # Выбор проекта для детального анализа
    selected_project = st.selectbox("Select project", df["project_name"].unique())

    if selected_project:
        project_data = df[df["project_name"] == selected_project]

        # Статистика проекта
        col1, col2, col3, col4 = st.columns(4)

        total_seconds = project_data["total_seconds"].sum()
        avg_daily_seconds = total_seconds / len(project_data) if len(project_data) > 0 else 0
        days_worked = project_data["date"].nunique()
        max_daily_seconds = project_data["total_seconds"].max() if len(project_data) > 0 else 0

        col1.metric("Total time", format_metric_value(total_seconds))
        col2.metric("Daily average", format_metric_value(avg_daily_seconds))
        col3.metric("Days worked", days_worked)
        col4.metric("Max daily", format_metric_value(max_daily_seconds))

        col1, col2 = st.columns(2)

        with col1:
            # Время по дням для выбранного проекта
            project_daily = project_data.groupby("date")["total_seconds"].sum().reset_index()
            project_daily["date"] = pd.to_datetime(project_daily["date"])
            project_daily["time_display"] = project_daily["total_seconds"].apply(seconds_to_hms)

            fig = px.bar(
                project_daily,
                x="date",
                y="total_seconds",
                title=f"Daily activity for {selected_project}",
                labels={"total_seconds": "Time", "date": "Date"},
                custom_data=["time_display"],
            )

            fig.update_traces(hovertemplate="<b>%{x}</b><br>Time: %{customdata[0]}<extra></extra>")

            fig.update_yaxes(
                tickformat=",",
                tickvals=[0, 1800, 3600, 5400, 7200, 9000],  # до 2.5 часов
                ticktext=["0", "30m", "1h", "1h30m", "2h", "2h30m"],
            )

            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Распределение по дням недели для проекта
            project_data_copy = project_data.copy()
            project_data_copy["date"] = pd.to_datetime(project_data_copy["date"])
            project_data_copy["day_of_week"] = project_data_copy["date"].dt.day_name()

            day_distribution = (
                project_data_copy.groupby("day_of_week")["total_seconds"]
                .sum()
                .reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], fill_value=0)
            )

            # Создаем данные для круговой диаграммы
            pie_data = pd.DataFrame(
                {
                    "day": day_distribution.index,
                    "seconds": day_distribution.values,
                    "time_display": [seconds_to_hms(sec) for sec in day_distribution.values],
                }
            )

            fig = px.pie(
                pie_data,
                values="seconds",
                names="day",
                title=f"Time distribution by day for {selected_project}",
                custom_data=["time_display"],
            )

            fig.update_traces(
                hovertemplate="<b>%{label}</b><br>Time: %{customdata[0]}<br>Percentage: %{percent}<extra></extra>",
                textinfo="percent+label",
            )

            st.plotly_chart(fig, use_container_width=True)

        # Прогресс проекта во времени (кумулятивная сумма)
        st.subheader("Project progress over time")
        project_data_sorted = project_data.sort_values("date")
        project_data_sorted["cumulative_seconds"] = project_data_sorted["total_seconds"].cumsum()
        project_data_sorted["date"] = pd.to_datetime(project_data_sorted["date"])
        project_data_sorted["cumulative_display"] = project_data_sorted["cumulative_seconds"].apply(seconds_to_hms)

        fig = px.line(
            project_data_sorted,
            x="date",
            y="cumulative_seconds",
            title=f"Cumulative time spent on {selected_project}",
            labels={"cumulative_seconds": "Cumulative time", "date": "Date"},
            custom_data=["cumulative_display"],
        )

        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>Cumulative time: %{customdata[0]}<extra></extra>", mode="lines+markers"
        )

        fig.update_yaxes(
            tickformat=",", tickvals=[0, 3600, 7200, 10800, 14400, 18000], ticktext=["0", "1h", "2h", "3h", "4h", "5h"]
        )

        st.plotly_chart(fig, use_container_width=True)


def show_raw_data(df):
    st.header("Raw data")

    # Показываем только основные колонки
    display_columns = ["date", "project_name", "total_seconds", "digital_time", "text_time", "percent"]
    display_df = df[display_columns].copy()

    # Добавляем отформатированное время
    display_df["time_formatted"] = display_df["total_seconds"].apply(seconds_to_hms)

    # Переупорядочиваем колонки для лучшего отображения
    display_df = display_df[
        ["date", "project_name", "time_formatted", "total_seconds", "digital_time", "text_time", "percent"]
    ]
    display_df = display_df.rename(columns={"time_formatted": "time"})

    st.dataframe(display_df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)

    # Скачивание данных
    csv = display_df.to_csv(index=False)
    st.download_button(label="Download data as CSV", data=csv, file_name="wakatime_data.csv", mime="text/csv")


if __name__ == "__main__":
    main()
