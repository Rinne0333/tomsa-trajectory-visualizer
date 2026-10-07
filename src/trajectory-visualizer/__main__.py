from dash import Dash, Input, Output, callback, dcc, html

import dash_ag_grid as dag
import pandas as pd
import plotly.express as px

rd1 = pd.read_csv('Robot Data/robot1_s1.csv')
rd4 = pd.read_csv('Robot Data/robot4_s1.csv')
rd7 = pd.read_csv('Robot Data/robot7_s1.csv')

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


if __name__ == '__main__':
    app.run(debug=True)