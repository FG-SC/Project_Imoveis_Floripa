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
    
    # Show sample data to verify coordinates
    st.write("**Sample properties:**")
    st.write(df[['lat', 'lon', 'price', 'area', 'type', 'neighborhood']].head())
    
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
    
    # Create the map with FORCED visible markers
    try:
        # FORCE larger, visible markers - ignore area scaling for now
        fig = px.scatter_mapbox(
            df, 
            lat='lat',
            lon='lon', 
            color='price',
            # Remove size parameter temporarily to see if it's causing issues
            zoom=11,
            opacity=1.0,
            hover_data=['type', 'neighborhood', 'price', 'area'],
            title=f"Real Estate Properties ({len(df)} properties)",
            color_continuous_scale="Rainbow"  # Use rainbow colors like your example
        )
        
        # FORCE all markers to be large and visible
        fig.update_traces(
            marker=dict(
                size=20,  # Fixed size for all markers - should be clearly visible
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
        
        # Update layout with dark style like your example
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
        
        fig.update_layout(
            height=600,
            width=1000,
            mapbox=dict(
                center=dict(lat=center_lat, lon=center_lon),
                style="carto-darkmatter"  # Dark background style like your example
            ),
            template="plotly_dark"
        )
        
        st.write(f"**Map centered at:** Lat: {center_lat:.6f}, Lon: {center_lon:.6f}")
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error creating map: {e}")
        st.write("**Trying alternative map style...**")
        
        # Fallback: FORCE visible markers with any map style
        try:
            st.warning("Primary map failed, trying fallback with maximum visibility...")
            
            fig_simple = px.scatter_mapbox(
                df, 
                lat='lat',
                lon='lon', 
                color='price',
                # No size parameter - just force fixed large markers
                zoom=11,
                opacity=1.0,
                mapbox_style="carto-darkmatter",  # Dark style
                color_continuous_scale="Rainbow"
            )
            
            # FORCE large visible markers
            fig_simple.update_traces(
                marker=dict(size=25)  # Even larger fixed size
            )
            fig_simple.update_layout(height=600, width=1000)
            st.plotly_chart(fig_simple, use_container_width=True)
            
        except Exception as e2:
            st.error(f"Fallback map also failed: {e2}")
            
            # LAST RESORT: Try with open street map and huge markers
            try:
                st.warning("Trying final fallback with OpenStreetMap...")
                fig_final = px.scatter_mapbox(
                    df, 
                    lat='lat',
                    lon='lon', 
                    color='price',
                    zoom=11,
                    opacity=1.0,
                    mapbox_style="open-street-map",
                    color_continuous_scale="Rainbow"
                )
                
                # MASSIVE markers that can't be missed
                fig_final.update_traces(marker=dict(size=30))
                fig_final.update_layout(height=600, width=1000)
                st.plotly_chart(fig_final, use_container_width=True)
                
            except Exception as e3:
                st.error(f"All map attempts failed: {e3}")
                # Show raw data for debugging
                st.write("**Raw coordinate data:**")
                st.write(df[['lat', 'lon', 'price', 'area']].head(10))
            st.plotly_chart(fig_simple, use_container_width=True)
            
        except Exception as e2:
            st.error(f"All map attempts failed: {e3}")
                # Show raw data for debugging
                st.write("**Raw coordinate data:**")
                st.write(df[['lat', 'lon', 'price', 'area']].head(10))
    
    # Show the data
    st.subheader("Properties Data")
    st.write(df)
