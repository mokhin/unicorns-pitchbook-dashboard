import altair as alt
import polars as pl
import streamlit as st

alt.themes.enable("vox")

st.set_page_config(
    page_title="Europe's Unicorn Startups",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DATA_FILE = "unicorns-pitchbook.csv"


# Functions
@st.cache_data
def prepare_dataset(data_file: str) -> pl.DataFrame:
    # Read the csv file
    df = pl.read_csv(data_file)

    # Filter the dataframe to only include European countries
    european_countries = [
        "Austria",
        "Belgium",
        "Bulgaria",
        "Croatia",
        "Cyprus",
        "Czech Republic",
        "Denmark",
        "Estonia",
        "Finland",
        "France",
        "Germany",
        "Greece",
        "Hungary",
        "Ireland",
        "Italy",
        "Latvia",
        "Lithuania",
        "Luxembourg",
        "Malta",
        "Netherlands",
        "Poland",
        "Portugal",
        "Romania",
        "Slovakia",
        "Slovenia",
        "Spain",
        "Sweden",
        "United Kingdom",
    ]

    df = df.filter(pl.col("country").is_in(european_countries))

    # Rename United Kingdom to UK

    df = df.with_columns(pl.col("country").str.replace(r"United Kingdom", "UK"))

    # Filter out only Active and Exited companies
    df = df.filter(pl.col("status").is_in(["Active", "Exited"]))

    # Delete $ symbol from raised_usd and valuation_usd columns
    # And convert M and B to numbers and N/A to 0
    df = df.with_columns(
        pl.col("raised_usd")
        .str.replace("N/A", "0")
        .str.replace("\\$", "")
        .str.replace("M", "e6")
        .str.replace("B", "e9")
        .cast(pl.Float64)
        .mul(1 / 1e9)
        .alias("raised_usd")
    )

    df = df.with_columns(
        pl.col("valuation_usd")
        .str.replace("N/A", "0")
        .str.replace("\\$", "")
        .str.replace("M", "e6")
        .str.replace("B", "e9")
        .cast(pl.Float64)
        .mul(1 / 1e9)
        .alias("valuation_usd")
    )

    # Extract the year from the founded column
    df = df.with_columns(
        pl.col("unicorn_month")
        .str.extract(r"(\d{4})")
        .cast(pl.Int32)
        .alias("unicorn_year")
    )
    return df


def bar_chart(
    df: pl.DataFrame,
    y: str,
    x: str,
    func: str,
    title: str = "",
    is_y_label: bool = True,
) -> alt.Chart:
    bars = (
        alt.Chart(df, title=title)
        .mark_bar()
        .encode(
            y=alt.Y(
                f"{y}:N",
                sort=alt.EncodingSortField(op="count", order="descending"),
                title=None,
                axis=alt.Axis(
                    labelColor="black",
                    labelBaseline="middle",
                    labels=is_y_label,
                    labelPadding=80,
                ),
            ),
            x=alt.X(f"{func}({x})", title=None, axis=None),
        )
    )

    text = bars.mark_text(
        align="left",
        baseline="middle",
        dx=3,
    ).encode(text=f"{func}({x}):Q")

    return (bars + text).properties(width=1000 / 4)


def combine_bar_charts(*plots):
    combined = alt.vconcat()
    for plot in plots:
        combined |= plot
    return (
        combined.configure_view(stroke=None)
        .configure_concat(spacing=10)
        .configure_axisY(labelPadding=70, labelAlign="left")
    )


def main():
    # Main dataset
    df = prepare_dataset(DATA_FILE)

    # Page layout
    st.markdown("## Europe's Unicorn Startups")
    st.markdown(
        "##### Source: [Pitchbook](https://pitchbook.com/news/articles/unicorn-startups-list-trends)"
    )

    # Filters
    col_1, col_2, col_3, _ = st.columns([1, 1, 1, 3])

    # Total scorecards
    col_1, col_2, col_3, _ = st.columns([2, 1.5, 1.5, 1.5])
    with col_1:
        st.metric(label="Total Unicorns", value=df.height)

    with col_2:
        st.metric(label="Total Valuation ($B)", value=df["valuation_usd"].sum())

    with col_3:
        st.metric(label="Total Funding ($B)", value=df["raised_usd"].sum())

    with col_1:
        location = st.selectbox(
            "Select country",
            ["All"] + sorted(df["country"].unique()),
        )

    with col_2:
        industry = st.selectbox(
            "Select industry",
            ["All"] + sorted(df["vertical"].unique()),
        )

    # Add a filter for the year
    with col_3:
        year_1b = st.slider(
            "Select year",
            min_value=df["unicorn_year"].min(),
            max_value=df["unicorn_year"].max(),
            value=(df["unicorn_year"].min(), df["unicorn_year"].max()),
            step=1,
        )

    # Filter polars dataframe
    if location == "All":
        filtered_df = df
    else:
        filtered_df = df.filter(pl.col("country") == location)

    if industry != "All":
        filtered_df = filtered_df.filter(pl.col("vertical") == industry)

    filtered_df = filtered_df.filter(
        (pl.col("unicorn_year") >= year_1b[0]) & (pl.col("unicorn_year") <= year_1b[1])
    )

    # Display the charts

    st.altair_chart(
        combine_bar_charts(
            bar_chart(
                df=filtered_df,
                y="country",
                x="company",
                func="count",
                title="Number of Unicorns",
            ),
            bar_chart(
                df=filtered_df,
                y="country",
                x="valuation_usd",
                func="sum",
                title="Valuation ($B)",
                is_y_label=False,
            ),
            bar_chart(
                df=filtered_df,
                y="country",
                x="raised_usd",
                func="sum",
                title="Total Funding ($B)",
                is_y_label=False,
            ),
        ),
    )

    st.markdown("##### ")

    st.altair_chart(
        combine_bar_charts(
            bar_chart(
                df=filtered_df,
                y="vertical",
                x="company",
                func="count",
                title="Number of Unicorns",
            ),
            bar_chart(
                df=filtered_df,
                y="vertical",
                x="valuation_usd",
                func="sum",
                title="Valuation ($B)",
                is_y_label=False,
            ),
            bar_chart(
                df=filtered_df,
                y="vertical",
                x="raised_usd",
                func="sum",
                title="Total Funding ($B)",
                is_y_label=False,
            ),
        ),
    )

    st.altair_chart(
        alt.Chart(filtered_df)
        .mark_bar()
        .encode(
            x=alt.X("unicorn_year:O", title=None),
            y=alt.Y("count()", title="Number of Unicorns"),
            color=alt.Color(
                "country:N", sort=alt.EncodingSortField(op="count", order="descending")
            ),
            order=alt.Order(
                "count()",
                sort="descending",
            ),
            tooltip=["country", "count()"],
        )
        .properties(width=1000, height=400)
    )

    st.altair_chart(
        alt.Chart(filtered_df)
        .mark_bar()
        .encode(
            x=alt.X("unicorn_year:O", title=None),
            y=alt.Y("count()", title="Number of Unicorns"),
            color=alt.Color(
                "vertical:N", sort=alt.EncodingSortField(op="count", order="descending")
            ),
            order=alt.Order(
                "count()",
                sort="descending",
            ),
            tooltip=["vertical", "count()"],
        )
        .properties(width=1000, height=400)
    )

    st.dataframe(
        filtered_df.select(
            [
                "company",
                "vertical",
                "country",
                "unicorn_year",
                "valuation_usd",
                "raised_usd",
            ]
        ),
        column_config={
            "company": st.column_config.TextColumn(
                "Company",
                help="The name of the company",
            ),
            "vertical": st.column_config.TextColumn(
                "Vertical",
                help="The industry vertical of the company",
            ),
            "country": st.column_config.TextColumn(
                "Country",
                help="The country where the company is based",
            ),
            "unicorn_year": st.column_config.NumberColumn(
                "1$ B Year",
                help="The year the company was valued at $1B",
                min_value=2000,
                max_value=2024,
                step=1,
                format="%d",
            ),
            "valuation_usd": st.column_config.NumberColumn(
                "Valuation ($B)",
                help="The valuation of the company in $B",
                min_value=1,
                max_value=1000,
                step=0.1,
                format="%0.1f",
            ),
            "raised_usd": st.column_config.NumberColumn(
                "Total Funding ($B)",
                help="The total funding raised by the company in $B",
                min_value=1,
                max_value=1000,
                step=0.1,
                format="%0.2f",
            ),
        },
    )


if __name__ == "__main__":
    main()
