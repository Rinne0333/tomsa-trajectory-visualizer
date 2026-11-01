from dash import html

from .orientation import quaternion_to_matrix, check_rotation_matrix


# Build a rotation card per robot using it's latest available record
def build_rotation_panels(robot_history):
    """Build one rotation matrix panel for each robot."""

    # STore the completed robot cards
    panels = []

    # Process each robot's available history
    for robot_name, history in robot_history.items():

        # Start the card with the robot's name
        content = [
            html.H4(
                robot_name,
                style={"margin": "0 0 8px"},
            )
        ]

        # Check if exist measurements for the robot, if not show a message
        if history.empty:
            content.append(
                html.P("Sem dados neste instante.")
            )

        else:
            # Use the same latest record displayed on the map.
            current = history.iloc[-1]


            try:
                # Convert a recorded quaternion to a rotation matrix
                rotation = quaternion_to_matrix(
                    current["pose.pose.orientation.x"],
                    current["pose.pose.orientation.y"],
                    current["pose.pose.orientation.z"],
                    current["pose.pose.orientation.w"],
                )

                # Check the rotation matrix for orthogonality and determinant
                validation = check_rotation_matrix(rotation)

            # Display an error message if the quaternion is invalid or the rotation matrix is not proper
            except ValueError as error:
                content.append(
                    html.P(
                        f"Orientação inválida: {error}",
                        style={"color": "#b91c1c"},
                    )
                )

            else:
                # Store the three html rows of the matrix
                matrix_rows = []

                # Process one row at a time
                for row in rotation:

                    # Store the three cells of  the row
                    cells = []

                    for value in row:

                        # Format the value to four decimals
                        text = f"{value:.4f}"

                        # Avoid displaying negative zero after rounding.
                        if text == "-0.0000":
                            text = "0.0000"

                        # Create one table cell for the value, right-aligned with padding
                        cells.append(
                            html.Td(
                                text,
                                style={
                                    "padding": "5px 10px",
                                    "textAlign": "right",
                                },
                            )
                        )

                    # Add the completed row to the matrix display
                    matrix_rows.append(html.Tr(cells))

                # Add the completed matrix to the card, with a border and monospace font
                content.append(
                    html.Table(
                        html.Tbody(matrix_rows),
                        style={
                            "width": "100%",
                            "borderLeft": "2px solid #64748b",
                            "borderRight": "2px solid #64748b",
                            "fontFamily": "monospace",
                            "fontVariantNumeric": "tabular-nums",
                            "fontSize": "14px",
                        },
                    )
                )

                # Show the time of the orientation measurement
                content.append(
                    html.Div(
                        f"Medição: {current['mission_time_s']:.1f} s",
                        style={
                            "marginTop": "8px",
                            "fontSize": "12px",
                            "color": "#64748b",
                        },
                    )
                )

                # Display the numerical validation result
                valid = validation["valid"]

                # Show the determinant and validation status
                content.append(
                    html.Div(
                        (
                            f"det(R) = {validation['determinant']:.6f}"
                            f" · {'Verificada' if valid else 'Falha na validação'}"
                        ),
                        style={
                            "marginTop": "4px",
                            "fontSize": "12px",
                            "color": "#15803d" if valid else "#b91c1c",
                        },
                    )
                )

        # Wrap this robot's content in a card with padding, border, and background color
        panels.append(
            html.Div(
                children=content,
                style={
                    "padding": "12px",
                    "border": "1px solid #e2e8f0",
                    "borderRadius": "8px",
                    "backgroundColor": "#ffffff",
                    "color": "#18253b",
                    "minWidth": 0,
                },
            )
        )
        
    # Return the list of completed robot cards
    return panels