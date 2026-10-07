from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = [
    # Time and Identification Headers
    "Time",
    "header.seq",
    "header.stamp.secs",
    "header.stamp.nsecs",
    "header.frame_id",
    "child_frame_id",

    # Position Header.
    "pose.pose.position.x",
    "pose.pose.position.y",
    "pose.pose.position.z",

    # Orientation Header
    "pose.pose.orientation.x",
    "pose.pose.orientation.y",
    "pose.pose.orientation.z",
    "pose.pose.orientation.w",

    # Covariance Header
    "pose.covariance",

    # Linear Speed Header
    "twist.twist.linear.x",
    "twist.twist.linear.y",
    "twist.twist.linear.z",

    # Angular Speed Header
    "twist.twist.angular.x",
    "twist.twist.angular.y",
    "twist.twist.angular.z",

    # Speed Covariance
    "twist.covariance",
]

NUMERIC_COLUMNS = [
    # Time and sequence.
    "Time",
    "header.seq",
    "header.stamp.secs",
    "header.stamp.nsecs",

    # Position.
    "pose.pose.position.x",
    "pose.pose.position.y",
    "pose.pose.position.z",

    # Orientation.
    "pose.pose.orientation.x",
    "pose.pose.orientation.y",
    "pose.pose.orientation.z",
    "pose.pose.orientation.w",

    # Linear velocity.
    "twist.twist.linear.x",
    "twist.twist.linear.y",
    "twist.twist.linear.z",

    # Angular velocity.
    "twist.twist.angular.x",
    "twist.twist.angular.y",
    "twist.twist.angular.z",
]

def load_robot_log(csv_path: Path) -> pd.DataFrame:
    """Load a robot log and validate its structure and numeric fields."""
    data = pd.read_csv(csv_path)

    # Check required columns.
    missing_columns = []

    for column in REQUIRED_COLUMNS:
        if column not in data.columns:
            missing_columns.append(column)

    if missing_columns:
        raise ValueError(
            f"File '{csv_path.name}' is missing required columns: "
            f"{missing_columns}"
        )

    # Reject a file that has a header but no records.
    if data.empty:
        raise ValueError(
            f"File '{csv_path.name}' contains no records."
        )

    # Convert and validate each numeric column.
    for column in NUMERIC_COLUMNS:
        converted = pd.to_numeric(data[column], errors="coerce")

        invalid_mask = (
            converted.isna()
            | (converted == float("inf"))
            | (converted == float("-inf"))
        )

        invalid_count = invalid_mask.sum()

        if invalid_count > 0:
            raise ValueError(
                f"File '{csv_path.name}': column '{column}' contains "
                f"{invalid_count} missing, non-numeric or infinite values."
            )

        # Store the numeric values after validating the column.
        data[column] = converted

    return data