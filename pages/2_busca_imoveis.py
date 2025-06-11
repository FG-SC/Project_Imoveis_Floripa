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
    df = df.dropna(subset=['lat', 'lon', 'price', 'area'])
    
    if len(df) == 0:
        st.error("No properties match your criteria")
        st.stop()
    
    # Calculate quintiles for color scaling (your original logic)
    quintis = (df['price'].describe([.2, .4, .6, .8]).loc[['20%', '40%', '60%', '80%']]\
            /df['price'].max()).reset_index(drop=True)
    
    # Choose map type
    map_type = st.radio("Choose map style:", ["Simple Streamlit Map", "Plotly Map with Original Colors"])
    
    if map_type == "Simple Streamlit Map":
        # SIMPLE STREAMLIT MAP (guaranteed to work)
        st.subheader("Property Locations")
        
        # Prepare simple map data
        simple_map_data = df[['lat', 'lon', 'price', 'area']].copy()
        simple_map_data.columns = ['latitude', 'longitude', 'price', 'area']
        simple_map_data = simple_map_data.reset_index(drop=True)
        
        # Normalize area for better visualization
        simple_map_data['area_normalized'] = (simple_map_data['area'] / simple_map_data['area'].max()) * 100
        
        st.map(simple_map_data, 
               latitude='latitude',
               longitude='longitude', 
               size='area_normalized',
               color='price')
    
    else:
        # PLOTLY MAP WITH YOUR ORIGINAL COLORS (but no mapbox)
        st.subheader("Property Map with Original Color Scheme")
        
        # Create scatter plot that mimics a map
        fig = px.scatter(df, x='lon', y='lat', 
                        color='price',
                        size='area',
                        hover_data={'lat': ':.6f', 'lon': ':.6f', 'price': ':$,.0f', 'area': ':.0f'},
                        size_max=35,
                        opacity=0.7)
        
        # Apply your original color scheme
        fig.update_coloraxes(colorscale = [
            [0,    'rgb(16, 26, 227)'],      # Blue
            [quintis[0], 'rgb(31, 120, 180)'],  # Light Blue
            [quintis[1], 'rgb(18, 223, 17)'],   # Green
            [quintis[2], 'rgb(255, 234, 44)'],  # Yellow
            [quintis[3], 'rgb(255, 178, 53)'],  # Orange
            [1,    'rgb(227, 26, 28)'],      # Red
        ])
        
        # Style the plot to look more map-like
        fig.update_layout(
            height=500, 
            width=800,
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            template="plotly_dark",
            title="Properties by Location, Price, and Size",
            # Make it look more like a map
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='rgba(128,128,128,0.2)',
                scaleanchor="x",  # Keep aspect ratio
                scaleratio=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Add a color legend for the original scheme
    if map_type == "Plotly Map with Original Colors":
        st.subheader("Price Color Legend")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"🔵 **Lowest 20%**: ${df['price'].quantile(0.0):,.0f} - ${df['price'].quantile(0.2):,.0f}")
        with col2:
            st.markdown(f"🔷 **20-40%**: ${df['price'].quantile(0.2):,.0f} - ${df['price'].quantile(0.4):,.0f}")
        with col3:
            st.markdown(f"🟢 **40-60%**: ${df['price'].quantile(0.4):,.0f} - ${df['price'].quantile(0.6):,.0f}")
        with col4:
            st.markdown(f"🟡 **60-80%**: ${df['price'].quantile(0.6):,.0f} - ${df['price'].quantile(0.8):,.0f}")
        with col5:
            st.markdown(f"🔴 **Top 20%**: ${df['price'].quantile(0.8):,.0f} - ${df['price'].max():,.0f}")
    
    # Display summary statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Properties", len(df))
    with col2:
        st.metric("Average Price", f"${df['price'].mean():,.0f}")
    with col3:
        st.metric("Average Area", f"{df['area'].mean():.0f}")
    
    # Show the filtered data
    st.subheader("Property Details")
    display_df = df[['neighborhood', 'type', 'price', 'area', 'lat', 'lon']].copy()
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:,.0f}")
    display_df['area'] = display_df['area'].apply(lambda x: f"{x:.0f}")
    st.dataframe(display_df, use_container_width=True)
