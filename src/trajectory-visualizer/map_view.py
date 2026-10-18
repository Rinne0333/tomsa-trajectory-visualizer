import pandas as pd
import plotly.express as px
import plotly.graph_objects as go       # Add Individual Plotly Elements as Robot Markers for example


ROBOT_COLORS = {
    "Robot 1": "#2563eb",
    "Robot 4": "#ea580c",
    "Robot 7": "#9333ea",
}

def build_trajectory_map(
    robot_history: dict[str, pd.DataFrame],
    prepared_logs: dict[str, pd.DataFrame],
):
    """Build a map from the available history of each robot."""

    # Combine robot histories and identify each robot.
    trajectories = pd.concat(
        [
            data.assign(robot=robot_name)[
                [
                    "mission_time_s",
                    "pose.pose.position.x",
                    "pose.pose.position.y",
                    "robot",
                ]
            ]
            for robot_name, data in robot_history.items()
        ],
        ignore_index=True,
    )

    # Draw each robot's available trajectory.
    fig = px.line_map(
        trajectories,
        lat="pose.pose.position.x",
        lon="pose.pose.position.y",
        color="robot",
        color_discrete_map=ROBOT_COLORS,
        hover_data=["mission_time_s"],
        map_style="open-street-map",
        center={"lat": 41.4525, "lon": -8.812},
        zoom=15,
    )

    # Show lines and recorded positions
    # Draw past trajectories as lighter lines without sample markers
    fig.update_traces(
        mode="lines",   # Removes small points from all samples
        opacity=0.08,   # Makes the course more "bright"
        line={"width": 3},
    )

    # Add one current-position marker for each available robot
    for robot_name, data in robot_history.items():

        # Skip robots that have no records at the selected time
        if data.empty:
            continue

        # Get the latest available record from the sorted history
        current_record = data.iloc[-1]

        # Draw the current position above the trajectory
        fig.add_trace(
            go.Scattermap(
                lat=[current_record["pose.pose.position.x"]],
                lon=[current_record["pose.pose.position.y"]],
                mode="markers+text",
                marker={
                    "size": 11,
                    "color": ROBOT_COLORS[robot_name],
                    "opacity": 1,
                },
                text=[robot_name],
                textposition="top center",
                textfont={
                    "size": 12,
                    "color": ROBOT_COLORS[robot_name],
                },
                name=robot_name,
                legendgroup=robot_name,
                showlegend=False,
                customdata=[
                    [current_record["mission_time_s"]]
                ],
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Latitude: %{lat:.7f}°<br>"
                    "Longitude: %{lon:.7f}°<br>"
                    "Record time: %{customdata[0]:.1f} s"
                    "<extra></extra>"
                ),
            )
        )

        # Store future trajectories as dashed map layers.
    future_layers = []

    for robot_name, full_data in prepared_logs.items():
        history = robot_history[robot_name]

        # Include the current position to connect it to the future path.
        # Before the robot starts, its entire trajectory is still future.
        start_index = max(len(history) - 1, 0)
        future_data = full_data.iloc[start_index:]

        # A line needs at least two points.
        if len(future_data) < 2:
            continue

        # GeoJSON coordinates use longitude first, then latitude.
        coordinates = future_data[
            [
                "pose.pose.position.y",
                "pose.pose.position.x",
            ]
        ].to_numpy().tolist()

        # Add a dashed line below the robot markers and past traces.
        future_layers.append(
            {
                "sourcetype": "geojson",
                "source": {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                },
                "type": "line",
                "color": ROBOT_COLORS[robot_name],
                "opacity": 0.45,
                "line": {
                    "width": 2,
                    "dash": [3, 3],
                },
                "below": "traces",
            }
        )
    
    # Apply future layers and preserve the user's map position.
    fig.update_layout(
        map_layers=future_layers,
        uirevision="mission-map",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
    )

    return fig