from dash import Dash, Input, Output, State, callback, ctx, dcc, html
from flask import jsonify, send_from_directory
from pathlib import Path

from data_loader import load_robot_log
from replay import build_viewer_payload, prepare_replay_data
from map_view import build_trajectory_map, update_trajectory_map
from replay import (build_viewer_payload, get_replay_history, prepare_replay_data,)
from mission_table import build_position_rows
import dash_ag_grid as dag


import dash_ag_grid as dag
import pandas as pd
import plotly.express as px
import time


project_dir = Path(__file__).resolve().parents[2]
pov_dir = project_dir / "src/trajectory-visualizer/pov-plot"
data_dir = project_dir / "data"

rd1 = load_robot_log(data_dir / "robot1_s1.csv")
rd4 = load_robot_log(data_dir / "robot4_s1.csv")
rd7 = load_robot_log(data_dir / "robot7_s1.csv")

# Replay Logs ordered and prepared for replay
replay_logs = prepare_replay_data(
    {
        "Robot 1": rd1,
        "Robot 4": rd4,
        "Robot 7": rd7
    }
)

viewer_payload = build_viewer_payload(replay_logs)

mission_duration_s = float(
    max(
        data["mission_time_s"].max()
        for data in replay_logs.values()
    )
)

app = Dash(
    assets_folder=str(project_dir / 'src/trajectory-visualizer/pov-plot'),
    assets_ignore=r'third_person\.(js|css)',
)
app.layout = [
    html.Div(children='Trajectory Visualizer', style={'textAlign': 'center', 'fontSize': 30}),
    html.Hr(),
        dcc.Dropdown(
            id="view-selector",
            options=[
                {"label": "Visão Local", "value": "third-person"},
                {"label": "Visão Global", "value": "mapa"},
            ],
            value="third-person-view",
            clearable=False,
            style={"width": "220px", "margin": "12px 24px", "color": "black"},
        ),
    html.Div(
        id="third-person-view",
        children=[
            html.H2("Visão Local", style={"margin": "20px 24px 8px"}),
            html.Iframe(
                src="/third-person",
                title="Three-dimensional robot replay",
                style={
                    "height": "720px",
                    "width": "calc(100% - 48px)",
                    "margin": "0 24px 24px",
                    "border": "0",
                    "display": "block",
                },
            ),
        ],
    ),
    html.Div(
        id="map-view",
        style={"display": "none"},
        children=[
            # Arrange controls, table and map vertically.
            html.Div(
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "height": "calc(100dvh - 160px)",
                    "minHeight": "520px",
                    "gap": "12px",
                    "padding": "0 20px 16px",
                    "boxSizing": "border-box",
                },
                children=[
                    # Mission time and playback controls.
                    html.Div(
                        style={
                            "flexShrink": 0,
                            "padding": "12px 16px",
                            "backgroundColor": "#f4f6f8",
                            "borderRadius": "10px",
                            "color": "#18253b",
                        },
                        children=[
                            html.Div(
                                id="mission-time-display",
                                style={
                                    "textAlign": "center",
                                    "fontSize": "20px",
                                    "fontWeight": "bold",
                                    "fontVariantNumeric": "tabular-nums",
                                    "marginBottom": "10px",
                                },
                            ),

                            html.Div(
                                style={
                                    "display": "flex",
                                    "justifyContent": "center",
                                    "alignItems": "center",
                                    "gap": "12px",
                                    "marginBottom": "12px",
                                },
                                children=[
                                    html.Button(
                                        "Play",
                                        id="replay-play-button",
                                        n_clicks=0,
                                        style={
                                            "padding": "8px 20px",
                                            "cursor": "pointer",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="replay-speed",
                                        options=[
                                            {"label": "1×", "value": 1},
                                            {"label": "5×", "value": 5},
                                            {"label": "10×", "value": 10},
                                            {"label": "25×", "value": 25},
                                            {"label": "50×", "value": 50},
                                            {"label": "100×", "value": 100},
                                        ],
                                        value=1,
                                        clearable=False,
                                        searchable=False,
                                        style={
                                            "width": "100px",
                                            "color": "black",
                                        },
                                    ),
                                ],
                            ),

                            dcc.Interval(
                                id="replay-timer",
                                interval=250,
                                n_intervals=0,
                                disabled=True,
                            ),

                            dcc.Store(
                                id="replay-state",
                                data={
                                    "playing": False,
                                    "last_tick": None,
                                    "speed": 1,
                                },
                            ),

                            dcc.Slider(
                                id="mission-time-slider",
                                min=0,
                                max=mission_duration_s,
                                step=0.1,
                                value=0,
                                marks={
                                    0: "Início",
                                    mission_duration_s: "Fim",
                                },
                                updatemode="drag",
                            ),
                        ],
                    ),

                    # Keep the coordinate table above the map.
                    html.Div(
                        style={
                            "flexShrink": 0,
                            "backgroundColor": "#ffffff",
                            "color": "#18253b",
                            "border": "1px solid #e2e8f0",
                            "borderRadius": "10px",
                            "padding": "10px 12px",
                        },
                        children=[
                            html.H3(
                                "Coordenadas no instante selecionado",
                                style={
                                    "margin": "0 0 6px",
                                    "fontSize": "16px",
                                },
                            ),

                            html.P(
                                "Última posição conhecida. "
                                "Idade = tempo selecionado − tempo da medição. "
                                "Z mantém o valor original do log.",
                                style={
                                    "margin": "0 0 8px",
                                    "fontSize": "12px",
                                    "color": "#64748b",
                                },
                            ),

                            # Scroll the table instead of expanding the panel.
                            html.Div(
                                style={
                                    "maxHeight": "160px",
                                    "overflowY": "auto",
                                },
                                children=[
                                    dag.AgGrid(
                                        id="mission-position-table",
                                        columnDefs=[
                                            {
                                                "headerName": "Robô",
                                                "field": "robot",
                                            },
                                            {
                                                "headerName": "Estado",
                                                "field": "status",
                                            },
                                            {
                                                "headerName": "Latitude (°)",
                                                "field": "latitude",
                                            },
                                            {
                                                "headerName": "Longitude (°)",
                                                "field": "longitude",
                                            },
                                            {
                                                "headerName": "Z — valor do log",
                                                "field": "position_z",
                                            },
                                            {
                                                "headerName": "Medição (s)",
                                                "field": "record_time_s",
                                            },
                                            {
                                                "headerName": "Idade (s)",
                                                "field": "age_s",
                                            },
                                        ],
                                        rowData=[],
                                        defaultColDef={
                                            "resizable": True,
                                            "sortable": False,
                                            "flex": 1,
                                            "minWidth": 130,
                                        },
                                        dashGridOptions={
                                            "domLayout": "autoHeight",
                                            "rowHeight": 32,
                                            "headerHeight": 34,
                                            "animateRows": False,
                                        },
                                        style={"width": "100%"},
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # Let the map fill the remaining vertical space.
                    html.Div(
                        style={
                            "flex": "1 1 0",
                            "minHeight": "220px",
                            "minWidth": 0,
                            "position": "relative",
                            "borderRadius": "10px",
                            "overflow": "hidden",
                        },
                        children=[
                            dcc.Graph(
                                id="mission-map",
                                figure=build_trajectory_map(
                                    get_replay_history(replay_logs, 0.0),
                                    replay_logs,
                                ),
                                responsive=True,
                                style={
                                    "position": "absolute",
                                    "inset": 0,
                                    "height": "100%",
                                    "width": "100%",
                                },
                                config={
                                    "responsive": True,
                                    "scrollZoom": True,
                                    "displaylogo": False,
                                },
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
    # dcc.Graph(
    #     figure=fig,
    #     style={'height': '85vh', 'width': '100%'},
    #     config={'responsive': True},
    # ),
    # dcc.RadioItems(options=['Robot 1', 'Robot 4', 'Robot 7'], value='Robot 1', id='viewTable', inline=True),
    # dag.AgGrid(id='sendTable', rowData=[], columnDefs=[], dashGridOptions={'suppressFieldDotNotation': True})
]


@app.server.get('/api/robot-trajectories')
def robot_trajectories():
    return jsonify(viewer_payload)


@app.server.get('/third-person')
def third_person_view():
    return send_from_directory(pov_dir, 'third_person.html')


@app.server.get('/pov-assets/<path:filename>')
def pov_asset_file(filename):
    return send_from_directory(pov_dir, filename)


@app.server.get('/robot-model/<path:filename>')
def robot_model_file(filename):
    return send_from_directory(data_dir / 'AUV model', filename)


# @callback(
#     Output('sendTable', 'rowData'),
#     Output('sendTable', 'columnDefs'),
#     Input('viewTable', 'value'),
# )
def update_table(robot):
    data = {
        'Robot 1': rd1,
        'Robot 4': rd4,
        'Robot 7': rd7,
    }[robot]

    return (
        data.to_dict('records'),
        [{'field': column} for column in data.columns],
    )

@callback(
    Output("mission-time-display", "children"),
    Output("mission-map", "figure"),
    Output("mission-position-table", "rowData"),
    Input("mission-time-slider", "value"),
)
def update_mission_view(selected_time_s):
    """Update the time, map and coordinate table together."""

    # Select the records available at the chosen time.
    history = get_replay_history(
        replay_logs,
        selected_time_s,
    )

    # Update only the changing map data.
    figure_patch = update_trajectory_map(
        history,
        replay_logs,
    )

    # Prepare the latest position of each robot.
    position_rows = build_position_rows(
        history,
        replay_logs,
        selected_time_s,
    )

    # Round values only for table presentation.
    for row in position_rows:
        for field in ("latitude", "longitude"):
            if row[field] is not None:
                row[field] = round(row[field], 7)

        for field in ("position_z", "record_time_s", "age_s"):
            if row[field] is not None:
                row[field] = round(row[field], 2)

    time_text = (
        f"Mission time: {selected_time_s:.1f} s"
        f" / {mission_duration_s:.1f} s"
    )

    # Match the order of the three Outputs.
    return time_text, figure_patch, position_rows


@callback(
    Output("third-person-view", "style"),
    Output("map-view", "style"),
    Input("view-selector", "value"),
)
def select_view(view):
    if view == "mapa":
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}


@callback(
    Output("mission-time-slider", "value"),
    Output("replay-timer", "disabled"),
    Output("replay-play-button", "children"),
    Output("replay-state", "data"),
    Input("replay-play-button", "n_clicks"),
    Input("replay-timer", "n_intervals"),
    Input("replay-speed", "value"),
    State("mission-time-slider", "value"),
    State("replay-state", "data"),
    prevent_initial_call=True,
)
def control_replay(
    n_clicks,
    n_intervals,
    selected_speed,
    selected_time_s,
    playback_state,
):
    """Control playback and advance the mission slider."""

    # Read the current playback state.
    playing = playback_state["playing"]
    previous_speed = playback_state["speed"]
    last_tick = playback_state["last_tick"]
    current_time_s = float(selected_time_s)

    # Use a clock that is not affected by system clock adjustments.
    now = time.monotonic()

    # Advance using the actual elapsed time and the previous speed.
    if playing and last_tick is not None:
        elapsed_s = max(0.0, now - last_tick)
        current_time_s += elapsed_s * previous_speed

    # Toggle playback when the button is pressed.
    if ctx.triggered_id == "replay-play-button":
        if playing:
            playing = False
        else:
            # Restart from the beginning if playback has already ended.
            if current_time_s >= mission_duration_s:
                current_time_s = 0.0

            playing = True

    # Stop automatically at the end of the mission.
    if current_time_s >= mission_duration_s:
        current_time_s = mission_duration_s
        playing = False

    # Save the state for the next update.
    new_state = {
        "playing": playing,
        "last_tick": now,
        "speed": selected_speed,
    }

    # Return values in the same order as the Outputs.
    return (
        current_time_s,
        not playing,
        "Pause" if playing else "Play",
        new_state,
    )

if __name__ == '__main__':
    app.run(debug=True)