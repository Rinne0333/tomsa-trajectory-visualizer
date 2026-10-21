import pandas as pd


def build_position_rows(
    robot_history: dict[str, pd.DataFrame],
    prepared_logs: dict[str, pd.DataFrame],
    selected_time_s: float,
) -> list[dict]:
    """Build one table row per robot using its latest available record."""

    rows = []

    for robot_name, full_data in prepared_logs.items():
        history = robot_history[robot_name]

        # Keep a row for robots that have not started yet.
        if history.empty:
            rows.append(
                {
                    "robot": robot_name,
                    "status": "A aguardar",
                    "latitude": None,
                    "longitude": None,
                    "position_z": None,
                    "record_time_s": None,
                    "age_s": None,
                }
            )
            continue

        # Use the same latest record displayed on the map.
        current = history.iloc[-1]
        record_time_s = float(current["mission_time_s"])
        last_time_s = float(full_data["mission_time_s"].iloc[-1])

        # Keep the last position after the robot's log ends.
        status = (
            "Log terminado"
            if selected_time_s > last_time_s
            else "Em reprodução"
        )

        rows.append(
            {
                "robot": robot_name,
                "status": status,
                "latitude": float(current["pose.pose.position.x"]),
                "longitude": float(current["pose.pose.position.y"]),
                "position_z": float(current["pose.pose.position.z"]),
                "record_time_s": record_time_s,
                "age_s": max(0.0, selected_time_s - record_time_s),
            }
        )

    return rows