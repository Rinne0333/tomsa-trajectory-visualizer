# Generate unique robot pairs
from itertools import combinations

# To perform angle convertions and math calculations
import numpy as np


LAT = "pose.pose.position.x"
LON = "pose.pose.position.y"
EARTH_RADIUS_M = 6_371_008.8

# Estimate the horizontal distance between two points on the Earth's surface using the Haversine formula
def horizontal_distance_m(lat1, lon1, lat2, lon2):
    """Calculate approximate surface distance in metres."""

    # Convert both latitudes from degrees to radians
    phi1, phi2 = np.radians([lat1, lat2])

    # Calculate the difference in latitude and longitude in radians
    delta_phi = phi2 - phi1
    delta_lambda = np.radians(lon2 - lon1)

    # Calculate the intermediate value 'a' using the Haversine formula
    a = (
        np.sin(delta_phi / 2) ** 2
        + np.cos(phi1)
        * np.cos(phi2)
        * np.sin(delta_lambda / 2) ** 2
    )

    # Keep the value of 'a' within the range [0, 1] to avoid numerical issues
    a = np.clip(a, 0.0, 1.0)

    # Calculate the central angle between the two points
    angle = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # Convert the angle to distance by multiplying with the Earth's radius
    return float(EARTH_RADIUS_M * angle)


# Apply the Haversine formula to each unique robot pair
def build_distance_rows(robot_history, selected_time_s):
    """Calculate each unique robot pair using its latest records."""

    # One dictionary per robot pair
    rows = []

    # Generate each pair once, without pairing a robot with itself
    for first_name, second_name in combinations(robot_history, 2):

        # Read each available robot's latest record, if any
        first_history = robot_history[first_name]
        second_history = robot_history[second_name]

        # Calculate the distance and measurement age for each robot pair, if both have a position
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

            # Calculate the horizontal distance from latitude and longitude using the Haversine formula
            row["distance_m"] = horizontal_distance_m(
                float(first[LAT]),
                float(first[LON]),
                float(second[LAT]),
                float(second[LON]),
            )

            # Calculate the age of each robot's latest measurement relative to the selected time
            row["first_age_s"] = max(
                0.0,
                selected_time_s - float(first["mission_time_s"]),
            )
            row["second_age_s"] = max(
                0.0,
                selected_time_s - float(second["mission_time_s"]),
            )

        # Store the pair's information, even if one or both robots have no position data
        rows.append(row)
    
    return rows