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

st.title("Busca imóveis - DEBUG VERSION")

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
    
    st.header("🔍 DEBUGGING INFORMATION")
    
    # DEBUG 1: Check basic data
    st.subheader("1. Data Overview")
    st.write(f"**Total properties after filtering:** {len(filtered_df)}")
    st.write(f"**Original dataset size:** {len(imoveis_df)}")
    
    if len(filtered_df) == 0:
        st.error("❌ NO DATA AFTER FILTERING!")
        st.stop()
    
    # DEBUG 2: Check coordinates
    st.subheader("2. Coordinate Analysis")
    missing_lat = filtered_df['lat'].isna().sum()
    missing_lon = filtered_df['lon'].isna().sum()
    
    st.write(f"**Missing latitude values:** {missing_lat}")
    st.write(f"**Missing longitude values:** {missing_lon}")
    st.write(f"**Latitude range:** {filtered_df['lat'].min():.6f} to {filtered_df['lat'].max():.6f}")
    st.write(f"**Longitude range:** {filtered_df['lon'].min():.6f} to {filtered_df['lon'].max():.6f}")
    
    # Check if coordinates are in valid range for Brazil
    valid_lat = ((filtered_df['lat'] >= -35) & (filtered_df['lat'] <= 5)).sum()
    valid_lon = ((filtered_df['lon'] >= -75) & (filtered_df['lon'] <= -30)).sum()
    st.write(f"**Properties with valid Brazil coordinates:** Lat: {valid_lat}/{len(filtered_df)}, Lon: {valid_lon}/{len(filtered_df)}")
    
    # DEBUG 3: Check price and area data
    st.subheader("3. Price and Area Analysis")
    st.write(f"**Price range:** ${filtered_df['price'].min():,.0f} to ${filtered_df['price'].max():,.0f}")
    st.write(f"**Area range:** {filtered_df['area'].min():.1f} to {filtered_df['area'].max():.1f}")
    st.write(f"**Price data type:** {filtered_df['price'].dtype}")
    st.write(f"**Area data type:** {filtered_df['area'].dtype}")
    
    # Clean the data
    df = filtered_df.copy()
    df = df.dropna(subset=['lat', 'lon', 'price', 'area'])
    
    st.write(f"**Properties after removing NaN values:** {len(df)}")
    
    if len(df) == 0:
        st.error("❌ NO VALID DATA AFTER CLEANING!")
        st.stop()
    
    # DEBUG 4: Show sample data
    st.subheader("4. Sample Data")
    st.write(df[['lat', 'lon', 'price', 'area']].head())
    
    # DEBUG 5: Test different map approaches
    st.header("🗺️ MAP TESTING")
    
    # Test 1: Simple map without color/size
    st.subheader("Test 1: Basic Scatter Map (No Color/Size)")
    try:
        fig_basic = px.scatter_mapbox(df, lat='lat', lon='lon',
                                    zoom=9,
                                    mapbox_style="open-street-map")
        fig_basic.update_layout(height=400, width=600)
        st.plotly_chart(fig_basic)
        st.success("✅ Basic map works!")
    except Exception as e:
        st.error(f"❌ Basic map failed: {e}")
    
    # Test 2: Map with color only
    st.subheader("Test 2: Map with Color Only")
    try:
        fig_color = px.scatter_mapbox(df, lat='lat', lon='lon', 
                                    color='price',
                                    zoom=9,
                                    mapbox_style="open-street-map")
        fig_color.update_layout(height=400, width=600)
        st.plotly_chart(fig_color)
        st.success("✅ Color map works!")
    except Exception as e:
        st.error(f"❌ Color map failed: {e}")
    
    # Test 3: Map with size only
    st.subheader("Test 3: Map with Size Only")
    try:
        fig_size = px.scatter_mapbox(df, lat='lat', lon='lon', 
                                   size='area',
                                   zoom=9,
                                   mapbox_style="open-street-map")
        fig_size.update_layout(height=400, width=600)
        st.plotly_chart(fig_size)
        st.success("✅ Size map works!")
    except Exception as e:
        st.error(f"❌ Size map failed: {e}")
    
    # Test 4: Your original map with higher opacity
    st.subheader("Test 4: Full Map (High Opacity)")
    try:
        quintis = (df['price'].describe([.2, .4, .6, .8]).loc[['20%', '40%', '60%', '80%']]\
                /df['price'].max()).reset_index(drop=True)
        
        fig_full = px.scatter_mapbox(df, lat='lat', lon='lon', color='price',
                            size='area',
                            size_max=35, 
                            zoom=9, 
                            opacity=0.8,  # Higher opacity!
                            mapbox_style="open-street-map")
        
        fig_full.update_coloraxes(colorscale = [
            [0,    'rgb(16, 26, 227)'],  # Removed alpha
            [quintis[0], 'rgb(31, 120, 180)'],
            [quintis[1], 'rgb(18, 223, 17)'],
            [quintis[2],  'rgb(255, 234, 44)'],
            [quintis[3], 'rgb(255, 178, 53)'],
            [1,    'rgb(227, 26, 28)'],
        ])
        
        fig_full.update_layout(height=500, width=800, 
                         mapbox=dict(center=go.layout.mapbox.Center(
                             lat=df['lat'].mean(), 
                             lon=df['lon'].mean())),
                         template="plotly_dark")
        
        st.plotly_chart(fig_full)
        st.success("✅ Full map works!")
    except Exception as e:
        st.error(f"❌ Full map failed: {e}")
        st.write("Error details:", str(e))
    
    # Show final cleaned data
    st.subheader("5. Final Cleaned Data")
    st.write(df)
