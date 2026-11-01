# Create the app, interface components and interactive callbacks
from dash import Dash, Input, Output, State, callback, ctx, dcc, html
from flask import jsonify, send_from_directory

# FIle and folder paths
from pathlib import Path

# Load and validate robot CSV files
from global_plot.data_loader import load_robot_log

# Build the map and update it's drawing data
from global_plot.map_view import (
    build_trajectory_map,
    update_trajectory_map,
    ROBOT_COLORS,
)

from global_plot.replay import (
    build_viewer_payload,
    get_replay_history,
    prepare_replay_data,
)
# Prepare coordinate summaries
from global_plot.mission_table import build_position_rows

# Calculate distances between robot pairs
from global_plot.distances import build_distance_rows

# Import the rotation cards
from global_plot.orientation_view import (
    build_rotation_panels as original_rotation_panels,
)
# Measure elapsed time during automatic playback
import time

# Perform vector and coordinate calculations
import numpy as np


# Find the project root 
project_dir = Path(__file__).resolve().parents[2]

# Locate the robot CSV files
data_dir = project_dir / "data"

# Locate the local view assets
pov_dir = project_dir / "src" / "trajectory-visualizer" / "pov-plot"

# Load and validate each robot's CSV file
rd1 = load_robot_log(data_dir / "robot1_s1.csv")
rd4 = load_robot_log(data_dir / "robot4_s1.csv")
rd7 = load_robot_log(data_dir / "robot7_s1.csv")

# Sort the logs and calulate mission time from a shared origin
replay_logs = prepare_replay_data(
    {
        "Robot 1": rd1,
        "Robot 4": rd4,
        "Robot 7": rd7
    }
)

viewer_payload = build_viewer_payload(replay_logs)

# Use the latest timestamp across all robots to define the mission duration
mission_duration_s = float(
    max(
        data["mission_time_s"].max()
        for data in replay_logs.values()
    )
)

# Shared Appearance for interface buttons
BUTTON_STYLE = {
    "padding": "8px 12px", 
    "border": "1px solid #dbe3ee",
    "borderRadius": "8px", 
    "backgroundColor": "#ffffff",
    "color": "#334155", 
    "cursor": "pointer", 
    "fontWeight": "600",
    "fontSize": "13px", 
    "whiteSpace": "nowrap",
}

# Format mission seconds as HH:MM:SS
def format_mission_time(seconds):
    """Format mission duration without wrapping after 24 hours."""

    # Discard fractional seconds
    total = max(0, int(float(seconds)))

    # Split the total seconds into hours and remaining seconds
    hours, remainder = divmod(total, 3600)

    # Split the remainder into minutes and seconds
    minutes, seconds = divmod(remainder, 60)

    # Display each component with two digits
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# Create a Robot label with it's name and map color
def robot_label(name):
    """Reuse the map color without relying on color alone."""

    return html.Span(
        [
            # Draw small colored circle before the name
            html.Span(
                style={
                    "display": "inline-block", 
                    "width": "8px", 
                    "height": "8px",
                    "borderRadius": "50%", 
                    "backgroundColor": ROBOT_COLORS.get(name, "#64748b"),
                    "marginRight": "7px",
                }
            ),

            #Display the robot's name next to the colored circle
            name,
        ], 
        style={
            "fontWeight": "600", 
            "fontSize": "13px"},
        )


def polish_cards(cards, names=None):
    """Apply one visual style to coordinate, velocity and rotation cards."""

    # Process each card and it's position in the list
    for index, card in enumerate(cards):

        # Get matching robot names if provided, otherwise None
        name = names[index] if names else None

        # Preserve existing styles and apply shared card application styles
        card.style = {
            **(card.style or {}), 
            "padding": "14px", 
            "marginBottom": "10px",
            "backgroundColor": "#ffffff", 
            "border": "1px solid #e2e8f0",
            "borderRadius": "12px", 
            "boxShadow": "0 2px 6px rgba(15,23,42,0.03)",
            "fontVariantNumeric": "tabular-nums", 
            "minWidth": 0,
        }
        if name:
            # Add a left border using the robot's map color
            card.style["borderLeft"] = f"3px solid {ROBOT_COLORS.get(name, '#64748b')}"

            # Replace the first child with a colored label
            card.children[0] = robot_label(name)

    # Return the card with their appearance updated
    return cards

# Build rotation cards and apply the shared appearance
def build_rotation_panels(history):
    """Keep rotation calculations in the existing module."""
    return polish_cards(original_rotation_panels(history), list(history))

# Calculate the camera position and zoom to fit the mission's geographic extent
def mission_camera(logs):
    """Estimate a padded overview for this geographically compact mission."""

    # Concatenate all robot latitudes and longitudes to find the geographic extent
    latitudes = np.concatenate([d["pose.pose.position.x"].to_numpy() for d in logs.values()])
    longitudes = np.concatenate([d["pose.pose.position.y"].to_numpy() for d in logs.values()])

    # Find the geographic bounding box of the mission
    south, north = float(latitudes.min()), float(latitudes.max())
    west, east = float(longitudes.min()), float(longitudes.max())

    # Measure extent in normalized Web Mercator coordinates
    phi = np.radians(np.clip([south, north], -85.0, 85.0))
    y = (1 - np.log(np.tan(np.pi / 4 + phi / 2)) / np.pi) / 2
    span = max((east - west) / 360, float(abs(y[1] - y[0])), 1e-8)

    # Conservative viewport allowance; exact fit depends on screen size.
    zoom = float(np.clip(np.log2(220 / (512 * span)) - 0.35, 0, 18))
    middle_y = float(y.mean())
    center_lat = float(np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * middle_y)))))

    # Return the geographic center and zoom level for the mission overview
    return {"lat": center_lat, "lon": (west + east) / 2}, zoom


# Calculate the camera position and zoom to fit the mission's geographic extent
MISSION_CENTER, MISSION_ZOOM = mission_camera(replay_logs)


def build_initial_map(history, logs):
    """Set the visual style once; normal replay updates keep the camera."""

    # Buil th map with robot paths and currnt positions
    figure = build_trajectory_map(history, logs)

    # Adjust th appearanc for ach robot's drawin elements
    for trace in figure.data:
        if str(trace.uid).endswith("-past"):
            trace.opacity = 0.18
        elif str(trace.uid).endswith("-current"):
            trace.marker.size = 13

    # Apply the mission overviw and shared visual settings
    figure.update_layout(
        map_center=MISSION_CENTER, map_zoom=MISSION_ZOOM,
        font={"family": "Arial, sans-serif", 
              "color": "#334155"
        },
        legend={
            "orientation": "h", 
            "x": 0.01, 
            "y": 0.99,
            "xanchor": "left", 
            "yanchor": "top",
            "bgcolor": "rgba(255,255,255,0.9)",
            "bordercolor": "#e2e8f0", 
            "borderwidth": 1,
            "font": {"size": 11},
        },
    )

    # Build the map
    return figure

# Crate Dash application
app = Dash(
    assets_folder=str(project_dir / 'src/trajectory-visualizer/pov-plot'),
    assets_ignore=r'third_person\.(js|css)',
)


app.layout = [
    # Display the application title.
    html.Div(
        children="Trajectory Visualizer",
        style={
            "textAlign": "center",
            "fontSize": 30,
        },
    ),

    html.Hr(),

    # Select between the Local View and the Global View.
    dcc.Dropdown(
        id="view-selector",
        options=[
            {"label": "Visão Local", "value": "third-person"},
            {"label": "Visão Global", "value": "mapa"},
        ],
        value="third-person",
        clearable=False,
        style={
            "width": "220px",
            "margin": "12px 24px",
            "color": "black",
        },
    ),

    # Embed the Local View in the shared application.
    html.Div(
        id="third-person-view",
        children=[
            html.H2(
                "Visão Local",
                style={"margin": "20px 24px 8px"},
            ),
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

    # Create the Global View, initially hidden.
    html.Div(
        id="map-view",
        style={"display": "none"},
        children=[
            # Arrange replay controls above the map and sidebar.
            html.Div(
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "height": "calc(100dvh - 140px)",
                    "minHeight": "520px",
                    "gap": "10px",
                    "padding": "0 20px 16px",
                    "fontFamily": "system-ui, -apple-system, sans-serif",
                    "fontVariantNumeric": "tabular-nums",
                    "boxSizing": "border-box",
                },
                children=[
                    # Create the replay control panel.
                    html.Div(
                        style={
                            "flexShrink": 0,
                            "padding": "12px 16px 8px",
                            "backgroundColor": "#ffffff",
                            "border": "1px solid #e2e8f0",
                            "borderRadius": "12px",
                            "color": "#18253b",
                        },
                        children=[
                            # Arrange controls horizontally, wrapping when needed.
                            html.Div(
                                style={
                                    "display": "flex",
                                    "alignItems": "center",
                                    "gap": "10px",
                                    "flexWrap": "wrap",
                                    "marginBottom": "12px",
                                },
                                children=[
                                    # Create the play/pause button.
                                    html.Button(
                                        "▶ Reproduzir",
                                        id="replay-play-button",
                                        n_clicks=0,
                                        style={
                                            **BUTTON_STYLE,
                                            "backgroundColor": "#0f172a",
                                            "color": "white",
                                            "minWidth": "120px",
                                        },
                                    ),

                                    # Select the playback speed multiplier.
                                    dcc.Dropdown(
                                        id="replay-speed",
                                        options=[
                                            {"label": f"{v}×", "value": v}
                                            for v in (1, 5, 10, 25, 50, 100)
                                        ],
                                        value=1,
                                        clearable=False,
                                        searchable=False,
                                        style={
                                            "width": "88px",
                                            "fontSize": "13px",
                                        },
                                    ),

                                    # Reserve space for the mission clock.
                                    html.Div(
                                        id="mission-time-display",
                                        style={
                                            "fontSize": "15px",
                                            "fontWeight": "600",
                                            "fontVariantNumeric": "tabular-nums",
                                            "flex": "1 1 180px",
                                            "textAlign": "center",
                                        },
                                    ),

                                    # Request an overview of the complete mission.
                                    html.Button(
                                        "Enquadrar missão",
                                        id="fit-mission-map",
                                        n_clicks=0,
                                        style=BUTTON_STYLE,
                                    ),

                                    # Request a change in sidebar visibility.
                                    html.Button(
                                        "Ocultar painel",
                                        id="toggle-mission-sidebar",
                                        n_clicks=0,
                                        style=BUTTON_STYLE,
                                        **{
                                            "aria-controls": "mission-sidebar",
                                            "aria-expanded": "true",
                                        },
                                    ),
                                ],
                            ),

                            # Trigger playback updates every 250 milliseconds.
                            dcc.Interval(
                                id="replay-timer",
                                interval=250,
                                n_intervals=0,
                                disabled=True,
                            ),

                            # Store playback state in the browser.
                            dcc.Store(
                                id="replay-state",
                                data={
                                    "playing": False,
                                    "last_tick": None,
                                    "speed": 1,
                                },
                            ),

                            # Select the mission instant for the replay.
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

                    # Allocate five width shares to the map and two to the sidebar.
                    html.Div(
                        id="mission-workspace",
                        style={
                            "display": "grid",
                            "gridTemplateColumns": (
                                "minmax(0, 5fr) minmax(0, 2fr)"
                            ),
                            "flex": "1 1 0",
                            "minHeight": "220px",
                            "minWidth": 0,
                        },
                        children=[
                            # Create a container that the map can completely fill.
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
                                    # Display the initial map at mission time zero.
                                    dcc.Graph(
                                        id="mission-map",
                                        figure=build_initial_map(
                                            get_replay_history(
                                                replay_logs,
                                                0.0,
                                            ),
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

                            # Create a scrollable mission information sidebar.
                            html.Aside(
                                id="mission-sidebar",
                                style={
                                    "minWidth": 0,
                                    "minHeight": 0,
                                    "overflow": "auto",
                                    "boxSizing": "border-box",
                                    "padding": "14px",
                                    "backgroundColor": "#f8fafc",
                                    "color": "#18253b",
                                    "borderLeft": "1px solid #e2e8f0",
                                },
                                children=[
                                    # Label the sidebar information selector.
                                    html.Label(
                                        "Informação a apresentar",
                                        htmlFor="sidebar-section",
                                    ),

                                    # Select which information section is visible.
                                    dcc.Dropdown(
                                        id="sidebar-section",
                                        options=[
                                            {
                                                "label": "Coordenadas",
                                                "value": "coordinates",
                                            },
                                            {
                                                "label": "Distâncias",
                                                "value": "distances",
                                            },
                                            {
                                                "label": "Matrizes de rotação",
                                                "value": "rotations",
                                            },
                                            {
                                                "label": "Velocidades",
                                                "value": "velocities",
                                            },
                                        ],
                                        value="coordinates",
                                        clearable=False,
                                        searchable=False,
                                        style={"margin": "8px 0 16px"},
                                    ),

                                    # Keep every section mounted for callback access.
                                    # Show the coordinates section initially.
                                    html.Div(
                                        id="sidebar-coordinates",
                                        children=[
                                            html.Label(
                                                "Robot a consultar",
                                                htmlFor=(
                                                    "coordinate-robot-selector"
                                                ),
                                            ),

                                            # Select one robot or all robots.
                                            dcc.Dropdown(
                                                id="coordinate-robot-selector",
                                                options=[
                                                    {
                                                        "label": name,
                                                        "value": name,
                                                    }
                                                    for name in replay_logs
                                                ] + [
                                                    {
                                                        "label": "Todos os robots",
                                                        "value": "all",
                                                    }
                                                ],
                                                value=next(iter(replay_logs)),
                                                clearable=False,
                                                searchable=False,
                                                style={"margin": "8px 0 12px"},
                                            ),

                                            # Receive coordinate cards from a callback.
                                            html.Div(
                                                id="mission-coordinate-panel",
                                            ),
                                        ],
                                    ),

                                    # Create the initially hidden distances section.
                                    html.Div(
                                        id="sidebar-distances",
                                        style={"display": "none"},
                                        children=[
                                            html.H3(
                                                "Distâncias entre robots",
                                                style={"fontSize": "16px"},
                                            ),

                                            # Explain what the distances represent.
                                            html.P(
                                                "Distâncias horizontais aproximadas, "
                                                "calculadas com as últimas "
                                                "posições conhecidas. Não incluem Z.",
                                                style={
                                                    "fontSize": "12px",
                                                    "color": "#64748b",
                                                },
                                            ),

                                            # Receive pairwise distances from a callback.
                                            html.Div(
                                                id="mission-distance-panel",
                                            ),
                                        ],
                                    ),

                                    # Create the initially hidden velocities section.
                                    html.Div(
                                        id="sidebar-velocities",
                                        style={"display": "none"},
                                        children=[
                                            html.Label(
                                                "Robot a consultar",
                                                htmlFor=(
                                                    "velocity-robot-selector"
                                                ),
                                            ),

                                            # Select one robot or all robots.
                                            dcc.Dropdown(
                                                id="velocity-robot-selector",
                                                options=[
                                                    {
                                                        "label": name,
                                                        "value": name,
                                                    }
                                                    for name in replay_logs
                                                ] + [
                                                    {
                                                        "label": "Todos os robots",
                                                        "value": "all",
                                                    }
                                                ],
                                                value=next(iter(replay_logs)),
                                                clearable=False,
                                                searchable=False,
                                                style={"margin": "8px 0 12px"},
                                            ),

                                            # Explain the velocity reference and units.
                                            html.P(
                                                "Velocidades do log, expressas "
                                                "no referencial indicado. "
                                                "Unidades apresentadas segundo "
                                                "a convenção ROS: m/s e rad/s.",
                                                style={
                                                    "fontSize": "12px",
                                                    "color": "#64748b",
                                                },
                                            ),

                                            # Receive velocity cards from a callback.
                                            html.Div(
                                                id="mission-velocity-panel",
                                            ),
                                        ],
                                    ),

                                    # Create the initially hidden rotation section.
                                    html.Div(
                                        id="sidebar-rotations",
                                        style={"display": "none"},
                                        children=[
                                            # State the quaternion component order
                                            # and the unresolved frame direction.
                                            html.P(
                                                "Conversão dos quaterniões "
                                                "[x, y, z, w]. "
                                                "A direção entre referenciais "
                                                "está por confirmar.",
                                                style={
                                                    "fontSize": "12px",
                                                    "color": "#64748b",
                                                    "margin": "0 0 10px",
                                                },
                                            ),

                                            # Build initial rotation cards and
                                            # arrange them in a single column.
                                            html.Div(
                                                id="rotation-matrices",
                                                children=build_rotation_panels(
                                                    get_replay_history(
                                                        replay_logs,
                                                        0.0,
                                                    )
                                                ),
                                                style={
                                                    "display": "grid",
                                                    "gridTemplateColumns": (
                                                        "minmax(0, 1fr)"
                                                    ),
                                                    "gap": "12px",
                                                },
                                            ),
                                        ],
                                    ),
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
    """Display one compact distance card per robot pair."""

    # Store the completed cards.
    cards = []

    for row in rows:
        # Show a message when the pair has no calculated distance.
        if row["distance_m"] is None:
            value_text = "Sem dados suficientes para calcular a distância"
            age_text = ""

        else:
            # Display the approximate distance with one decimal place.
            value_text = f"≈ {row['distance_m']:.1f} m"

            # Display the age of each position in the pair's order.
            age_text = (
                "Idade das posições, pela ordem do par: "
                f"{row['first_age_s']:.1f} s / "
                f"{row['second_age_s']:.1f} s"
            )

        # Build one card for the current robot pair.
        cards.append(
            html.Div(
                children=[
                    # Separate the pair's names and create colored labels.
                    html.Div(
                        children=[
                            robot_label(name.strip())
                            for name in row["pair"].split("↔")
                        ],
                        style={
                            "display": "flex",
                            "gap": "10px",
                            "flexWrap": "wrap",
                        },
                    ),

                    # Show the distance or the missing-data message.
                    html.Div(
                        value_text,
                        style={
                            "fontSize": "26px",
                            "fontWeight": "600",
                            "margin": "10px 0",
                            "fontVariantNumeric": "tabular-nums",
                        },
                    ),

                    # Show measurement ages when a distance is available.
                    html.Div(
                        age_text,
                        style={
                            "fontSize": "12px",
                            "color": "#64748b",
                        },
                    ),
                ],
                style={
                    "padding": "12px",
                    "marginBottom": "10px",
                    "backgroundColor": "#ffffff",
                    "border": "1px solid #e2e8f0",
                    "borderRadius": "8px",
                },
            )
        )

    # Apply the shared appearance without replacing the pair labels.
    return polish_cards(cards)


def build_coordinate_panel(rows):
    """Display coordinates and measurement details as compact robot cards."""

    # Format available values with the requested precision and unit.
    def format_value(value, decimals, unit):
        return "—" if value is None else f"{value:.{decimals}f} {unit}"

    cards = []

    for row in rows:
        # Prepare the coordinates and measurement timing without displaying Z.
        fields = [
            ("Latitude", format_value(row["latitude"], 7, "°")),
            ("Longitude", format_value(row["longitude"], 7, "°")),
            ("Instante da medição", format_value(row["record_time_s"], 1, "s")),
            ("Idade da medição", format_value(row["age_s"], 1, "s")),
        ]

        # Create a label and a value for each field.
        entries = []

        for label, value in fields:
            entries.extend([
                html.Dt(
                    label,
                    style={
                        "color": "#64748b",
                        "fontSize": "12px",
                    },
                ),
                html.Dd(
                    value,
                    style={
                        "margin": "2px 0 10px",
                        "fontWeight": "600",
                        "fontVariantNumeric": "tabular-nums",
                        "overflowWrap": "anywhere",
                    },
                ),
            ])

        # Describe record availability independently of playback state.
        status = {
            "A aguardar": "A aguardar",
            "Em reprodução": "Dados disponíveis",
            "Log terminado": "Log terminado",
        }.get(row["status"], row["status"])

        # Build the coordinate card for the current robot.
        cards.append(
            html.Div(
                children=[
                    html.Div(
                        row["robot"],
                        style={
                            "fontWeight": "bold",
                            "fontSize": "16px",
                        },
                    ),
                    html.Div(
                        status,
                        style={
                            "fontSize": "12px",
                            "color": "#64748b",
                            "margin": "4px 0 12px",
                        },
                    ),
                    html.Dl(
                        entries,
                        style={"margin": 0},
                    ),

                    # Explain how measurement age is calculated.
                    html.P(
                        "Idade = tempo selecionado − tempo da medição.",
                        style={
                            "fontSize": "11px",
                            "color": "#64748b",
                            "margin": "0",
                        },
                    ),
                ],
                style={
                    "padding": "12px",
                    "marginBottom": "10px",
                    "backgroundColor": "#ffffff",
                    "border": "1px solid #e2e8f0",
                    "borderRadius": "8px",
                },
            )
        )

    # Apply the shared card style and robot identification.
    return polish_cards(cards, [row["robot"] for row in rows])


# Refresh coordinates when mission time or the selected robot changes.
@callback(
    Output("mission-coordinate-panel", "children"),
    Input("mission-time-slider", "value"),
    Input("coordinate-robot-selector", "value"),
)
def update_coordinate_panel(selected_time_s, selected_robot):
    """Update coordinate cards independently of the map."""

    # Select records available up to the chosen mission instant.
    history = get_replay_history(replay_logs, selected_time_s)

    # Prepare positions, measurement times and availability states.
    rows = build_position_rows(
        history,
        replay_logs,
        selected_time_s,
    )

    # Keep only the selected robot unless all robots were requested.
    if selected_robot != "all":
        rows = [
            row
            for row in rows
            if row["robot"] == selected_robot
        ]

    # Build the visual cards for the coordinate panel.
    return build_coordinate_panel(rows)


def build_velocity_panel(robot_history, prepared_logs, selected_time_s):
    """Display logged velocities without changing replay speed."""

    cards = []

    for name, history in robot_history.items():
        # Start the card with the robot's name.
        content = [
            html.Div(
                name,
                style={
                    "fontWeight": "bold",
                    "fontSize": "16px",
                },
            )
        ]

        # Handle robots with no record available at the selected instant.
        if history.empty:
            content.append(
                html.P("Sem registos neste instante.")
            )

        else:
            # Read the latest available record and its measurement age.
            current = history.iloc[-1]
            record_time_s = float(current["mission_time_s"])
            age_s = max(0.0, selected_time_s - record_time_s)

            # Check whether the selected instant is beyond this robot's log.
            log_ended = selected_time_s > float(
                prepared_logs[name]["mission_time_s"].iloc[-1]
            )

            # Read linear velocity components in the reported frame.
            linear = np.array(
                [
                    current[f"twist.twist.linear.{axis}"]
                    for axis in ("x", "y", "z")
                ],
                dtype=float,
            )

            # Read angular velocity components in the reported frame.
            angular = np.array(
                [
                    current[f"twist.twist.angular.{axis}"]
                    for axis in ("x", "y", "z")
                ],
                dtype=float,
            )

            # Calculate the magnitude of the full 3D linear velocity.
            speed_m_s = float(np.linalg.norm(linear))

            # Display record availability and linear speed magnitude.
            content.extend([
                html.Div(
                    (
                        "Última medição — log terminado"
                        if log_ended
                        else "Última medição disponível"
                    ),
                    style={
                        "fontSize": "12px",
                        "color": "#64748b",
                        "marginTop": "4px",
                    },
                ),
                html.Div(
                    "Velocidade total",
                    style={
                        "fontSize": "12px",
                        "marginTop": "12px",
                    },
                ),
                html.Div(
                    f"{speed_m_s:.3f} m/s",
                    style={
                        "fontSize": "24px",
                        "fontWeight": "bold",
                        "fontVariantNumeric": "tabular-nums",
                        "marginBottom": "12px",
                    },
                ),
            ])

            # Build separate sections for linear and angular components.
            for title, vector, unit in [
                ("Velocidade linear", linear, "m/s"),
                ("Velocidade angular", angular, "rad/s"),
            ]:
                entries = []

                # Associate each axis label with its corresponding component.
                for axis, value in zip(("X", "Y", "Z"), vector):
                    entries.extend([
                        html.Dt(
                            axis,
                            style={"color": "#64748b"},
                        ),
                        html.Dd(
                            f"{float(value):.4f} {unit}",
                            style={
                                "margin": 0,
                                "textAlign": "right",
                                "fontVariantNumeric": "tabular-nums",
                                "overflowWrap": "anywhere",
                            },
                        ),
                    ])

                # Arrange axis labels and values in two columns.
                content.extend([
                    html.Div(
                        title,
                        style={
                            "fontWeight": "600",
                            "fontSize": "13px",
                            "marginBottom": "6px",
                        },
                    ),
                    html.Dl(
                        entries,
                        style={
                            "display": "grid",
                            "gridTemplateColumns": "auto minmax(0, 1fr)",
                            "gap": "6px 12px",
                            "margin": "0 0 14px",
                            "fontSize": "13px",
                        },
                    ),
                ])

            # Show the reported frame, measurement instant and age.
            content.append(
                html.Div(
                    children=[
                        html.Div(
                            f"Referencial: {current['child_frame_id']}"
                        ),
                        html.Div(
                            f"Medição: {record_time_s:.1f} s de missão"
                        ),
                        html.Div(
                            f"Idade da medição: {age_s:.1f} s"
                        ),
                    ],
                    style={
                        "fontSize": "12px",
                        "color": "#64748b",
                        "lineHeight": "1.6",
                    },
                )
            )

        # Create a card even when no velocity record is available.
        cards.append(
            html.Div(
                children=content,
                style={
                    "padding": "12px",
                    "marginBottom": "10px",
                    "backgroundColor": "#ffffff",
                    "border": "1px solid #e2e8f0",
                    "borderRadius": "8px",
                },
            )
        )

    # Apply the shared card appearance and colored robot labels.
    return polish_cards(cards, list(robot_history))


# Refresh velocities when mission time or the selected robot changes.
@callback(
    Output("mission-velocity-panel", "children"),
    Input("mission-time-slider", "value"),
    Input("velocity-robot-selector", "value"),
)
def update_velocity_panel(selected_time_s, selected_robot):
    """Refresh velocity cards independently of the map."""

    # Select each robot's history at the chosen mission instant.
    history = get_replay_history(replay_logs, selected_time_s)

    # Restrict the dictionary to one robot when requested.
    if selected_robot != "all":
        history = {
            selected_robot: history[selected_robot],
        }

    # Build the cards using the selected histories and complete logs.
    return build_velocity_panel(
        history,
        replay_logs,
        selected_time_s,
    )


# Toggle sidebar visibility and update the workspace width distribution.
@callback(
    Output("mission-workspace", "style"),
    Output("mission-sidebar", "style"),
    Output("toggle-mission-sidebar", "children"),
    Output("toggle-mission-sidebar", "aria-expanded"),
    Input("toggle-mission-sidebar", "n_clicks"),
)
def toggle_mission_sidebar(n_clicks):
    """Let the map fill the workspace when the sidebar is hidden."""

    # Show the sidebar for even click counts, including the initial zero.
    visible = (n_clicks or 0) % 2 == 0

    # Use two columns when visible and one full-width column otherwise.
    workspace_style = {
        "display": "grid",
        "gridTemplateColumns": (
            "minmax(0, 5fr) minmax(0, 2fr)"
            if visible
            else "minmax(0, 1fr)"
        ),
        "flex": "1 1 0",
        "minHeight": "220px",
        "minWidth": 0,
    }

    # Preserve sidebar formatting while changing its visibility.
    sidebar_style = {
        "display": "block" if visible else "none",
        "minWidth": 0,
        "minHeight": 0,
        "overflow": "auto",
        "boxSizing": "border-box",
        "padding": "14px",
        "backgroundColor": "#f8fafc",
        "color": "#18253b",
        "borderLeft": "1px solid #e2e8f0",
    }

    # Update both layouts, the button label and its accessibility state.
    return (
        workspace_style,
        sidebar_style,
        "Ocultar painel" if visible else "Mostrar painel",
        "true" if visible else "false",
    )


# Change the visible sidebar section when its dropdown changes.
@callback(
    Output("sidebar-coordinates", "style"),
    Output("sidebar-distances", "style"),
    Output("sidebar-rotations", "style"),
    Output("sidebar-velocities", "style"),
    Input("sidebar-section", "value"),
)
def select_sidebar_section(section):
    """Show one section while keeping all callback targets mounted."""

    # Return one visibility style per Output, in the same order.
    return tuple(
        {"display": "block" if section == name else "none"}
        for name in (
            "coordinates",
            "distances",
            "rotations",
            "velocities",
        )
    )


# Serve the prepared trajectory data to the Local View as JSON.
@app.server.get("/api/robot-trajectories")
def robot_trajectories():
    """Return the trajectory payload consumed by the Local View."""

    return jsonify(viewer_payload)


# Serve the HTML page embedded in the Local View iframe.
@app.server.get("/third-person")
def third_person_view():
    """Return the Local View HTML page."""

    return send_from_directory(
        pov_dir,
        "third_person.html",
    )


# Serve Local View resources using the requested relative filename.
@app.server.get("/pov-assets/<path:filename>")
def pov_asset_file(filename):
    """Return a resource from the Local View directory."""

    return send_from_directory(
        pov_dir,
        filename,
    )


# Serve robot model files used by the Local View.
@app.server.get("/robot-model/<path:filename>")
def robot_model_file(filename):
    """Return a file from the robot model directory."""

    return send_from_directory(
        data_dir / "AUV model",
        filename,
    )


# This callback is currently disabled.
# The function below remains available for an explicit Python call.
# @callback(
#     Output("sendTable", "rowData"),
#     Output("sendTable", "columnDefs"),
#     Input("viewTable", "value"),
# )
def update_table(robot):
    """Prepare a robot's records and column definitions for a table."""

    # Select the original DataFrame associated with the robot.
    data = {
        "Robot 1": rd1,
        "Robot 4": rd4,
        "Robot 7": rd7,
    }[robot]

    # Return row dictionaries and one field definition per column.
    return (
        data.to_dict("records"),
        [
            {"field": column}
            for column in data.columns
        ],
    )


# Refresh the shared mission outputs when time changes or fit is requested.
@callback(
    Output("mission-time-display", "children"),
    Output("mission-map", "figure"),
    Output("rotation-matrices", "children"),
    Output("mission-distance-panel", "children"),
    Input("mission-time-slider", "value"),
    Input("fit-mission-map", "n_clicks"),
)
def update_mission_view(selected_time_s, fit_clicks):
    """Update the map, rotations, distances and clock for one mission instant."""

    # Use the same history for every output built in this callback.
    history = get_replay_history(
        replay_logs,
        selected_time_s,
    )

    # Rebuild the figure when the user requests the complete mission overview.
    if "fit-mission-map.n_clicks" in ctx.triggered_prop_ids:
        figure_patch = build_initial_map(
            history,
            replay_logs,
        )

        # Change the UI revision so the requested camera reset takes effect.
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
        # Update drawing data without replacing the current map camera.
        figure_patch = update_trajectory_map(
            history,
            replay_logs,
        )

    # Build rotation cards from the latest available orientations.
    rotation_panels = build_rotation_panels(history)

    # Calculate and display distances for every unique robot pair.
    distance_rows = build_distance_rows(
        history,
        selected_time_s,
    )
    distance_panel = build_distance_panel(distance_rows)

    # Display the selected mission time alongside the total duration.
    time_text = (
        f"{format_mission_time(selected_time_s)}"
        f" / {format_mission_time(mission_duration_s)}"
    )

    # Match the return order to the four Outputs above.
    return (
        time_text,
        figure_patch,
        rotation_panels,
        distance_panel,
    )


# Switch between the Local View and the Global View.
@callback(
    Output("third-person-view", "style"),
    Output("map-view", "style"),
    Input("view-selector", "value"),
)
def select_view(view):
    """Show the selected view and hide the other."""

    # Hide the Local View and show the Global View.
    if view == "mapa":
        return (
            {"display": "none"},
            {"display": "block"},
        )

    # Show the Local View for the other selection.
    return (
        {"display": "block"},
        {"display": "none"},
    )


# Handle playback button clicks, timer ticks and speed changes.
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

    # Read stored playback state and the current slider position.
    playing = playback_state["playing"]
    previous_speed = playback_state["speed"]
    last_tick = playback_state["last_tick"]
    current_time_s = float(selected_time_s)

    # Use an elapsed-time clock unaffected by system clock adjustments.
    now = time.monotonic()

    # Account for elapsed real time at the previously active speed.
    # On a speed change, the new speed applies after this update.
    if playing and last_tick is not None:
        elapsed_s = max(0.0, now - last_tick)
        current_time_s += elapsed_s * previous_speed

    # Identify button clicks through the callback context.
    # The click and interval counts trigger execution but are not used directly.
    if ctx.triggered_id == "replay-play-button":
        if playing:
            # Pause after accounting for the elapsed playback time.
            playing = False

        else:
            # Restart from zero when Play is pressed at the mission end.
            if current_time_s >= mission_duration_s:
                current_time_s = 0.0

            playing = True

    # Clamp the slider to the mission end and stop playback.
    if current_time_s >= mission_duration_s:
        current_time_s = mission_duration_s
        playing = False

    # Save the timing reference and selected speed for the next callback.
    new_state = {
        "playing": playing,
        "last_tick": now,
        "speed": selected_speed,
    }

    # Update the slider, timer, button label and stored state.
    # The timer is disabled whenever playback is paused.
    return (
        current_time_s,
        not playing,
        "Ⅱ Pausar" if playing else "▶ Reproduzir",
        new_state,
    )

if __name__ == '__main__':
    app.run(debug=True)
