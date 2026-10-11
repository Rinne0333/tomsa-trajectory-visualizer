from dash import Dash, Input, Output, callback, dcc, html
from pathlib import Path

from data_loader import load_robot_log
from replay import prepare_replay_data


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

app = Dash()
app.layout = [
    html.Div(children='Trajectory Visualizer', style={'textAlign': 'center', 'fontSize': 30}),
    html.Hr(),
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
                marks={
                    0: "Início",
                    mission_duration_s: "Fim",
                },
                updatemode="drag",
            ),
        ],
        style={
            "padding": "20px 30px",
            "backgroundColor": "#f4f6f8",
            "borderRadius": "10px",
            "margin": "12px 20px",
        },
    ),
        dcc.Graph(
        figure=fig,
        style={'height': '85vh', 'width': '100%'},
        config={'responsive': True},
    ),
    dcc.RadioItems(options=['Robot 1', 'Robot 4', 'Robot 7'], value='Robot 1', id='viewTable', inline=True),
    dag.AgGrid(id='sendTable', rowData=[], columnDefs=[], dashGridOptions={'suppressFieldDotNotation': True})
]


@callback(
    Output('sendTable', 'rowData'),
    Output('sendTable', 'columnDefs'),
    Input('viewTable', 'value'),
)
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


if __name__ == '__main__':
    app.run(debug=True)