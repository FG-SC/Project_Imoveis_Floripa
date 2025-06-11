import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

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

st.title("Busca imóveis - Alternative Maps")

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
    df = df.dropna(subset=['lat', 'lon', 'price', 'area'])
    
    if len(df) == 0:
        st.error("No properties match your criteria")
        st.stop()
    
    st.write(f"Found {len(df)} properties")
    
    # Calculate quintiles for color scaling
    quintis = (df['price'].describe([.2, .4, .6, .8]).loc[['20%', '40%', '60%', '80%']]\
            /df['price'].max()).reset_index(drop=True)
    
    # Choose which map to display
    map_choice = st.radio("Choose map type:", 
                         ["Streamlit Native Map", "Folium Map", "Plotly Scatter", "PyDeck Map"])
    
    # ====================
    # OPTION 1: STREAMLIT NATIVE MAP (Most Reliable)
    # ====================
    if map_choice == "Streamlit Native Map":
        st.subheader("Streamlit Native Map")
        
        # Prepare data for streamlit map
        map_data = df[['lat', 'lon', 'price', 'area']].copy()
        
        # Add size column (normalized)
        map_data['size'] = df['area'] / df['area'].max() * 100  # Scale to 0-100
        
        # Simple but effective native streamlit map
        st.map(map_data[['lat', 'lon']], zoom=9)
        
        # Alternative with more control
        st.subheader("Enhanced Native Map")
        chart_data = df[['lat', 'lon', 'price']].copy()
        chart_data.columns = ['latitude', 'longitude', 'price']  # streamlit expects these names
        
        st.map(chart_data, 
               latitude='latitude',
               longitude='longitude', 
               size='price',
               color='price')
    
    # ====================
    # OPTION 2: FOLIUM MAP (Very Popular & Reliable)
    # ====================
    elif map_choice == "Folium Map":
        try:
            import folium
            from streamlit_folium import st_folium
            
            st.subheader("Folium Interactive Map")
            
            # Create base map
            center_lat = df['lat'].mean()
            center_lon = df['lon'].mean()
            
            m = folium.Map(location=[center_lat, center_lon], zoom_start=10)
            
            # Add markers with colors based on price
            for idx, row in df.iterrows():
                # Determine color based on price quintile
                if row['price'] <= df['price'].quantile(0.2):
                    color = 'blue'
                elif row['price'] <= df['price'].quantile(0.4):
                    color = 'lightblue'
                elif row['price'] <= df['price'].quantile(0.6):
                    color = 'green'
                elif row['price'] <= df['price'].quantile(0.8):
                    color = 'orange'
                else:
                    color = 'red'
                
                # Calculate radius based on area
                radius = max(5, min(20, row['area'] / df['area'].max() * 20))
                
                folium.CircleMarker(
                    location=[row['lat'], row['lon']],
                    radius=radius,
                    popup=f"Price: ${row['price']:,.0f}<br>Area: {row['area']:.0f}",
                    color=color,
                    fill=True,
                    opacity=0.7
                ).add_to(m)
            
            # Display the map
            st_folium(m, width=800, height=500)
            
        except ImportError:
            st.error("Folium not installed. Run: pip install folium streamlit-folium")
    
    # ====================
    # OPTION 3: PLOTLY SCATTER (No MapBox)
    # ====================
    elif map_choice == "Plotly Scatter":
        st.subheader("Plotly Scatter Plot")
        
        # Create regular scatter plot
        fig = px.scatter(df, x='lon', y='lat', 
                        color='price',
                        size='area',
                        hover_data=['price', 'area'],
                        color_continuous_scale='viridis',
                        size_max=20)
        
        fig.update_layout(
            title="Property Locations",
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            height=500,
            width=800
        )
        
        st.plotly_chart(fig)
    
    # ====================
    # OPTION 4: PYDECK MAP (Streamlit's 3D solution)
    # ====================
    elif map_choice == "PyDeck Map":
        st.subheader("PyDeck 3D Map")
        
        # Prepare data for pydeck
        pydeck_data = df[['lat', 'lon', 'price', 'area']].copy()
        
        # Normalize price for color (0-255 range)
        pydeck_data['price_norm'] = ((df['price'] - df['price'].min()) / 
                                    (df['price'].max() - df['price'].min()) * 255).astype(int)
        
        # Normalize area for size
        pydeck_data['area_norm'] = ((df['area'] - df['area'].min()) / 
                                   (df['area'].max() - df['area'].min()) * 100 + 10).astype(int)
        
        st.pydeck_chart({
            "map_style": "mapbox://styles/mapbox/light-v9",
            "initial_view_state": {
                "latitude": df['lat'].mean(),
                "longitude": df['lon'].mean(),
                "zoom": 10,
                "pitch": 0,
            },
            "layers": [{
                "type": "ScatterplotLayer",
                "data": pydeck_data,
                "get_position": ["lon", "lat"],
                "get_color": [255, 255, "price_norm", 160],
                "get_radius": "area_norm",
                "radius_scale": 6,
            }],
        })
    
    # Show the data
    st.subheader("Property Data")
    st.write(df)
