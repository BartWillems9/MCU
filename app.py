import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
import dash
from dash import dcc, html, Output, Input, ctx, State
import geopandas as gpd
import pandas as pd
import plotly.express as px

df = pd.read_csv('MjS-data-lente2025.csv', sep='\t')

df2 = df[['id', 'timestamp', 'longitude', 'latitude', 'temperature', 'humidity']]
df2['longitude'] = df2.groupby('id')['longitude'].transform(lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
df2['latitude'] = df2.groupby('id')['latitude'].transform(lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0])
df2['timestamp'] = pd.to_datetime(df2['timestamp'])
ids_with_nan = df2.loc[df2['longitude'].isna() | df2['latitude'].isna(), 'id'].unique()
gdfz = df2[~df2['id'].isin(ids_with_nan)].copy()

neighborhoods = gpd.read_file('MCU-data-municip.shp')
neighborhoods = neighborhoods.to_crs("EPSG:4326")

geometry = [Point(lon, lat) for lon, lat in zip(gdfz['longitude'], gdfz['latitude'])]
gdf_group = gpd.GeoDataFrame(gdfz, geometry=geometry)
gdf_group.crs = "EPSG:4326"
print(f"Points CRS: {gdf_group.crs}")
gdf_group = gpd.sjoin(gdf_group, neighborhoods, how="left", predicate="within")
gdf_group['Name'].fillna('Onbekend of buiten Utrecht-Stad', inplace=True)
print(gdf_group['Name'])
gdf = gdf_group.copy()

app = dash.Dash(__name__)
app.title = "Dataclub Dashboard"

app.layout = html.Div(
    style={
        'fontFamily': 'Segoe UI, Tahoma, Geneva, Verdana, sans-serif',
        'backgroundColor': '#f0f2f5',
        'padding': '20px',
        'color': '#222'
    },
    children=[
        html.H1("🌡️ Interactief Dashboard - Meet Je Stad Utrecht", style={'textAlign': 'center', 'color': '#333'}),

        html.Div([
    html.Div([
        dcc.Dropdown(
            id='group-select',
            options=[
                {'label': 'Per kastje', 'value': 'sensor'},
                {'label': 'Per wijk', 'value': 'region'}
            ],
            value='sensor',
            placeholder='Groeperen op...',
            style={
                'height': '45px',
                'fontSize': '16px',
                'padding': '0 10px'
            }
        )
    ], style={'width': '200px'}),
    html.Div([
        dcc.Dropdown(
            id='multi-select',
            multi=True,
            placeholder='Sensoren of Wijken selecteren...',
            style={
                'height': '45px',
                'fontSize': '16px',
                'padding': '0 10px'
            }
        )
    ], style={'width': '400px', 'marginLeft': '20px'}),

    html.Div([
        dcc.DatePickerRange(
            id='date-picker',
            start_date=gdf['timestamp'].min(),
            end_date=gdf['timestamp'].max(),
            display_format='DD-MM-YYYY',
            style={
                'height': '45px',
                'fontSize': '16px',
                'padding': '0 10px'
            }
        )
    ], style={'marginLeft': '20px'})

    
], style={
    'display': 'flex',
    'justifyContent': 'center',
    'alignItems': 'center',
    'gap': '20px',
    'marginBottom': '30px'
}),


        html.Div([
            dcc.Graph(
                id='map',
                style={
                    'backgroundColor': 'white',
                    'borderRadius': '12px',
                    'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.1)',
                    'padding': '15px',
                    'margin': '10px',
                    'width': '50%',
                    'height': '600px'
                }
            ),
            dcc.Graph(
                id='temp-plot',
                style={
                    'backgroundColor': 'white',
                    'borderRadius': '12px',
                    'boxShadow': '0 4px 12px rgba(0, 0, 0, 0.1)',
                    'padding': '15px',
                    'margin': '10px',
                    'width': '50%',
                    'height': '600px'
                }
            )
        ], style={'display': 'flex', 'flexWrap': 'nowrap', 'justifyContent': 'center'}),

        
    ]
)

@app.callback(
    Output('multi-select', 'options'),
    Output('multi-select', 'value'),
    Input('group-select', 'value'),
    Input('map', 'clickData'),
    State('multi-select', 'value'),
    prevent_initial_call=True
)
def update_multi_select_combined(group_type, click_data, current_values):
    triggered = ctx.triggered_id

    if triggered == 'group-select':
        if group_type == 'sensor':
            options = [{'label': str(i), 'value': i} for i in sorted(gdf['id'].dropna().unique())]
        else:
            options = [{'label': str(i), 'value': i} for i in sorted(gdf['Name'].dropna().unique())]
        return options, []  # Clear current selections when switching group

    # Default to keep existing options
    if group_type == 'sensor':
        options = [{'label': str(i), 'value': i} for i in sorted(gdf['id'].dropna().unique())]
    else:
        options = [{'label': str(i), 'value': i} for i in sorted(gdf['Name'].dropna().unique())]

    # Handle map click
    if click_data:
        point = click_data['points'][0]
        if group_type == 'region':
            selected_value = point.get('customdata', [None])[0]
        else:
            selected_value = point.get('hovertext', None)

        if selected_value:
            if current_values is None:
                current_values = []
            if selected_value not in current_values:
                current_values.append(selected_value)

    return options, current_values or []



# Update map
@app.callback(
    Output('map', 'figure'),
    Input('group-select', 'value'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def update_map(group_type, start_date, end_date):
    filtered = gdf[(gdf['timestamp'] >= start_date) & (gdf['timestamp'] <= end_date)]

    if group_type == 'region':
        regions_to_plot = neighborhoods.copy()
        fig = px.choropleth_mapbox(
            regions_to_plot,
            geojson=regions_to_plot.geometry,
            locations=regions_to_plot.index,
            custom_data=['Name'],
            hover_data={'Name': True},
            mapbox_style='open-street-map',
            zoom=11,
            center={"lat": 52.0907, "lon": 5.080},
            opacity=0.4,
            color_discrete_sequence=["#76ac35"]
        )
    else:
        fig = px.scatter_mapbox(
            filtered,
            lat='latitude',
            lon='longitude',
            hover_name='id',
            mapbox_style='open-street-map',
            zoom=11,
            center={"lat": 52.0907, "lon": 5.080},
            size_max=20
        )

    fig.update_layout(margin={'r': 0, 't': 0, 'l': 0, 'b': 0})
    return fig


# Update temp plot
@app.callback(
    Output('temp-plot', 'figure'),
    Input('multi-select', 'value'),
    Input('group-select', 'value'),
    Input('date-picker', 'start_date'),
    Input('date-picker', 'end_date')
)
def update_temp_plot(selected_values, group_type, start_date, end_date):
    filtered = gdf[(gdf['timestamp'] >= start_date) & (gdf['timestamp'] <= end_date)]

    if not selected_values:
        return px.line(title="📍 Selecteer sensoren of wijken")

    if group_type == 'region':
        df = filtered[filtered['Name'].isin(selected_values)].copy()
        df['timestamp_hour'] = df['timestamp'].dt.floor('h')
        df_agg = df.groupby(['Name', 'timestamp_hour'])['temperature'].mean().reset_index()

        fig = px.line(
            df_agg,
            x='timestamp_hour',
            y='temperature',
            color='Name',
            title="📊 Gemiddelde temperatuur per wijk (per uur)",
        )
        fig.update_traces(opacity=0.6)
    else:
        df = filtered[filtered['id'].isin(selected_values)].copy()

        fig = px.line(
            df,
            x='timestamp',
            y='temperature',
            color='id',
            title="🌡️ Temperatuur per sensor",
        )
        fig.update_traces(opacity=0.6)

    fig.update_layout(
        xaxis_title='🕒 Tijdstip',
        yaxis_title='🌡️ Temperatuur (°C)',
        plot_bgcolor='white',
        margin={'r': 0, 't': 40, 'l': 30, 'b': 30}
    )
    return fig

server = app.server
if __name__ == '__main__':
    app.run(debug=True)
