from dash import Dash, Input, Output, State, callback, ctx, dcc, html
from flask import jsonify, send_from_directory
from pathlib import Path

from data_loader import load_robot_log
from map_view import build_trajectory_map, update_trajectory_map
from replay import (build_viewer_payload, get_replay_history, prepare_replay_data,)
from mission_table import build_position_rows
from orientation_view import build_rotation_panels

from distances import build_distance_rows

import dash_ag_grid as dag
import time


# Find the project root from this script's new location.
project_dir = Path(__file__).resolve().parents[3]

data_dir = project_dir / "data"
pov_dir = project_dir / "src" / "trajectory-visualizer" / "pov-plot"

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
        value="third-person",
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
            html.Div(
                style={
                    "display": "flex", "flexDirection": "column",
                    "height": "calc(100dvh - 160px)", "minHeight": "520px",
                    "gap": "10px", "padding": "0 20px 16px",
                    "boxSizing": "border-box",
                },
                children=[
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
                    html.Div(
                        html.Button(
                            "Ocultar painel", id="toggle-mission-sidebar",
                            n_clicks=0,
                            style={"padding": "8px 14px", "cursor": "pointer"},
                            **{"aria-controls": "mission-sidebar", "aria-expanded": "true"},
                        ),
                        style={"textAlign": "right", "flexShrink": 0},
                    ),
                    # Five shares for the map; at most two for the sidebar.
                    html.Div(
                        id="mission-workspace",
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "minmax(0, 5fr) minmax(0, 2fr)",
                            "flex": "1 1 0", "minHeight": "220px", "minWidth": 0,
                        },
                        children=[
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
                            html.Aside(
                                id="mission-sidebar",
                                style={
                                    "minWidth": 0, "minHeight": 0,
                                    "overflow": "auto", "boxSizing": "border-box",
                                    "padding": "12px", "backgroundColor": "#f8fafc",
                                    "color": "#18253b", "borderLeft": "1px solid #e2e8f0",
                                },
                                children=[
                                    html.Label("Informação a apresentar", htmlFor="sidebar-section"),
                                    dcc.Dropdown(
                                        id="sidebar-section",
                                        options=[
                                            {"label": "Coordenadas", "value": "coordinates"},
                                            {"label": "Distâncias", "value": "distances"},
                                            {"label": "Matrizes de rotação", "value": "rotations"},
                                        ],
                                        value="coordinates", clearable=False, searchable=False,
                                        style={"margin": "8px 0 16px"},
                                    ),
                                    # Keep all outputs mounted so existing callbacks still work.
                                    html.Div(id="sidebar-coordinates", children=[
                                        html.H3("Coordenadas", style={"fontSize": "16px"}),
                                        html.P("Última posição conhecida. Idade = tempo selecionado − tempo da medição. Z mantém o valor do log.", style={"fontSize": "12px"}),
                                        html.Div(children=[
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
                                            )
                                        ], style={"overflowX": "auto", "minWidth": 0}),
                                    ]),
                                    html.Div(
                                        id="sidebar-distances",
                                        style={"display": "none"},
                                        children=[
                                            html.H3("Distâncias entre robôs", style={"fontSize": "16px"}),
                                            html.P(
                                                "Distâncias horizontais aproximadas, calculadas com as últimas "
                                                "posições conhecidas. Não incluem Z.",
                                                style={"fontSize": "12px", "color": "#64748b"},
                                            ),
                                            html.Div(id="mission-distance-panel"),
                                        ],
                                    ),
                                    html.Div(id="sidebar-rotations", style={"display": "none"}, children=[
                                        html.P(
                                            "Conversão dos quaterniões [x, y, z, w]. "
                                            "A direção entre referenciais está por confirmar.",
                                            style={
                                                "fontSize": "12px",
                                                "color": "#64748b",
                                                "margin": "0 0 10px",
                                            },
                                        ),
                                        html.Div(
                                            id="rotation-matrices",
                                            children=build_rotation_panels(
                                                get_replay_history(replay_logs, 0.0)
                                            ),
                                            style={
                                                "display": "grid",
                                                "gridTemplateColumns": (
                                                    "minmax(0, 1fr)"
                                                ),
                                                "gap": "12px",
                                            },
                                        ),
                                    ]),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    ),
]


def build_distance_panel(rows):
    """Display one compact card per robot pair."""
    cards = []
    for row in rows:
        if row["distance_m"] is None:
            value_text = "Sem dados para ambos os robôs"
            age_text = ""
        else:
            value_text = f"≈ {row['distance_m']:.1f} m"
            age_text = (
                "Idade das posições, pela ordem do par: "
                f"{row['first_age_s']:.1f} s / {row['second_age_s']:.1f} s"
            )
        cards.append(
            html.Div(
                children=[
                    html.Div(row["pair"], style={"fontWeight": "bold"}),
                    html.Div(value_text, style={
                        "fontSize": "20px", "margin": "8px 0",
                        "fontVariantNumeric": "tabular-nums",
                    }),
                    html.Div(age_text, style={"fontSize": "12px", "color": "#64748b"}),
                ],
                style={
                    "padding": "12px", "marginBottom": "10px",
                    "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0",
                    "borderRadius": "8px",
                },
            )
        )
    return cards


# Sidebar visibility and section selection.
@callback(
    Output("mission-workspace", "style"),
    Output("mission-sidebar", "style"),
    Output("toggle-mission-sidebar", "children"),
    Output("toggle-mission-sidebar", "aria-expanded"),
    Input("toggle-mission-sidebar", "n_clicks"),
)
def toggle_mission_sidebar(n_clicks):
    """Hide the sidebar and let the map use the full available width."""
    visible = (n_clicks or 0) % 2 == 0
    workspace_style = {
        "display": "grid",
        "gridTemplateColumns": (
            "minmax(0, 5fr) minmax(0, 2fr)" if visible else "minmax(0, 1fr)"
        ),
        "flex": "1 1 0", "minHeight": "220px", "minWidth": 0,
    }
    sidebar_style = {
        "display": "block" if visible else "none",
        "minWidth": 0, "minHeight": 0, "overflow": "auto",
        "boxSizing": "border-box", "padding": "12px",
        "backgroundColor": "#f8fafc", "color": "#18253b",
        "borderLeft": "1px solid #e2e8f0",
    }
    return (
        workspace_style, sidebar_style,
        "Ocultar painel" if visible else "Mostrar painel",
        "true" if visible else "false",
    )


@callback(
    Output("sidebar-coordinates", "style"),
    Output("sidebar-distances", "style"),
    Output("sidebar-rotations", "style"),
    Input("sidebar-section", "value"),
)
def select_sidebar_section(section):
    """Show one section without removing the other callback targets."""
    return tuple(
        {"display": "block" if section == name else "none"}
        for name in ("coordinates", "distances", "rotations")
    )


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
    Output("rotation-matrices", "children"),
    Output("mission-distance-panel", "children"),
    Input("mission-time-slider", "value"),
)
def update_mission_view(selected_time_s):
    """Update trajectories and all panels from the same mission instant."""
    history = get_replay_history(replay_logs, selected_time_s)

    # Update trajectories only; distances never modify map traces.
    figure_patch = update_trajectory_map(history, replay_logs)
    rotation_panels = build_rotation_panels(history)
    position_rows = build_position_rows(history, replay_logs, selected_time_s)

    # Round values only for table presentation.
    for row in position_rows:
        for field in ("latitude", "longitude"):
            if row[field] is not None:
                row[field] = round(row[field], 7)
        for field in ("position_z", "record_time_s", "age_s"):
            if row[field] is not None:
                row[field] = round(row[field], 2)

    # Calculate every unique pair whenever the mission time changes.
    distance_rows = build_distance_rows(history, selected_time_s)
    distance_panel = build_distance_panel(distance_rows)
    time_text = (
        f"Mission time: {selected_time_s:.1f} s"
        f" / {mission_duration_s:.1f} s"
    )
    return time_text, figure_patch, position_rows, rotation_panels, distance_panel

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
