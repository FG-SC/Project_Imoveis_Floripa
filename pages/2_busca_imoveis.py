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
    
    # DEBUG: Check if we have data after filtering
    st.write(f"**Debug Info:**")
    st.write(f"- Filtered dataframe shape: {filtered_df.shape}")
    
    if filtered_df.empty:
        st.error("No properties match your criteria. Please adjust your filters.")
        st.stop()
    
    df = filtered_df.copy()
    
    # DEBUG: Check for valid coordinates
    valid_coords = df.dropna(subset=['lat', 'lon'])
    invalid_coords = len(df) - len(valid_coords)
    
    if invalid_coords > 0:
        st.warning(f"Found {invalid_coords} properties with invalid coordinates (will be excluded)")
        df = valid_coords
    
    if df.empty:
        st.error("No properties have valid coordinates.")
        st.stop()
    
    # Check coordinate ranges (reasonable lat/lon for most countries)
    lat_valid = (df['lat'] >= -90) & (df['lat'] <= 90)
    lon_valid = (df['lon'] >= -180) & (df['lon'] <= 180)
    coord_valid = lat_valid & lon_valid
    
    if not coord_valid.all():
        st.warning(f"Found {(~coord_valid).sum()} properties with invalid coordinate ranges")
        df = df[coord_valid]
    
    if df.empty:
        st.error("No properties have valid coordinate ranges.")
        st.stop()
    
    # DEBUG: Show coordinate summary
    st.write(f"- Valid coordinates: {len(df)} properties")
    st.write(f"- Latitude range: {df['lat'].min():.6f} to {df['lat'].max():.6f}")
    st.write(f"- Longitude range: {df['lon'].min():.6f} to {df['lon'].max():.6f}")
    st.write(f"- Price range: {df['price'].min():,.0f} to {df['price'].max():,.0f}")
    st.write(f"- Area range: {df['area'].min():.1f} to {df['area'].max():.1f}")
    
    # Calculate quintiles for color scale
    try:
        quintis = (df['price'].describe([.2, .4, .6, .8]).loc[['20%', '40%', '60%', '80%']] / df['price'].max()).reset_index(drop=True)
        st.write(f"- Price quintiles: {quintis.tolist()}")
    except Exception as e:
        st.error(f"Error calculating quintiles: {e}")
        quintis = [0.2, 0.4, 0.6, 0.8]  # fallback
    
    # Read mapbox token
    try:
        with open('mapbox_token.txt', 'r') as mapbox_api_file:
            mapbox_token = mapbox_api_file.read().strip()
        
        if not mapbox_token:
            st.error("Mapbox token is empty. Please check your mapbox_token.txt file.")
            st.stop()
            
        # Test if token starts with 'pk.' (typical Mapbox token format)
        if not mapbox_token.startswith('pk.'):
            st.warning("Mapbox token doesn't start with 'pk.' - this might be invalid.")
            
    except FileNotFoundError:
        st.error("mapbox_token.txt file not found. Please create this file with your Mapbox token.")
        st.stop()
    except Exception as e:
        st.error(f"Error reading Mapbox token: {e}")
        st.stop()
    
    # Set mapbox token
    px.set_mapbox_access_token(mapbox_token)
    
    # Create the map with better defaults
    try:
        # Add size scaling to make dots more visible
        # Scale area to a reasonable range for map markers
        min_size = 8   # Minimum marker size
        max_size = 50  # Maximum marker size
        
        # Use a simpler color scale first to test
        fig = px.scatter_mapbox(
            df, 
            lat='lat',
            lon='lon', 
            color='price',
            size='area',
            size_max=max_size,
            zoom=12,  # Increased zoom even more for better visibility
            opacity=0.9,  # Increased opacity for better visibility
            hover_data=['type', 'neighborhood', 'price', 'area'],  # Add hover info
            title=f"Real Estate Properties ({len(df)} properties)",
            color_continuous_scale="Viridis"  # Use a built-in scale first to test
        )
        
        # Force minimum marker size
        fig.update_traces(
            marker=dict(
                sizemin=min_size,  # Ensure minimum size
                line=dict(width=1, color='white')  # Add white border for visibility
            )
        )
        
        # Apply custom color scale - fix the quintile issue
        # Create a more evenly distributed color scale
        fig.update_coloraxes(
            colorscale=[
                [0.0, 'rgb(0, 0, 255)'],      # Blue for lowest prices
                [0.2, 'rgb(0, 128, 255)'],    # Light blue
                [0.4, 'rgb(0, 255, 0)'],      # Green
                [0.6, 'rgb(255, 255, 0)'],    # Yellow  
                [0.8, 'rgb(255, 128, 0)'],    # Orange
                [1.0, 'rgb(255, 0, 0)'],      # Red for highest prices
            ],
            colorbar=dict(title="Price (R$)")  # Add colorbar title
        )
        
        # Update layout with better centering
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
        
        fig.update_layout(
            height=600,  # Increased height
            width=1000,  # Increased width
            mapbox=dict(
                center=dict(lat=center_lat, lon=center_lon),
                style="open-street-map"  # Fallback style that doesn't require token
            ),
            template="plotly_dark"
        )
        
        st.write(f"**Map centered at:** Lat: {center_lat:.6f}, Lon: {center_lon:.6f}")
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error creating map: {e}")
        st.write("**Trying alternative map style...**")
        
        # Fallback: try without custom styling
        try:
            fig_simple = px.scatter_mapbox(
                df, 
                lat='lat',
                lon='lon', 
                color='price',
                size='area',
                size_max=35, 
                zoom=10,
                opacity=0.8,
                mapbox_style="open-street-map"  # Use OpenStreetMap (no token needed)
            )
            
            fig_simple.update_layout(height=600, width=1000)
            st.plotly_chart(fig_simple, use_container_width=True)
            
        except Exception as e2:
            st.error(f"Alternative map also failed: {e2}")
            st.write("**Data preview (first 5 rows):**")
            st.write(df[['lat', 'lon', 'price', 'area', 'type', 'neighborhood']].head())
    
    # Show the filtered data
    st.subheader("Filtered Properties")
    st.write(df)
