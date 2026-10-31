from itertools import combinations

import numpy as np


LAT = "pose.pose.position.x"
LON = "pose.pose.position.y"
EARTH_RADIUS_M = 6_371_008.8


def horizontal_distance_m(lat1, lon1, lat2, lon2):
    """Calculate approximate surface distance in metres."""

    # Convert degrees to radians.
    phi1, phi2 = np.radians([lat1, lat2])
    delta_phi = phi2 - phi1
    delta_lambda = np.radians(lon2 - lon1)

    # Haversine formula for a spherical Earth.
    a = (
        np.sin(delta_phi / 2) ** 2
        + np.cos(phi1)
        * np.cos(phi2)
        * np.sin(delta_lambda / 2) ** 2
    )

    # Avoid rounding errors outside the valid range.
    a = np.clip(a, 0.0, 1.0)

    angle = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    return float(EARTH_RADIUS_M * angle)


def build_distance_rows(robot_history, selected_time_s):
    """Calculate each unique robot pair using its latest records."""

    rows = []

    # Generate each pair once, without pairing a robot with itself.
    for first_name, second_name in combinations(robot_history, 2):
        first_history = robot_history[first_name]
        second_history = robot_history[second_name]

        row = {
            "pair": f"{first_name} ↔ {second_name}",
            "distance_m": None,
            "first_age_s": None,
            "second_age_s": None,
        }

        # Wait until both robots have a position.
        if not first_history.empty and not second_history.empty:
            first = first_history.iloc[-1]
            second = second_history.iloc[-1]

            row["distance_m"] = horizontal_distance_m(
                float(first[LAT]),
                float(first[LON]),
                float(second[LAT]),
                float(second[LON]),
            )

            # Keep measurement age visible when a log stops updating.
            row["first_age_s"] = max(
                0.0,
                selected_time_s - float(first["mission_time_s"]),
            )
            row["second_age_s"] = max(
                0.0,
                selected_time_s - float(second["mission_time_s"]),
            )

        rows.append(row)

    return rows