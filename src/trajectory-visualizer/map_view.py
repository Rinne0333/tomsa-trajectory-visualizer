import pandas as pd
import plotly.graph_objects as go
from dash import Patch


ROBOT_COLORS = {
    "Robot 1": "#2563eb",
    "Robot 4": "#ea580c",
    "Robot 7": "#9333ea",
}

LAT = "pose.pose.position.x"
LON = "pose.pose.position.y"


def simplify_path(
    data: pd.DataFrame,
    max_points: int = 200,
) -> pd.DataFrame:
    """Reduce line detail while keeping both endpoints."""

    if len(data) <= max_points:
        return data

    positions = [
        i * (len(data) - 1) // (max_points - 1)
        for i in range(max_points)
    ]

    return data.iloc[positions]


def get_robot_parts(history, full_data):
    """Prepare the past, current position and future path."""

    # Simplify only the line used for drawing.
    past = simplify_path(history)

    # Keep the exact latest record, or an empty table.
    current = history.tail(1)

    # Connect the current position to the future path.
    start_index = max(len(history) - 1, 0)
    future = simplify_path(full_data.iloc[start_index:])

    # Keep an empty source when no future line exists.
    source = {
        "type": "FeatureCollection",
        "features": [],
    }

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


def build_trajectory_map(robot_history, prepared_logs):
    """Create the fixed map structure when the page loads."""

    fig = go.Figure()
    layers = []

    for name, color in ROBOT_COLORS.items():
        past, current, source = get_robot_parts(
            robot_history[name],
            prepared_logs[name],
        )

        # Create one permanent past trace for each robot.
        fig.add_trace(
            go.Scattermap(
                uid=f"{name}-past",
                name=name,
                legendgroup=name,
                lat=past[LAT].tolist(),
                lon=past[LON].tolist(),
                mode="lines",
                line={"width": 3, "color": color},
                opacity=0.12,
                hoverinfo="skip",
            )
        )

        # Create the marker even when its coordinates are empty.
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


def update_trajectory_map(robot_history, prepared_logs):
    """Update coordinates without replacing the map structure."""

    patch = Patch()

    for index, name in enumerate(ROBOT_COLORS):
        past, current, source = get_robot_parts(
            robot_history[name],
            prepared_logs[name],
        )

        # Each robot has two traces: past line, then current marker.
        line_index = index * 2
        marker_index = line_index + 1

        # Update the past line coordinates.
        patch["data"][line_index]["lat"] = past[LAT].tolist()
        patch["data"][line_index]["lon"] = past[LON].tolist()

        # Update the exact current position and its hover information.
        patch["data"][marker_index]["lat"] = current[LAT].tolist()
        patch["data"][marker_index]["lon"] = current[LON].tolist()
        patch["data"][marker_index]["customdata"] = (
            current[["mission_time_s"]].to_numpy().tolist()
        )

        # Update only the future layer's geometry.
        patch["layout"]["map"]["layers"][index]["source"] = source

    return patch