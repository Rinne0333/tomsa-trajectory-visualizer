import math

import pandas as pd

# Receives a dictionary of robot logs and prepares them for replay visualization
def prepare_replay_data(robot_logs: dict[str, pd.DataFrame],) -> dict[str, pd.DataFrame]:
    """Prepare robot logs for replay visualization."""

    # Number of nanoseconds in one second
    ns_per_second = 1_000_000_000
    prepared_logs = {} 

    # Loop through each robot's logs and treat the timestamp columns to create a unified timestamp in nanoseconds
    for robot_name, data in robot_logs.items():

        # Copy the DataFrame to avoid modifying the original data
        prepared_data = data.copy()

        seconds = prepared_data["header.stamp.secs"]
        nanoseconds = prepared_data["header.stamp.nsecs"]

        # Unify Both values in Nanoseconds
        prepared_data["timestamp_ns"] = (seconds * ns_per_second + nanoseconds)

        # Sort the DataFrame by the new timestamp column to ensure chronological order
        prepared_logs[robot_name] = prepared_data.sort_values(by="timestamp_ns", kind="stable")

    # Find the earliest timestamp across all robots to establish a common temporal origin
    mission_start_ns = min(
        data["timestamp_ns"].iloc[0]
        for data in prepared_logs.values()
    )

    # Calculate the mission time in seconds for each robot's logs relative to the earliest timestamp
    for data in prepared_logs.values():
        data["mission_time_s"] = (data["timestamp_ns"] - mission_start_ns) / ns_per_second

    # Return the prepared logs with the new timestamp and mission time columns
    return prepared_logs


def build_viewer_payload(
    prepared_logs: dict[str, pd.DataFrame],
) -> dict[str, object]:
    """Serialize pose samples in a shared local east/up/north coordinate frame."""
    earth_radius_m = 6_378_137.0
    position_x = "pose.pose.position.x"
    position_y = "pose.pose.position.y"
    position_z = "pose.pose.position.z"
    quaternion_columns = [
        "pose.pose.orientation.x",
        "pose.pose.orientation.y",
        "pose.pose.orientation.z",
        "pose.pose.orientation.w",
    ]

    first_samples = [
        data.loc[data["mission_time_s"].idxmin()]
        for data in prepared_logs.values()
    ]
    origin = min(first_samples, key=lambda sample: sample["mission_time_s"])
    origin_latitude_rad = math.radians(origin[position_x])
    origin_longitude = origin[position_y]
    origin_altitude = origin[position_z]
    meters_per_degree = earth_radius_m * math.pi / 180.0

    robots: dict[str, list[list[float]]] = {}
    for robot_name, data in prepared_logs.items():
        latitude_delta = data[position_x] - origin[position_x]
        longitude_delta = data[position_y] - origin_longitude
        east_m = longitude_delta * meters_per_degree * math.cos(origin_latitude_rad)
        north_m = latitude_delta * meters_per_degree
        altitude_m = data[position_z] - origin_altitude

        samples = pd.DataFrame(
            {
                "time": data["mission_time_s"],
                "east": east_m,
                "up": altitude_m,
                "north": north_m,
                **{
                    column.rsplit(".", 1)[-1]: data[column]
                    for column in quaternion_columns
                },
            }
        )
        robots[robot_name] = samples.astype(float).to_numpy().tolist()

    return {
        "columns": ["time", "east", "up", "north", "qx", "qy", "qz", "qw"],
        "origin": {
            "latitude": float(origin[position_x]),
            "longitude": float(origin_longitude),
            "altitude": float(origin_altitude),
        },
        "robots": robots,
    }

# Get the history of each robot's records up to a selected mission time
def get_replay_history(
    prepared_logs: dict[str, pd.DataFrame],
    selected_time_s: float,
) -> dict[str, pd.DataFrame]:
    """Return each robot's records up to the selected mission time."""

    history = {}

    # Loop through each robot's prepared logs and filter the records based on the selected mission time
    for robot_name, data in prepared_logs.items():

        # Boolean mask to filter row where the mission time is less than or equal to the selected time
        mask = data["mission_time_s"] <= selected_time_s

        # Store the filtered DataFrame in the history dictionary for each robot
        history[robot_name] = data.loc[mask]

    # Return the history dictionary 
    return history