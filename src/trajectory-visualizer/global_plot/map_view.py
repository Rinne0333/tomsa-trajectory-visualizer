import pandas as pd
import plotly.graph_objects as go
from dash import Patch

# Robot colors list
ROBOT_COLORS = {
    "Robot 1": "#2563eb",
    "Robot 4": "#ea580c",
    "Robot 7": "#9333ea",
    "Robot 8": "#16a34a",
}

# Column names for latitude and longitude in the DataFrame used on the map
LAT = "pose.pose.position.x"
LON = "pose.pose.position.y"

# Reduce the number of records used to draw a trajectory
def simplify_path(
    data: pd.DataFrame,
    max_points: int = 1000,
) -> pd.DataFrame:
    """Reduce line detail while keeping both endpoints."""

    # When the number of records is less than or equal to the maximum allowed, return the original data
    if len(data) <= max_points:
        return data

    # Calculate evenly spaced row positions, including both endpoints
    positions = [
        i * (len(data) - 1) // (max_points - 1)
        for i in range(max_points)
    ]

    # Select row by position instead of index label
    return data.iloc[positions]

# Prepare the past path, current record and future GeoJSON line for one robot
def get_robot_parts(history, full_data):
    """Prepare the past, current position and future path."""

    # Simplify only the line used for drawing
    past = simplify_path(history)

    # Keep the exact latest record, or an empty table
    current = history.tail(1)

    # Start at the current record to connect the past and future paths
    start_index = max(len(history) - 1, 0)
    future = simplify_path(full_data.iloc[start_index:])

    # Keep an empty source when no future line exists.
    source = {
        "type": "FeatureCollection",
        "features": [],
    }

    # Add a future line only when there are at least two records to connect
    if len(future) >= 2:
        source["features"].append(
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "LineString",
                    "coordinates": (
                        future[[LON, LAT]].to_numpy().tolist()
                    ),
                },
            }
        )

    return past, current, source

# Build the map with past apths, currnt markers and future layers
def build_trajectory_map(robot_history, prepared_logs):
    """Create the fixed map structure when the page loads."""

    # Creates a new empty plot figure responsible for reuning all the traces and layers of the map
    fig = go.Figure()

    # Store the future layers for each robot to be added to the map layout
    layers = []

    # Get each Robot a name and a selected color
    for name, color in ROBOT_COLORS.items():
        past, current, source = get_robot_parts(
            robot_history[name],
            prepared_logs[name],
        )

        # Add a permanent past-path trace for a robot
        fig.add_trace(
            go.Scattermap(
                # Use a unique identifier for the trace to avoid conflicts with other traces
                uid=f"{name}-past",
                name=name,
                legendgroup=name,
                lat=past[LAT].tolist(),
                lon=past[LON].tolist(),
                mode="lines",
                line={"width": 3, "color": color},
                opacity=0.7,
                hoverinfo="skip",
            )
        )

        # Add a permanent current position marker
        fig.add_trace(
            go.Scattermap(
                uid=f"{name}-current",
                name=name,
                legendgroup=name,
                showlegend=False,
                lat=current[LAT].tolist(),
                lon=current[LON].tolist(),
                mode="markers+text",
                marker={
                    "size": 11,
                    "color": color,
                    "opacity": 1,
                },
                text=[name],
                textposition="top center",
                textfont={
                    "size": 12,
                    "color": color,
                },
                customdata=(
                    current[["mission_time_s"]]
                    .to_numpy()
                    .tolist()
                ),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Latitude: %{lat:.7f}°<br>"
                    "Longitude: %{lon:.7f}°<br>"
                    "Record time: %{customdata[0]:.1f} s"
                    "<extra></extra>"
                ),
            )
        )

        # Keep one permanent future layer for each robot.
        layers.append(
            {
                "sourcetype": "geojson",
                "source": source,
                "type": "line",
                "color": color,
                "opacity": 0.35,
                "line": {
                    "width": 3,
                    "dash": [1, 3],
                },
                "below": "traces",
            }
        )

    # Set the camera only when creating the initial figure.
    fig.update_layout(
        map={
            "style": "open-street-map",
            "center": {"lat": 41.4525, "lon": -8.812},
            "zoom": 15,
            "layers": layers,
            "uirevision": "mission-map",
        },
        uirevision="mission-map",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
    )

    return fig

# Updates the drawing data while keeping the existing map struct
def update_trajectory_map(robot_history, prepared_logs):
    """Update coordinates without replacing the map structure."""

    # Collect the changes to be applied to the existing map figure
    patch = Patch()

    # Get each robot position in the configured robot order
    for index, name in enumerate(ROBOT_COLORS):

        # Prepare robot's past, current and futue data
        past, current, source = get_robot_parts(
            robot_history[name],
            prepared_logs[name],
        )

        # Each robot has two traces: past line, then current marker
        line_index = index * 2
        marker_index = line_index + 1

        # Replace the past line's coordinates with the new ones
        patch["data"][line_index]["lat"] = past[LAT].tolist()
        patch["data"][line_index]["lon"] = past[LON].tolist()

        # Replace the current marker's coordinates and custom data with the new ones
        patch["data"][marker_index]["lat"] = current[LAT].tolist()
        patch["data"][marker_index]["lon"] = current[LON].tolist()
        patch["data"][marker_index]["customdata"] = (
            current[["mission_time_s"]].to_numpy().tolist()
        )

        # Replace the future layer's source with the new one
        patch["layout"]["map"]["layers"][index]["source"] = source

    # Return the changes for the callback to apply to the figure
    return patch