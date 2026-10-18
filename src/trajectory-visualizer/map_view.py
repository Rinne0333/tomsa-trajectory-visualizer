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
        opacity=0.35,   # Makes the course more "bright"
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
                    "size": 18,
                    "color": ROBOT_COLORS[robot_name],
                    "opacity": 1,
                },
                text=[robot_name],
                textposition="top center",
                textfont={
                    "size": 14,
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

    # Preserve the user's zoom and map position during updates.
    fig.update_layout(
        uirevision="mission-map",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
    )

    return fig