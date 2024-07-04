import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title='Selection',
    page_icon="👀",
    layout='wide'
)

# Assuming imoveis_df is your DataFrame
para_alugar_df = st.session_state['data2']
para_alugar_df = para_alugar_df[para_alugar_df['area']>0]

df = para_alugar_df.copy().rename(columns={'tipo': 'type',
                                       'preço': 'rent_price',
                                       'aluguel_previsto': 'forecast_rent',
                                       'arbitragem_no_aluguel': 'rent_arbitrage',
                                       'bairro': 'neighborhood'},
                                       )

st.title("Busca imóveis")

st.write('This feature is in under construction yet, so I\'t will only work for __APARTAMENTOS__')

with st.form(key='my_form'):
    # First question: type of property
    types = list(sorted(df['type'].value_counts().index))
    selected_types = st.multiselect('Select type of property', options=types)

    # Filter DataFrame based on selected types
    df_type = df[df['type'].isin(selected_types)]
    # Second question: neighborhood
    neighborhoods = list(sorted(df['neighborhood'].value_counts().index))
    selected_neighborhoods = st.multiselect('Select neighborhoods', options=neighborhoods)

    # Filter DataFrame based on selected neighborhoods
    df_neighborhood = df_type[df_type['neighborhood'].isin(selected_neighborhoods)]

    # Third question: price range
    min_price, max_price = df_neighborhood['rent_price'].min(), df_neighborhood['rent_price'].max()
    selected_min_price = st.number_input('Select minimum rent price', min_value=min_price, max_value=max_price, value=min_price)
    selected_max_price = st.number_input('Select maximum rent price', min_value=selected_min_price, max_value=max_price, value=max_price)

    # Filter DataFrame based on selected price range
    df_price = df_neighborhood[(df_neighborhood['rent_price'] >= selected_min_price) & (df_neighborhood['rent_price'] <= selected_max_price)]

    # Fourth question: area range
    min_area, max_area = df_price['area'].min(), df_price['area'].max()
    selected_min_area = st.number_input('Select minimum area', min_value=min_area, max_value=max_area, value=min_area)
    selected_max_area = st.number_input('Select maximum area', min_value=selected_min_area, max_value=max_area, value=max_area)

    submit_button = st.form_submit_button(label='Submit')

if submit_button:
    # Filter DataFrame based on selected area range
    filtered_df = df_price[(df_price['area'] >= selected_min_area) & (df_price['area'] <= selected_max_area)]
    #st.write(filtered_df)

    df = filtered_df.copy()

    #print(tipo, price, area)
    quintis = (df['rent_price'].describe([.2, .4, .6, .8]).loc[['20%', '40%', '60%', '80%']]\
            /df['rent_price'].max()).reset_index(drop=True)


    mapbox_api_file = open('mapbox_token.txt', 'r')
    mapbox_token = mapbox_api_file.read()
    mapbox_api_file.close()

    px.set_mapbox_access_token(mapbox_token)

    fig = px.scatter_mapbox(df, lat='lat',
                            lon='lon', color='rent_price',
                        size = 'area',
                        #color_continuous_scale=px.colors.cyclical.Edge,
                        size_max=35, zoom = 9, opacity=.3)


    fig.update_coloraxes(colorscale = [
        [0,    'rgb(16, 26, 227, 0.5)'],
        [quintis[0], 'rgb(31, 120, 180, 0.5)'],
        [quintis[1], 'rgb(18, 223, 17, 0.5)'],
        [quintis[2],  'rgb(255, 234, 44, 0.5)'],
        [quintis[3], 'rgb(255, 178, 53, 0.5)'],
        [1,    'rgb(227, 26, 28, 0.5)'],
    ],
                        )


    fig.update_layout(height=500, width=800, mapbox=dict(center=              
                                            go.layout.mapbox.Center(lat=df['lat'].mean(), lon = df['lon'].mean())),
                    template = "plotly_dark"
                    )
    st.write(fig)

    st.write(df[['rent_price', 'forecast_rent', 'rent_arbitrage', 'link', 'area', 'descrição', 'quartos', 'banheiros', 'vagas_garagem']].sort_values(by='rent_arbitrage', ascending=False))
