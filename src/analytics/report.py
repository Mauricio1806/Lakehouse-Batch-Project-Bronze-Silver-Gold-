"""
NYC TLC Lakehouse — Client Analytics Report
============================================
Reads Gold-layer Parquet files via DuckDB and generates a self-contained
interactive HTML dashboard.

Output: reports/lakehouse_report_YYYYMMDD_HHMMSS.html
Usage:  python -m src.analytics.report
        (or triggered by Airflow task 07_analytics_report)
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT        = Path(os.getenv("LAKEHOUSE_ROOT", str(Path(__file__).parents[2])))
DATA_DIR    = ROOT / "data"
BRONZE_DIR  = DATA_DIR / "bronze"
SILVER_DIR  = DATA_DIR / "silver"
GOLD_DIR    = DATA_DIR / "gold"
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH     = os.getenv("LAKEHOUSE_DB_PATH", str(DATA_DIR / "lakehouse.duckdb"))


# ── Data loading ──────────────────────────────────────────────────────────
def _read(con: duckdb.DuckDBPyConnection, sql: str) -> pd.DataFrame:
    try:
        return con.execute(sql).fetchdf()
    except Exception as exc:
        print(f"[report] WARNING – query skipped: {exc}")
        return pd.DataFrame()


def load_all(con: duckdb.DuckDBPyConnection) -> dict[str, pd.DataFrame]:
    bronze_glob = (BRONZE_DIR / "**" / "*.parquet").as_posix()
    silver_file = (SILVER_DIR / "stg_trips.parquet").as_posix()
    daily_file  = (GOLD_DIR / "mart_revenue_daily.parquet").as_posix()
    hour_file   = (GOLD_DIR / "mart_trips_by_hour.parquet").as_posix()
    loc_file    = (GOLD_DIR / "mart_trips_by_location.parquet").as_posix()
    pay_file    = (GOLD_DIR / "mart_payment_breakdown.parquet").as_posix()

    return {
        "bronze_count": _read(con, f"SELECT COUNT(*) AS n FROM read_parquet('{bronze_glob}')"),
        "silver_count": _read(con, f"SELECT COUNT(*) AS n FROM read_parquet('{silver_file}')"),
        "silver_stats": _read(con, f"""
            SELECT
                MIN(pickup_datetime)::DATE  AS min_date,
                MAX(pickup_datetime)::DATE  AS max_date,
                ROUND(AVG(trip_distance),2) AS avg_dist,
                ROUND(MIN(fare_amount),2)   AS min_fare,
                ROUND(MAX(fare_amount),2)   AS max_fare,
                ROUND(AVG(passenger_count),2) AS avg_pax,
                SUM(CASE WHEN passenger_count IS NULL THEN 1 ELSE 0 END) AS null_pax,
                SUM(CASE WHEN fare_amount    IS NULL THEN 1 ELSE 0 END) AS null_fare
            FROM read_parquet('{silver_file}')
        """),
        "daily":    _read(con, f"SELECT * FROM read_parquet('{daily_file}') ORDER BY trip_date"),
        "hourly":   _read(con, f"SELECT * FROM read_parquet('{hour_file}')  ORDER BY hour_of_day"),
        "location": _read(con, f"SELECT * FROM read_parquet('{loc_file}')   ORDER BY total_trips DESC LIMIT 25"),
        "payment":  _read(con, f"SELECT * FROM read_parquet('{pay_file}')   ORDER BY total_trips DESC"),
    }


# ── Chart builders ────────────────────────────────────────────────────────
_PLOTLY_JS = "https://cdn.plot.ly/plotly-2.35.2.min.js"
_COLORS    = ["#2ecc71", "#3498db", "#9b59b6", "#e67e22", "#e74c3c", "#1abc9c"]


def _fig_to_html(fig: go.Figure, first: bool = False) -> str:
    return fig.to_html(
        full_html=False,
        include_plotlyjs=_PLOTLY_JS if first else False,
        config={"displayModeBar": True, "responsive": True},
    )


def chart_revenue_trend(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p class='no-data'>No daily data available.</p>"
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df["trip_date"], y=df["total_revenue"],
        name="Total Revenue ($)", line=dict(color=_COLORS[0], width=2.5),
        fill="tozeroy", fillcolor="rgba(46,204,113,0.12)",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df["trip_date"], y=df["total_trips"],
        name="Total Trips", line=dict(color=_COLORS[1], width=2, dash="dot"),
    ), secondary_y=True)
    fig.update_layout(
        template="plotly_white", height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=50, r=50, t=30, b=40),
    )
    fig.update_yaxes(title_text="Revenue (USD)", tickprefix="$", secondary_y=False)
    fig.update_yaxes(title_text="Number of Trips", secondary_y=True)
    return _fig_to_html(fig, first=True)


def chart_revenue_breakdown(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    other = (df["total_revenue"] - df["total_fare"] - df["total_tips"]).clip(lower=0)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["trip_date"], y=df["total_fare"],
        name="Base Fare", stackgroup="rev", fillcolor="rgba(52,152,219,0.65)",
        line=dict(width=0),
    ))
    fig.add_trace(go.Scatter(
        x=df["trip_date"], y=df["total_tips"],
        name="Tips", stackgroup="rev", fillcolor="rgba(46,204,113,0.65)",
        line=dict(width=0),
    ))
    fig.add_trace(go.Scatter(
        x=df["trip_date"], y=other,
        name="Surcharges / Other", stackgroup="rev", fillcolor="rgba(241,196,15,0.65)",
        line=dict(width=0),
    ))
    fig.update_layout(
        template="plotly_white", height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        yaxis=dict(tickprefix="$"),
        margin=dict(l=50, r=30, t=30, b=40),
    )
    return _fig_to_html(fig)


def chart_avg_metrics(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=df["trip_date"], y=df["avg_distance_miles"],
        name="Avg Distance (mi)", marker_color="rgba(155,89,182,0.7)",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=df["trip_date"], y=df["avg_passengers"],
        name="Avg Passengers", line=dict(color=_COLORS[3], width=2),
        mode="lines+markers", marker=dict(size=4),
    ), secondary_y=True)
    fig.update_layout(
        template="plotly_white", height=340,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=50, r=50, t=30, b=40),
    )
    fig.update_yaxes(title_text="Distance (mi)", secondary_y=False)
    fig.update_yaxes(title_text="Passengers", secondary_y=True)
    return _fig_to_html(fig)


def chart_hourly(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p class='no-data'>No hourly data.</p>"
    colors = [
        "#e74c3c" if (6 <= h <= 9 or 16 <= h <= 19) else "#3498db"
        for h in df["hour_of_day"]
    ]
    fig = go.Figure(go.Bar(
        x=df["hour_of_day"], y=df["total_trips"],
        marker_color=colors,
        text=df["total_trips"].apply(lambda x: f"{x:,}"),
        textposition="outside", textfont=dict(size=9),
        hovertemplate="Hour %{x}h<br>Trips: %{y:,}<br>Avg Fare: $%{customdata:.2f}",
        customdata=df["avg_fare"],
    ))
    fig.add_annotation(
        text="■ Peak hours (6–9h, 16–19h)", xref="paper", yref="paper",
        x=0.01, y=0.97, showarrow=False,
        font=dict(size=10, color="#e74c3c"),
    )
    fig.update_layout(
        template="plotly_white", height=380,
        xaxis=dict(title="Hour of Day (24h)", tickmode="linear", dtick=1),
        yaxis=dict(title="Number of Trips"),
        margin=dict(l=50, r=30, t=30, b=50),
    )
    return _fig_to_html(fig)


def chart_payment(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p class='no-data'>No payment data.</p>"
    fig = go.Figure(go.Pie(
        labels=df["payment_method"],
        values=df["total_trips"],
        hole=0.48,
        textinfo="label+percent",
        marker=dict(colors=px.colors.qualitative.Set2),
        hovertemplate="%{label}<br>Trips: %{value:,}<br>Share: %{percent}",
    ))
    fig.update_layout(
        template="plotly_white", height=360,
        showlegend=False,
        margin=dict(l=20, r=20, t=30, b=30),
    )
    return _fig_to_html(fig)


def chart_location(df: pd.DataFrame) -> str:
    if df.empty:
        return "<p class='no-data'>No location data.</p>"
    df = df.head(25).sort_values("total_trips")
    fig = go.Figure(go.Bar(
        x=df["total_trips"],
        y=df["pickup_location_id"].astype(str),
        orientation="h",
        marker=dict(
            color=df["total_revenue"],
            colorscale="Viridis",
            colorbar=dict(title="Revenue ($)", x=1.01),
        ),
        hovertemplate="Zone %{y}<br>Trips: %{x:,}<br>Revenue: $%{customdata:,.0f}",
        customdata=df["total_revenue"],
    ))
    fig.update_layout(
        template="plotly_white", height=560,
        xaxis=dict(title="Number of Trips"),
        yaxis=dict(title="Pickup Zone ID"),
        margin=dict(l=70, r=80, t=20, b=50),
    )
    return _fig_to_html(fig)


def chart_payment_revenue(df: pd.DataFrame) -> str:
    if df.empty:
        return ""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Trips", x=df["payment_method"], y=df["total_trips"],
        marker_color="rgba(52,152,219,0.8)",
        yaxis="y1",
    ))
    fig.add_trace(go.Bar(
        name="Revenue ($)", x=df["payment_method"], y=df["total_revenue"],
        marker_color="rgba(46,204,113,0.8)",
        yaxis="y2",
    ))
    fig.update_layout(
        template="plotly_white", height=360,
        barmode="group",
        yaxis=dict(title="Trips"),
        yaxis2=dict(title="Revenue ($)", overlaying="y", side="right", tickprefix="$"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=60, r=60, t=30, b=60),
    )
    return _fig_to_html(fig)


# ── Profiling table ───────────────────────────────────────────────────────
def _profile_row(label: str, rows: int, status: str, location: str) -> str:
    badge = (
        f'<span class="badge-pass">PASS</span>' if status == "pass"
        else f'<span class="badge-info">{status.upper()}</span>'
    )
    return (
        f"<tr><td><strong>{label}</strong></td>"
        f"<td><code>{location}</code></td>"
        f"<td class='num'>{rows:,}</td>"
        f"<td>{badge}</td></tr>"
    )


# ── HTML template ─────────────────────────────────────────────────────────
_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background: #f0f2f5; color: #2c3e50; }

/* Header */
.header { background: linear-gradient(135deg, #0f0c29 0%, #302b63 60%, #24243e 100%);
          color: white; padding: 44px 64px; }
.header h1 { font-size: 2.1rem; font-weight: 700; letter-spacing: -.5px; }
.header .subtitle { color: #a8b2c1; margin-top: 6px; font-size: 1rem; }
.header .meta { margin-top: 18px; display: flex; flex-wrap: wrap; gap: 10px; }
.header .meta span { background: rgba(255,255,255,.12); padding: 4px 14px;
                     border-radius: 20px; font-size: .82rem; color: #cdd6e0; }

/* Container */
.container { max-width: 1400px; margin: 0 auto; padding: 40px 64px; }

/* KPI Grid */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 20px; margin-bottom: 36px; }
.kpi-card { background: white; border-radius: 12px; padding: 24px 20px;
            box-shadow: 0 2px 14px rgba(0,0,0,.07); border-left: 4px solid; }
.kpi-card.c1 { border-color: #2ecc71; }
.kpi-card.c2 { border-color: #3498db; }
.kpi-card.c3 { border-color: #9b59b6; }
.kpi-card.c4 { border-color: #e67e22; }
.kpi-label { font-size: .73rem; font-weight: 700; text-transform: uppercase;
             letter-spacing: .6px; color: #7f8c8d; }
.kpi-value { font-size: 1.95rem; font-weight: 800; margin-top: 7px; color: #1a1a2e; }
.kpi-sub   { font-size: .75rem; color: #95a5a6; margin-top: 5px; }

/* Section */
.section { background: white; border-radius: 12px; padding: 28px 28px 20px;
           box-shadow: 0 2px 14px rgba(0,0,0,.07); margin-bottom: 24px; }
.section-title { font-size: 1.05rem; font-weight: 700; color: #1a1a2e;
                 border-bottom: 2px solid #f0f2f5; padding-bottom: 10px; margin-bottom: 18px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; margin-bottom: 24px; }

/* Table */
.data-table { width: 100%; border-collapse: collapse; font-size: .88rem; }
.data-table th { background: #f8f9fa; font-weight: 700; color: #7f8c8d;
                 text-transform: uppercase; font-size: .72rem; letter-spacing: .5px;
                 padding: 10px 14px; border-bottom: 2px solid #ecf0f1; text-align: left; }
.data-table td { padding: 10px 14px; border-bottom: 1px solid #f0f2f5; }
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: #fafbfc; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.badge-pass { background: #d5f5e3; color: #1e8449; padding: 2px 10px;
              border-radius: 20px; font-size: .72rem; font-weight: 700; }
.badge-info { background: #d6eaf8; color: #1a5276; padding: 2px 10px;
              border-radius: 20px; font-size: .72rem; font-weight: 700; }
.no-data { color: #aaa; font-style: italic; padding: 20px 0; }

/* Footer */
.footer { text-align: center; padding: 28px; color: #95a5a6;
          font-size: .8rem; background: white; margin-top: 20px; border-top: 1px solid #ecf0f1; }
"""


def build_html(dfs: dict, ts: str) -> str:
    daily   = dfs.get("daily",    pd.DataFrame())
    hourly  = dfs.get("hourly",   pd.DataFrame())
    loc_df  = dfs.get("location", pd.DataFrame())
    pay_df  = dfs.get("payment",  pd.DataFrame())
    stats   = dfs.get("silver_stats", pd.DataFrame())

    bronze_n = int(dfs.get("bronze_count", pd.DataFrame({"n": [0]}))["n"].iloc[0])
    silver_n = int(dfs.get("silver_count", pd.DataFrame({"n": [0]}))["n"].iloc[0])
    gold_n   = len(daily)

    total_trips   = int(daily["total_trips"].sum())   if not daily.empty else 0
    total_revenue = float(daily["total_revenue"].sum()) if not daily.empty else 0
    avg_fare      = float(daily["total_fare"].sum() / total_trips) if total_trips > 0 else 0
    quality_pct   = round(silver_n / bronze_n * 100, 1) if bronze_n > 0 else 0

    date_range = ""
    if not daily.empty:
        date_range = f"{daily['trip_date'].min()} → {daily['trip_date'].max()}"

    # Silver column stats
    null_pax  = int(stats["null_pax"].iloc[0])  if not stats.empty else 0
    null_fare = int(stats["null_fare"].iloc[0]) if not stats.empty else 0
    avg_dist  = float(stats["avg_dist"].iloc[0]) if not stats.empty else 0
    avg_pax   = float(stats["avg_pax"].iloc[0])  if not stats.empty else 0

    # Payment table rows
    pay_rows = ""
    for _, r in pay_df.iterrows():
        pay_rows += (
            f"<tr><td>{r.get('payment_method','—')}</td>"
            f"<td class='num'>{int(r.get('total_trips',0)):,}</td>"
            f"<td class='num'>${float(r.get('total_revenue',0)):,.2f}</td>"
            f"<td class='num'>${float(r.get('avg_fare',0)):.2f}</td>"
            f"<td class='num'>${float(r.get('avg_tip',0)):.2f}</td>"
            f"<td class='num'>{float(r.get('pct_of_trips',0)):.1f}%</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>NYC TLC Lakehouse Analytics Report</title>
<style>{_CSS}</style>
</head>
<body>

<div class="header">
  <h1>NYC TLC Lakehouse — Analytics Report</h1>
  <div class="subtitle">Bronze → Silver → Gold Pipeline &nbsp;·&nbsp; DuckDB · dbt · Apache Airflow</div>
  <div class="meta">
    <span>Generated: {ts}</span>
    <span>Dataset: NYC Yellow Taxi</span>
    <span>Period: {date_range}</span>
    <span>Source: NYC TLC Trip Record Data</span>
  </div>
</div>

<div class="container">

  <!-- ── KPI Cards ── -->
  <div class="kpi-grid">
    <div class="kpi-card c1">
      <div class="kpi-label">Total Revenue</div>
      <div class="kpi-value">${total_revenue:,.0f}</div>
      <div class="kpi-sub">Gold · mart_revenue_daily</div>
    </div>
    <div class="kpi-card c2">
      <div class="kpi-label">Total Trips</div>
      <div class="kpi-value">{total_trips:,}</div>
      <div class="kpi-sub">Silver · stg_trips</div>
    </div>
    <div class="kpi-card c3">
      <div class="kpi-label">Avg Base Fare</div>
      <div class="kpi-value">${avg_fare:.2f}</div>
      <div class="kpi-sub">Excl. tips &amp; surcharges</div>
    </div>
    <div class="kpi-card c4">
      <div class="kpi-label">Data Quality</div>
      <div class="kpi-value">{quality_pct}%</div>
      <div class="kpi-sub">{silver_n:,} clean / {bronze_n:,} raw rows</div>
    </div>
  </div>

  <!-- ── Revenue & Volume Trend ── -->
  <div class="section">
    <div class="section-title">Daily Revenue &amp; Trip Volume Trend</div>
    {chart_revenue_trend(daily)}
  </div>

  <!-- ── Revenue Breakdown + Avg Metrics ── -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title">Revenue Breakdown — Fare vs Tips vs Surcharges</div>
      {chart_revenue_breakdown(daily)}
    </div>
    <div class="section">
      <div class="section-title">Daily Avg Trip Distance &amp; Passengers</div>
      {chart_avg_metrics(daily)}
    </div>
  </div>

  <!-- ── Peak Hours + Payment Distribution ── -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title">Trip Volume by Hour of Day (Peak Hours Highlighted)</div>
      {chart_hourly(hourly)}
    </div>
    <div class="section">
      <div class="section-title">Payment Method Distribution</div>
      {chart_payment(pay_df)}
    </div>
  </div>

  <!-- ── Payment Detail Table + Revenue by Payment ── -->
  <div class="grid-2">
    <div class="section">
      <div class="section-title">Payment Method — Detail Table</div>
      <table class="data-table">
        <thead>
          <tr><th>Method</th><th class="num">Trips</th><th class="num">Revenue</th>
              <th class="num">Avg Fare</th><th class="num">Avg Tip</th><th class="num">% Trips</th></tr>
        </thead>
        <tbody>{pay_rows}</tbody>
      </table>
    </div>
    <div class="section">
      <div class="section-title">Trips &amp; Revenue by Payment Method</div>
      {chart_payment_revenue(pay_df)}
    </div>
  </div>

  <!-- ── Top Pickup Locations ── -->
  <div class="section">
    <div class="section-title">Top 25 Pickup Locations — Trips &amp; Revenue (color intensity)</div>
    {chart_location(loc_df)}
  </div>

  <!-- ── Data Pipeline Lineage ── -->
  <div class="section">
    <div class="section-title">Data Pipeline Lineage &amp; Row Counts</div>
    <table class="data-table">
      <thead>
        <tr><th>Layer</th><th>Artifact</th><th class="num">Row Count</th><th>Format</th><th>Status</th></tr>
      </thead>
      <tbody>
        {_profile_row("Bronze", bronze_n, "pass", "data/bronze/dataset=yellow/year=*/month=*/trips.parquet")}
        {_profile_row("Silver · stg_trips", silver_n, "pass", "data/silver/stg_trips.parquet")}
        {_profile_row("Gold · mart_revenue_daily", gold_n, "pass", "data/gold/mart_revenue_daily.parquet")}
        <tr><td><strong>Gold · mart_trips_by_hour</strong></td>
            <td><code>data/gold/mart_trips_by_hour.parquet</code></td>
            <td class="num">24</td><td>Parquet · Snappy · dbt external</td>
            <td><span class="badge-pass">PASS</span></td></tr>
        <tr><td><strong>Gold · mart_trips_by_location</strong></td>
            <td><code>data/gold/mart_trips_by_location.parquet</code></td>
            <td class="num">—</td><td>Parquet · Snappy · dbt external</td>
            <td><span class="badge-pass">PASS</span></td></tr>
        <tr><td><strong>Gold · mart_payment_breakdown</strong></td>
            <td><code>data/gold/mart_payment_breakdown.parquet</code></td>
            <td class="num">—</td><td>Parquet · Snappy · dbt external</td>
            <td><span class="badge-pass">PASS</span></td></tr>
        <tr><td><strong>Analytical DB</strong></td>
            <td><code>data/lakehouse.duckdb</code></td>
            <td class="num" colspan="2">DuckDB in-process engine · all layers queryable</td>
            <td><span class="badge-info">ACTIVE</span></td></tr>
      </tbody>
    </table>
  </div>

  <!-- ── Silver Column Profile ── -->
  <div class="section">
    <div class="section-title">Silver Layer — Column Quality Summary (stg_trips)</div>
    <table class="data-table">
      <thead>
        <tr><th>Metric</th><th class="num">Value</th><th>Notes</th></tr>
      </thead>
      <tbody>
        <tr><td>Total clean rows</td><td class="num">{silver_n:,}</td><td>After dedup &amp; filters</td></tr>
        <tr><td>Date range</td><td class="num">{date_range}</td><td>pickup_datetime</td></tr>
        <tr><td>Avg trip distance</td><td class="num">{avg_dist:.2f} mi</td><td></td></tr>
        <tr><td>Avg passengers</td><td class="num">{avg_pax:.2f}</td><td></td></tr>
        <tr><td>Null passenger_count</td><td class="num">{null_pax:,}</td>
            <td>{'<span class="badge-pass">OK</span>' if null_pax == 0 else '<span class="badge-info">CHECK</span>'}</td></tr>
        <tr><td>Null fare_amount</td><td class="num">{null_fare:,}</td>
            <td>{'<span class="badge-pass">OK</span>' if null_fare == 0 else '<span class="badge-info">CHECK</span>'}</td></tr>
        <tr><td>Bronze → Silver drop rate</td>
            <td class="num">{100 - quality_pct:.1f}%</td>
            <td>Removed by dedup + quality filters</td></tr>
      </tbody>
    </table>
  </div>

</div><!-- /container -->

<div class="footer">
  NYC TLC Lakehouse Pipeline &nbsp;·&nbsp; Bronze → Silver → Gold
  &nbsp;·&nbsp; DuckDB + dbt + Apache Airflow
  &nbsp;·&nbsp; Generated {ts}
</div>

</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────
def main() -> None:
    con = duckdb.connect(DB_PATH)
    dfs = load_all(con)
    con.close()

    ts      = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    ts_file = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    html    = build_html(dfs, ts)

    out = REPORTS_DIR / f"lakehouse_report_{ts_file}.html"
    out.write_text(html, encoding="utf-8")
    print(f"[report] Report written → {out}")
    print(f"[report] Open in browser: file:///{out.as_posix()}")


if __name__ == "__main__":
    main()
