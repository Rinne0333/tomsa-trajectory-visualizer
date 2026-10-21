from dash import html

from orientation import quaternion_to_matrix, check_rotation_matrix


def build_rotation_panels(robot_history):
    """Build one rotation matrix panel for each robot."""

    panels = []

    for robot_name, history in robot_history.items():
        content = [
            html.H4(
                robot_name,
                style={"margin": "0 0 8px"},
            )
        ]

        # Do not invent an orientation before the first record.
        if history.empty:
            content.append(
                html.P("Sem dados neste instante.")
            )

        else:
            # Use the same latest record displayed on the map.
            current = history.iloc[-1]

            try:
                rotation = quaternion_to_matrix(
                    current["pose.pose.orientation.x"],
                    current["pose.pose.orientation.y"],
                    current["pose.pose.orientation.z"],
                    current["pose.pose.orientation.w"],
                )

                validation = check_rotation_matrix(rotation)

            except ValueError as error:
                # Keep the remaining panels working if one quaternion is invalid.
                content.append(
                    html.P(
                        f"Orientação inválida: {error}",
                        style={"color": "#b91c1c"},
                    )
                )

            else:
                # Format only the displayed values.
                matrix_rows = []

                for row in rotation:
                    cells = []

                    for value in row:
                        text = f"{value:.4f}"

                        # Avoid displaying negative zero after rounding.
                        if text == "-0.0000":
                            text = "0.0000"

                        cells.append(
                            html.Td(
                                text,
                                style={
                                    "padding": "5px 10px",
                                    "textAlign": "right",
                                },
                            )
                        )

                    matrix_rows.append(html.Tr(cells))

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

                # Show the time of the orientation measurement.
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

                # Display the numerical validation result.
                valid = validation["valid"]

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

    return panels