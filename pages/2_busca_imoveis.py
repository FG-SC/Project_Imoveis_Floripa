import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title='Selection',
    page_icon="👀",
    layout='wide'
)

# Assuming imoveis_df is your DataFrame
imoveis_df = st.session_state['data']
imoveis_df = imoveis_df[imoveis_df['area']>0]
df = imoveis_df.copy().rename(columns={'tipo': 'type',
                                       'preço': 'price',
                                       'bairro': 'neighborhood'},
                                       )

st.title("Busca imóveis")

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
    min_price, max_price = df_neighborhood['price'].min(), df_neighborhood['price'].max()
    selected_min_price = st.number_input('Select minimum price', min_value=min_price, max_value=max_price, value=min_price)
    selected_max_price = st.number_input('Select maximum price', min_value=selected_min_price, max_value=max_price, value=max_price)
    
    # Filter DataFrame based on selected price range
    df_price = df_neighborhood[(df_neighborhood['price'] >= selected_min_price) & (df_neighborhood['price'] <= selected_max_price)]
    
    # Fourth question: area range
    min_area, max_area = df_price['area'].min(), df_price['area'].max()
    selected_min_area = st.number_input('Select minimum area', min_value=min_area, max_value=max_area, value=min_area)
    selected_max_area = st.number_input('Select maximum area', min_value=selected_min_area, max_value=max_area, value=max_area)
    
    submit_button = st.form_submit_button(label='Submit')

if submit_button:
    # Filter DataFrame based on selected area range
    filtered_df = df_price[(df_price['area'] >= selected_min_area) & (df_price['area'] <= selected_max_area)]
    
    df = filtered_df.copy()
    
    # Calculate quintiles for color scaling
    quintis = (df['price'].describe([.2, .4, .6, .8]).loc[['20%', '40%', '60%', '80%']]\
            /df['price'].max()).reset_index(drop=True)
    
    # NO MAPBOX TOKEN NEEDED ANYMORE!
    # Create the scatter mapbox plot with Open Street Map
    fig = px.scatter_mapbox(df, lat='lat', lon='lon', color='price',
                        size='area',
                        size_max=35, 
                        zoom=9, 
                        opacity=0.3,
                        mapbox_style="open-street-map")  # This is the key change!
    
    # Keep your exact same color scheme
    fig.update_coloraxes(colorscale = [
        [0,    'rgb(16, 26, 227, 0.5)'],
        [quintis[0], 'rgb(31, 120, 180, 0.5)'],
        [quintis[1], 'rgb(18, 223, 17, 0.5)'],
        [quintis[2],  'rgb(255, 234, 44, 0.5)'],
        [quintis[3], 'rgb(255, 178, 53, 0.5)'],
        [1,    'rgb(227, 26, 28, 0.5)'],
    ])
    
    # Keep your exact same layout
    fig.update_layout(height=500, width=800, 
                     mapbox=dict(center=go.layout.mapbox.Center(
                         lat=df['lat'].mean(), 
                         lon=df['lon'].mean())),
                     template="plotly_dark")
    
    st.plotly_chart(fig)
    st.write(df)
