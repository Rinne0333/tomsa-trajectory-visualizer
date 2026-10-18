import pandas as pd
import plotly.express as px


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
        color_discrete_map={
            "Robot 1": "#2563eb",
            "Robot 4": "#ea580c",
            "Robot 7": "#9333ea",
        },
        hover_data=["mission_time_s"],
        map_style="open-street-map",
        center={"lat": 41.4525, "lon": -8.812},
        zoom=15,
    )

    # Show lines and recorded positions.
    fig.update_traces(mode="lines+markers")

    # Preserve the user's zoom and map position during updates.
    fig.update_layout(
        uirevision="mission-map",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
    )

    return fig