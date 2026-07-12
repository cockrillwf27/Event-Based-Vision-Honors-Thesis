from nicegui import ui
import random
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from collections import deque
import asyncio
import json
from decision_brain import current_decisions, run_decision_brain

# ====================== LOAD CONFIG FROM JSON ======================
with open("panel_config.json", "r") as f:
    config = json.load(f)

# Build GAUGES from the JSON (super easy to customize later)
GAUGES = {}
for panel_name, panel_data in config["panels"].items():
    for gauge_name, props in panel_data["gauges"].items():
        GAUGES[gauge_name] = props

history = {name: deque(maxlen=300) for name in GAUGES}
current_values = {name: (GAUGES[name]["min"] + GAUGES[name]["max"]) / 2 for name in GAUGES}

# ====================== UI ======================
ui.html("""<style>.control-panel { background: linear-gradient(#1f2937, #111827); border: 8px solid #64748b; box-shadow: 0 0 30px rgba(0,0,0,0.8); }</style>""")

with ui.card().classes("control-panel w-full max-w-7xl mx-auto my-8 p-8"):
    ui.label("🔧 LUCID TRITON 2 CONTROL PANEL").classes("text-5xl font-bold text-center text-white tracking-widest mb-2")
    ui.label("REAL-TIME INDUSTRIAL MONITORING").classes("text-center text-slate-400 text-xl mb-8")

    with ui.grid(columns=4).classes("gap-8 w-full"):
        gauge_widgets = {}
        for name, cfg in GAUGES.items():
            with ui.card().tight().classes("bg-zinc-900 border border-slate-600 hover:border-amber-400 cursor-pointer"):
                ui.label(name).classes("text-xl font-bold text-center text-white pt-4")
                fig = go.Figure(go.Indicator(mode="gauge+number", value=current_values[name],
                    gauge={"axis": {"range": [cfg["min"], cfg["max"]]}, "bar": {"color": cfg["color"]},
                           "steps": [{"range": [cfg["min"], cfg["alert_threshold"]*0.9], "color": "#22c55e"},
                                     {"range": [cfg["alert_threshold"]*0.9, cfg["alert_threshold"]], "color": "#eab308"},
                                     {"range": [cfg["alert_threshold"], cfg["max"]], "color": "#ef4444"}]}))
                fig.update_layout(height=220, margin=dict(l=20,r=20,t=30,b=20), paper_bgcolor="#18181b")
                gauge_plot = ui.plotly(fig).classes("w-full")
                gauge_widgets[name] = gauge_plot
                ui.label(cfg["unit"]).classes("text-center text-slate-400 text-sm pb-4")

                async def show_details(g=name):
                    ui.notify(f"📊 Opening {g} details", type="info")
                    with ui.dialog().props("persistent") as dialog, ui.card().classes("w-[900px]"):
                        ui.label(f"{g} – Live Details").classes("text-3xl font-bold p-6")
                        df = pd.DataFrame(list(history[g]), columns=["time", "value"])
                        fig_trend = go.Figure(go.Scatter(x=df["time"], y=df["value"], mode="lines+markers", line=dict(color=GAUGES[g]["color"])))
                        fig_trend.update_layout(height=420, title="Last 5 minutes trend")
                        ui.plotly(fig_trend).classes("w-full")
                        ui.button("Close", on_click=dialog.close).classes("mx-auto mt-6")
                    await dialog.open()
                gauge_plot.on("click", lambda _, g=name: asyncio.create_task(show_details(g)))

    # AI Decision Brain panel
    with ui.card().classes("mt-8 p-6 bg-zinc-900 border border-amber-400"):
        ui.label("🤖 AI DECISION BRAIN").classes("text-3xl font-bold text-amber-400 text-center mb-4")
        status_label = ui.label().classes("text-4xl font-bold text-center")
        recommendation_label = ui.label().classes("text-xl text-center mt-2")

async def update_panel():
    while True:
        for name, cfg in GAUGES.items():
            current_values[name] = max(cfg["min"], min(cfg["max"], current_values[name] + random.uniform(-0.7, 0.7)))
            fig = go.Figure(go.Indicator(mode="gauge+number", value=current_values[name],
                gauge={"axis": {"range": [cfg["min"], cfg["max"]]}, "bar": {"color": cfg["color"]},
                       "steps": [{"range": [cfg["min"], cfg["alert_threshold"]*0.9], "color": "#22c55e"},
                                 {"range": [cfg["alert_threshold"]*0.9, cfg["alert_threshold"]], "color": "#eab308"},
                                 {"range": [cfg["alert_threshold"], cfg["max"]], "color": "#ef4444"}]}))
            fig.update_layout(height=220, margin=dict(l=20,r=20,t=30,b=20), paper_bgcolor="#18181b")
            gauge_widgets[name].figure = fig

            timestamp = datetime.now().strftime("%H:%M:%S")
            history[name].append((timestamp, current_values[name]))

        run_decision_brain(current_values)

        status_label.text = f"STATUS: {current_decisions['overall_status']}"
        recommendation_label.text = current_decisions["recommendation"]

        await asyncio.sleep(1.0)

ui.timer(1.0, lambda: asyncio.create_task(update_panel()))
ui.run(title="LUCID TRITON 2 Control Panel", port=8080, reload=False, dark=True)