from dash import Dash, Input, Output, callback, dcc, html
from flask import jsonify, send_from_directory
from pathlib import Path

from data_loader import load_robot_log
from replay import build_viewer_payload, prepare_replay_data


import dash_ag_grid as dag
import pandas as pd
import plotly.express as px


project_dir = Path(__file__).resolve().parents[2]
data_dir = project_dir / "data"

rd1 = load_robot_log(data_dir / "robot1_s1.csv")
rd4 = load_robot_log(data_dir / "robot4_s1.csv")
rd7 = load_robot_log(data_dir / "robot7_s1.csv")

# Replay Logs ordered and prepared for replay
replay_logs = prepare_replay_data(
    {
        "Robot 1": rd1,
        "Robot 4": rd4,
        "Robot 7": rd7
    }
)
viewer_payload = build_viewer_payload(replay_logs)

mission_duration_s = float(
    max(
        data["mission_time_s"].max()
        for data in replay_logs.values()
    )
)

trajectories = pd.concat(
    [
        data.assign(robot=label)[
            ['Time', 'pose.pose.position.x', 'pose.pose.position.y', 'robot']
        ]
        for label, data in [('Robot 1', rd1), ('Robot 4', rd4), ('Robot 7', rd7)]
    ],
    ignore_index=True,
).sort_values(['robot', 'Time'])

fig = px.line_map(
    trajectories,
    lat='pose.pose.position.x',
    lon='pose.pose.position.y',
    color='robot',
    hover_data=['Time'],
    map_style='open-street-map',
    center={'lat': 41.4525, 'lon': -8.812},
    zoom=15,
)

fig.update_traces(mode='lines+markers')

app = Dash(
    assets_folder=str(project_dir / 'assets'),
    assets_ignore=r'third_person\.(js|css)',
)
app.layout = [
    html.Div(children='Trajectory Visualizer', style={'textAlign': 'center', 'fontSize': 30}),
    html.Hr(),
    dcc.Dropdown(
        id="view-selector",
        options=[
            {"label": "Visão Local", "value": "third-person"},
            {"label": "Visão Global", "value": "mapa"},
        ],
        value="third-person-view",
        clearable=False,
        style={"width": "220px", "margin": "12px 24px", "color": "black"},
    ),
    html.Div(
        id="third-person-view",
        children=[
            html.H2("Visão Local", style={"margin": "20px 24px 8px"}),
            html.Iframe(
                src="/third-person",
                title="Three-dimensional robot replay",
                style={
                    "height": "720px",
                    "width": "calc(100% - 48px)",
                    "margin": "0 24px 24px",
                    "border": "0",
                    "display": "block",
                },
            ),
        ],
    ),
    html.Div(
        id="map-view",
        style={"display": "none"},
        children=[
            # Put the existing mission-time display and slider here.
            # Keep their IDs: mission-time-display, mission-time-slider.
            html.Div(
                children=[
                    html.Div(
                        id="mission-time-display",
                        style={
                            "textAlign": "center",
                            "fontSize": "20px",
                            "fontWeight": "bold",
                            "fontVariantNumeric": "tabular-nums",
                            "marginBottom": "16px",
                        },
                    ),
                    dcc.Slider(
                        id="mission-time-slider",
                        min=0,
                        max=mission_duration_s,
                        step=0.1,
                        value=0,
                        marks={0: "Início", mission_duration_s: "Fim"},
                        updatemode="drag",
                    ),
                ],
                style={
                    "padding": "10px 10px",
                    "backgroundColor": "#f4f6f8",
                    "borderRadius": "10px",
                    "margin": "12px 20px",
                },
            ),
            dcc.Graph(
                figure=fig,
                style={"height": "85vh", "width": "100%"},
                config={"responsive": True},
            ),
        ],
    ),
    # dcc.Graph(
    #     figure=fig,
    #     style={'height': '85vh', 'width': '100%'},
    #     config={'responsive': True},
    # ),
    # dcc.RadioItems(options=['Robot 1', 'Robot 4', 'Robot 7'], value='Robot 1', id='viewTable', inline=True),
    # dag.AgGrid(id='sendTable', rowData=[], columnDefs=[], dashGridOptions={'suppressFieldDotNotation': True})
]


@app.server.get('/api/robot-trajectories')
def robot_trajectories():
    return jsonify(viewer_payload)


@app.server.get('/third-person')
def third_person_view():
    return send_from_directory(project_dir / 'assets', 'third_person.html')


@app.server.get('/robot-model/<path:filename>')
def robot_model_file(filename):
    return send_from_directory(data_dir / 'AUV model', filename)


# @callback(
#     Output('sendTable', 'rowData'),
#     Output('sendTable', 'columnDefs'),
#     Input('viewTable', 'value'),
# )
def update_table(robot):
    data = {
        'Robot 1': rd1,
        'Robot 4': rd4,
        'Robot 7': rd7,
    }[robot]

    return (
        data.to_dict('records'),
        [{'field': column} for column in data.columns],
    )

# Update Text when Slider Value Changes
@callback(
    Output("mission-time-display", "children"),
    Input("mission-time-slider", "value"),
)
def update_mission_time(selected_time_s):
    return (
        f"Tempo de missão: {selected_time_s:.1f} s"
        f" / {mission_duration_s:.1f} s"
    )

@callback(
    Output("third-person-view", "style"),
    Output("map-view", "style"),
    Input("view-selector", "value"),
)
def select_view(view):
    if view == "mapa":
        return {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "none"}


if __name__ == '__main__':
    app.run(debug=True)