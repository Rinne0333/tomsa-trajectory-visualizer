import pandas as pd

def prepare_replay_data(robot_logs: dict[str, pd.DataFrame],) -> dict[str, pd.DataFrame]:
    ns_per_second = 1_000_000_000
    prepared_logs = {}      # Initalization of Returning Dictionary

    # Dictionary of the 3 Robot Data -> Update data without changing the original
    for robot_name, data in robot_logs.items():
        prepared_data = data.copy()

        seconds = prepared_data["header.stamp.secs"]
        nanoseconds = prepared_data["header.stamp.nsecs"]

        # Unify Both values in Nanoseconds
        prepared_data["timestamp_ns"] = (seconds * ns_per_second + nanoseconds)

        prepared_logs[robot_name] = prepared_data.sort_values(by="timestamp_ns", kind="stable")

    # Start Mission Instant
    mission_start_ns = min(
        data["timestamp_ns"].iloc[0]
        for data in prepared_logs.values()
    )

    # Apply same Temporal Origin to every register
    for data in prepared_logs.values():
        data["mission_time_s"] = (data["timestamp_ns"] - mission_start_ns) / ns_per_second

    return prepared_logs
        