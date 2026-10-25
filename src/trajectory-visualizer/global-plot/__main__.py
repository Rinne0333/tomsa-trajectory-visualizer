from dash import Dash, Input, Output, State, callback, ctx, dcc, html
from flask import jsonify, send_from_directory
from pathlib import Path

from data_loader import load_robot_log
from map_view import build_trajectory_map, update_trajectory_map, ROBOT_COLORS
from replay import (build_viewer_payload, get_replay_history, prepare_replay_data,)
from mission_table import build_position_rows
from orientation_view import build_rotation_panels as original_rotation_panels

from distances import build_distance_rows

import time
import numpy as np


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

# Shared styles keep every sidebar card consistent.
BUTTON_STYLE = {
    "padding": "8px 12px", "border": "1px solid #dbe3ee",
    "borderRadius": "8px", "backgroundColor": "#ffffff",
    "color": "#334155", "cursor": "pointer", "fontWeight": "600",
    "fontSize": "13px", "whiteSpace": "nowrap",
}


def format_mission_time(seconds):
    """Format mission duration without wrapping after 24 hours."""
    total = max(0, int(float(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def robot_label(name):
    """Reuse the map color without relying on color alone."""
    return html.Span([
        html.Span(style={
            "display": "inline-block", "width": "8px", "height": "8px",
            "borderRadius": "50%", "backgroundColor": ROBOT_COLORS.get(name, "#64748b"),
            "marginRight": "7px",
        }),
        name,
    ], style={"fontWeight": "600", "fontSize": "13px"})


def polish_cards(cards, names=None):
    """Apply one visual style to coordinate, velocity and rotation cards."""
    for index, card in enumerate(cards):
        name = names[index] if names else None
        card.style = {
            **(card.style or {}), "padding": "14px", "marginBottom": "10px",
            "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0",
            "borderRadius": "12px", "boxShadow": "0 2px 6px rgba(15,23,42,0.03)",
            "fontVariantNumeric": "tabular-nums", "minWidth": 0,
        }
        if name:
            card.style["borderLeft"] = f"3px solid {ROBOT_COLORS.get(name, '#64748b')}"
            card.children[0] = robot_label(name)
    return cards


def build_rotation_panels(history):
    """Keep rotation calculations in the existing module."""
    return polish_cards(original_rotation_panels(history), list(history))


def mission_camera(logs):
    """Estimate a padded overview for this geographically compact mission."""
    latitudes = np.concatenate([d["pose.pose.position.x"].to_numpy() for d in logs.values()])
    longitudes = np.concatenate([d["pose.pose.position.y"].to_numpy() for d in logs.values()])
    south, north = float(latitudes.min()), float(latitudes.max())
    west, east = float(longitudes.min()), float(longitudes.max())
    # Measure extent in normalized Web Mercator coordinates.
    phi = np.radians(np.clip([south, north], -85.0, 85.0))
    y = (1 - np.log(np.tan(np.pi / 4 + phi / 2)) / np.pi) / 2
    span = max((east - west) / 360, float(abs(y[1] - y[0])), 1e-8)
    # Conservative viewport allowance; exact fit depends on screen size.
    zoom = float(np.clip(np.log2(220 / (512 * span)) - 0.35, 0, 18))
    middle_y = float(y.mean())
    center_lat = float(np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * middle_y)))))
    return {"lat": center_lat, "lon": (west + east) / 2}, zoom


MISSION_CENTER, MISSION_ZOOM = mission_camera(replay_logs)


def build_initial_map(history, logs):
    """Set the visual style once; normal replay updates keep the camera."""
    figure = build_trajectory_map(history, logs)
    for trace in figure.data:
        if str(trace.uid).endswith("-past"):
            trace.opacity = 0.18
        elif str(trace.uid).endswith("-current"):
            trace.marker.size = 13
    figure.update_layout(
        map_center=MISSION_CENTER, map_zoom=MISSION_ZOOM,
        font={"family": "Arial, sans-serif", "color": "#334155"},
        legend={
            "orientation": "h", "x": 0.01, "y": 0.99,
            "xanchor": "left", "yanchor": "top",
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#e2e8f0", "borderwidth": 1,
            "font": {"size": 11},
        },
    )
    return figure


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
                    "height": "calc(100dvh - 140px)", "minHeight": "520px",
                    "gap": "10px", "padding": "0 20px 16px",
                    "fontFamily": "system-ui, -apple-system, sans-serif",
                    "fontVariantNumeric": "tabular-nums",
                    "boxSizing": "border-box",
                },
                children=[
                    html.Div(
                        style={
                            "flexShrink": 0, "padding": "12px 16px 8px",
                            "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0",
                            "borderRadius": "12px", "color": "#18253b",
                        },
                        children=[
                            html.Div(style={
                                "display": "flex", "alignItems": "center", "gap": "10px",
                                "flexWrap": "wrap", "marginBottom": "12px",
                            }, children=[
                                html.Button("▶ Reproduzir", id="replay-play-button", n_clicks=0,
                                    style={**BUTTON_STYLE, "backgroundColor": "#0f172a", "color": "white", "minWidth": "120px"}),
                                dcc.Dropdown(
                                    id="replay-speed",
                                    options=[{"label": f"{v}×", "value": v} for v in (1, 5, 10, 25, 50, 100)],
                                    value=1, clearable=False, searchable=False,
                                    style={"width": "88px", "fontSize": "13px"},
                                ),
                                html.Div(id="mission-time-display", style={
                                    "fontSize": "15px", "fontWeight": "600", "fontVariantNumeric": "tabular-nums",
                                    "flex": "1 1 180px", "textAlign": "center",
                                }),
                                html.Button("Enquadrar missão", id="fit-mission-map", n_clicks=0, style=BUTTON_STYLE),
                                html.Button("Ocultar painel", id="toggle-mission-sidebar", n_clicks=0,
                                    style=BUTTON_STYLE, **{"aria-controls": "mission-sidebar", "aria-expanded": "true"}),
                            ]),
                            dcc.Interval(id="replay-timer", interval=250, n_intervals=0, disabled=True),
                            dcc.Store(id="replay-state", data={"playing": False, "last_tick": None, "speed": 1}),
                            dcc.Slider(
                                id="mission-time-slider", min=0, max=mission_duration_s, step=0.1, value=0,
                                marks={0: "Início", mission_duration_s: "Fim"}, updatemode="drag",
                            ),
                        ],
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
                                        figure=build_initial_map(
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
                                    "padding": "14px", "backgroundColor": "#f8fafc",
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
                                            {"label": "Velocidades", "value": "velocities"},
                                        ],
                                        value="coordinates", clearable=False, searchable=False,
                                        style={"margin": "8px 0 16px"},
                                    ),
                                    # Keep all outputs mounted so existing callbacks still work.
                                    html.Div(
                                        id="sidebar-coordinates",
                                        children=[
                                            html.Label("Robô a consultar", htmlFor="coordinate-robot-selector"),
                                            dcc.Dropdown(
                                                id="coordinate-robot-selector",
                                                options=[
                                                    {"label": name, "value": name} for name in replay_logs
                                                ] + [{"label": "Todos os robôs", "value": "all"}],
                                                value=next(iter(replay_logs)),
                                                clearable=False,
                                                searchable=False,
                                                style={"margin": "8px 0 12px"},
                                            ),
                                            html.Div(id="mission-coordinate-panel"),
                                        ],
                                    ),
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
                                    html.Div(
                                        id="sidebar-velocities",
                                        style={"display": "none"},
                                        children=[
                                            html.Label("Robô a consultar", htmlFor="velocity-robot-selector"),
                                            dcc.Dropdown(
                                                id="velocity-robot-selector",
                                                options=[{"label": name, "value": name} for name in replay_logs]
                                                + [{"label": "Todos os robôs", "value": "all"}],
                                                value=next(iter(replay_logs)),
                                                clearable=False,
                                                searchable=False,
                                                style={"margin": "8px 0 12px"},
                                            ),
                                            html.P(
                                                "Velocidades do log, expressas no referencial indicado. "
                                                "Unidades apresentadas segundo a convenção ROS: m/s e rad/s.",
                                                style={"fontSize": "12px", "color": "#64748b"},
                                            ),
                                            html.Div(id="mission-velocity-panel"),
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
                    html.Div([robot_label(name.strip()) for name in row["pair"].split("↔")], style={"display": "flex", "gap": "10px", "flexWrap": "wrap"}),
                    html.Div(value_text, style={
                        "fontSize": "26px", "fontWeight": "600", "margin": "10px 0",
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
    return polish_cards(cards)


def build_coordinate_panel(rows):
    """Display position and measurement details as compact robot cards."""
    cards = []
    for row in rows:
        def format_value(value, decimals, unit):
            return "—" if value is None else f"{value:.{decimals}f} {unit}"

        # Z is displayed without assuming its vertical reference or units.
        fields = [
            ("Latitude", format_value(row["latitude"], 7, "°")),
            ("Longitude", format_value(row["longitude"], 7, "°")),
            ("Z do log", format_value(row["position_z"], 2, "")),
            ("Instante da medição", format_value(row["record_time_s"], 1, "s")),
            ("Idade da medição", format_value(row["age_s"], 1, "s")),
        ]
        entries = []
        for label, value in fields:
            entries.extend([
                html.Dt(label, style={"color": "#64748b", "fontSize": "12px"}),
                html.Dd(value, style={
                    "margin": "2px 0 10px", "fontWeight": "600",
                    "fontVariantNumeric": "tabular-nums", "overflowWrap": "anywhere",
                }),
            ])
        # State describes record availability, independently of Play/Pause.
        status = {
            "A aguardar": "A aguardar",
            "Em reprodução": "Dados disponíveis",
            "Log terminado": "Log terminado",
        }.get(row["status"], row["status"])
        cards.append(html.Div(
            children=[
                html.Div(row["robot"], style={"fontWeight": "bold", "fontSize": "16px"}),
                html.Div(status, style={"fontSize": "12px", "color": "#64748b", "margin": "4px 0 12px"}),
                html.Dl(entries, style={"margin": 0}),
                html.P(
                    "Profundidade por confirmar: falta conhecer o significado, "
                    "a unidade e o zero de Z. Idade = tempo selecionado − tempo da medição.",
                    style={"fontSize": "11px", "color": "#64748b", "margin": "0"},
                ),
            ],
            style={
                "padding": "12px", "marginBottom": "10px",
                "backgroundColor": "#ffffff", "border": "1px solid #e2e8f0",
                "borderRadius": "8px",
            },
        ))
    return polish_cards(cards, [row["robot"] for row in rows])


@callback(
    Output("mission-coordinate-panel", "children"),
    Input("mission-time-slider", "value"),
    Input("coordinate-robot-selector", "value"),
)
def update_coordinate_panel(selected_time_s, selected_robot):
    """Update coordinates without refreshing the map when selecting a robot."""
    history = get_replay_history(replay_logs, selected_time_s)
    rows = build_position_rows(history, replay_logs, selected_time_s)
    if selected_robot != "all":
        rows = [row for row in rows if row["robot"] == selected_robot]
    return build_coordinate_panel(rows)


def build_velocity_panel(robot_history, prepared_logs, selected_time_s):
    """Display the latest logged velocities without changing replay speed."""
    cards = []
    for name, history in robot_history.items():
        content = [html.Div(name, style={"fontWeight": "bold", "fontSize": "16px"})]
        if history.empty:
            content.append(html.P("Sem registos neste instante."))
        else:
            current = history.iloc[-1]
            record_time_s = float(current["mission_time_s"])
            age_s = max(0.0, selected_time_s - record_time_s)
            log_ended = selected_time_s > float(prepared_logs[name]["mission_time_s"].iloc[-1])

            # Read the components in the robot's reported velocity frame.
            linear = np.array([
                current[f"twist.twist.linear.{axis}"] for axis in ("x", "y", "z")
            ], dtype=float)
            angular = np.array([
                current[f"twist.twist.angular.{axis}"] for axis in ("x", "y", "z")
            ], dtype=float)

            # The vector norm gives speed regardless of direction.
            speed_m_s = float(np.linalg.norm(linear))
            content.extend([
                html.Div(
                    "Última medição — log terminado" if log_ended else "Última medição disponível",
                    style={"fontSize": "12px", "color": "#64748b", "marginTop": "4px"},
                ),
                html.Div("Velocidade total", style={"fontSize": "12px", "marginTop": "12px"}),
                html.Div(f"{speed_m_s:.3f} m/s", style={
                    "fontSize": "24px", "fontWeight": "bold",
                    "fontVariantNumeric": "tabular-nums", "marginBottom": "12px",
                }),
            ])
            for title, vector, unit in [
                ("Velocidade linear", linear, "m/s"),
                ("Velocidade angular", angular, "rad/s"),
            ]:
                entries = []
                for axis, value in zip(("X", "Y", "Z"), vector):
                    entries.extend([
                        html.Dt(axis, style={"color": "#64748b"}),
                        html.Dd(f"{float(value):.4f} {unit}", style={
                            "margin": 0, "textAlign": "right",
                            "fontVariantNumeric": "tabular-nums", "overflowWrap": "anywhere",
                        }),
                    ])
                content.extend([
                    html.Div(title, style={"fontWeight": "600", "fontSize": "13px", "marginBottom": "6px"}),
                    html.Dl(entries, style={
                        "display": "grid", "gridTemplateColumns": "auto minmax(0, 1fr)",
                        "gap": "6px 12px", "margin": "0 0 14px", "fontSize": "13px",
                    }),
                ])
            content.append(html.Div([
                html.Div(f"Referencial: {current['child_frame_id']}"),
                html.Div(f"Medição: {record_time_s:.1f} s de missão"),
                html.Div(f"Idade da medição: {age_s:.1f} s"),
            ], style={"fontSize": "12px", "color": "#64748b", "lineHeight": "1.6"}))
        cards.append(html.Div(content, style={
            "padding": "12px", "marginBottom": "10px", "backgroundColor": "#ffffff",
            "border": "1px solid #e2e8f0", "borderRadius": "8px",
        }))
    return polish_cards(cards, list(robot_history))


@callback(
    Output("mission-velocity-panel", "children"),
    Input("mission-time-slider", "value"),
    Input("velocity-robot-selector", "value"),
)
def update_velocity_panel(selected_time_s, selected_robot):
    """Refresh velocity cards independently of the map."""
    history = get_replay_history(replay_logs, selected_time_s)
    if selected_robot != "all":
        history = {selected_robot: history[selected_robot]}
    return build_velocity_panel(history, replay_logs, selected_time_s)


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
        "boxSizing": "border-box", "padding": "14px",
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
    Output("sidebar-velocities", "style"),
    Input("sidebar-section", "value"),
)
def select_sidebar_section(section):
    """Show one section without removing the other callback targets."""
    return tuple(
        {"display": "block" if section == name else "none"}
        for name in ("coordinates", "distances", "rotations", "velocities")
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
    Output("rotation-matrices", "children"),
    Output("mission-distance-panel", "children"),
    Input("mission-time-slider", "value"),
    Input("fit-mission-map", "n_clicks"),
)
def update_mission_view(selected_time_s, fit_clicks):
    """Update trajectories and all panels from the same mission instant."""
    history = get_replay_history(replay_logs, selected_time_s)

    # A button click rebuilds the view once; replay keeps lightweight patches.
    if "fit-mission-map.n_clicks" in ctx.triggered_prop_ids:
        figure_patch = build_initial_map(history, replay_logs)
        revision = f"overview-{fit_clicks}"
        figure_patch.update_layout(
            uirevision=revision,
            map_uirevision=revision,
            map_center=dict(MISSION_CENTER),
            map_zoom=MISSION_ZOOM,
            map_bearing=0,
            map_pitch=0,
        )
    else:
        figure_patch = update_trajectory_map(history, replay_logs)
    rotation_panels = build_rotation_panels(history)

    # Calculate every unique pair whenever the mission time changes.
    distance_rows = build_distance_rows(history, selected_time_s)
    distance_panel = build_distance_panel(distance_rows)
    time_text = (
        f"{format_mission_time(selected_time_s)}"
        f" / {format_mission_time(mission_duration_s)}"
    )
    return time_text, figure_patch, rotation_panels, distance_panel

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
        "Ⅱ Pausar" if playing else "▶ Reproduzir",
        new_state,
    )


if __name__ == '__main__':
    app.run(debug=True)
