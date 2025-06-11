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
    
    # Map style choice
    map_style = st.radio("Choose map style:", 
                        ["Basic Map (Simple)", "Colored Map (Fast)", "Colored Map (Full Dataset)"])
    
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
    
    if map_style == "Basic Map (Simple)":
        # OPTION 1: SIMPLE STREAMLIT MAP
        st.subheader("🗺️ Property Locations")
        
        simple_map_data = df[['lat', 'lon', 'area']].copy()
        simple_map_data.columns = ['latitude', 'longitude', 'area']
        simple_map_data = simple_map_data.reset_index(drop=True)
        simple_map_data['size'] = (simple_map_data['area'] / simple_map_data['area'].max()) * 50
        
        st.map(simple_map_data, 
               latitude='latitude',
               longitude='longitude', 
               size='size')
        
        st.write(f"**Price range**: ${df['price'].min():,.0f} - ${df['price'].max():,.0f}")
        st.write(f"**Area range**: {df['area'].min():.0f} - {df['area'].max():.0f}")
    
    elif map_style == "Colored Map (Fast)":
        # OPTION 2: SAMPLED DATA FOR PERFORMANCE
        st.subheader("🌈 Property Map - Sample View (Fast)")
        
        # Sample data if too large (for performance)
        if len(df) > 500:
            sample_size = 500
            df_sample = df.sample(n=sample_size, random_state=42)
            st.info(f"Showing {sample_size} properties (randomly sampled) for better performance")
        else:
            df_sample = df.copy()
            st.info(f"Showing all {len(df_sample)} properties")
        
        # Calculate quintiles from full dataset but plot sample
        full_quintiles = df['price'].quantile([0.2, 0.4, 0.6, 0.8])
        
        # Add color categories to sample data
        def get_color_category(price):
            if price <= full_quintiles[0.2]:
                return 'Lowest 20%'
            elif price <= full_quintiles[0.4]:
                return '20-40%'
            elif price <= full_quintiles[0.6]:
                return '40-60%'
            elif price <= full_quintiles[0.8]:
                return '60-80%'
            else:
                return 'Top 20%'
        
        df_sample['price_category'] = df_sample['price'].apply(get_color_category)
        
        # Create scatter plot with categories
        fig = px.scatter(df_sample, x='lon', y='lat', 
                        color='price_category',
                        size='area',
                        hover_data={
                            'lat': ':.6f', 
                            'lon': ':.6f', 
                            'price': ':$,.0f', 
                            'area': ':.0f',
                            'neighborhood': True,
                            'type': True,
                            'price_category': False
                        },
                        color_discrete_map={
                            'Lowest 20%': 'rgb(16, 26, 227)',      # Blue
                            '20-40%': 'rgb(31, 120, 180)',        # Light Blue
                            '40-60%': 'rgb(18, 223, 17)',         # Green
                            '60-80%': 'rgb(255, 234, 44)',        # Yellow
                            'Top 20%': 'rgb(227, 26, 28)'         # Red
                        },
                        size_max=25,
                        opacity=0.7,
                        title=f"Property Distribution - {len(df_sample)} Properties")
        
        fig.update_layout(
            height=500,
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            template="plotly_dark",
            xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
            yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', scaleanchor="x", scaleratio=1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show legend with actual data from full dataset
        st.subheader("💰 Price Categories (Based on Full Dataset)")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(f"🔵 **Lowest 20%**<br>${df['price'].min():,.0f} - ${full_quintiles[0.2]:,.0f}", unsafe_allow_html=True)
        with col2:
            st.markdown(f"🔷 **20-40%**<br>${full_quintiles[0.2]:,.0f} - ${full_quintiles[0.4]:,.0f}", unsafe_allow_html=True)
        with col3:
            st.markdown(f"🟢 **40-60%**<br>${full_quintiles[0.4]:,.0f} - ${full_quintiles[0.6]:,.0f}", unsafe_allow_html=True)
        with col4:
            st.markdown(f"🟡 **60-80%**<br>${full_quintiles[0.6]:,.0f} - ${full_quintiles[0.8]:,.0f}", unsafe_allow_html=True)
        with col5:
            st.markdown(f"🔴 **Top 20%**<br>${full_quintiles[0.8]:,.0f} - ${df['price'].max():,.0f}", unsafe_allow_html=True)
    
    else:
        # OPTION 3: FULL DATASET (might be slow)
        st.subheader("🌈 Property Map - Full Dataset")
        
        if len(df) > 1000:
            st.warning(f"⚠️ Rendering {len(df)} properties - this might take a moment...")
            
        with st.spinner("Creating detailed map..."):
            # Simplified approach for large datasets
            quintis = (df['price'].describe([.2, .4, .6, .8]).loc[['20%', '40%', '60%', '80%']]\
                    /df['price'].max()).reset_index(drop=True)
            
            # Use discrete colors instead of continuous for better performance
            df_plot = df.copy()
            df_plot['price_normalized'] = (df_plot['price'] - df_plot['price'].min()) / (df_plot['price'].max() - df_plot['price'].min())
            
            # Assign discrete colors
            conditions = [
                df_plot['price_normalized'] <= quintis[0],
                (df_plot['price_normalized'] > quintis[0]) & (df_plot['price_normalized'] <= quintis[1]),
                (df_plot['price_normalized'] > quintis[1]) & (df_plot['price_normalized'] <= quintis[2]),
                (df_plot['price_normalized'] > quintis[2]) & (df_plot['price_normalized'] <= quintis[3]),
                df_plot['price_normalized'] > quintis[3]
            ]
            
            colors = ['#102BE3', '#1F78B4', '#12DF11', '#FFEA2C', '#E31A1C']
            df_plot['color'] = np.select(conditions, colors, default='#102BE3')
            
            # Create plot with Go for better performance
            fig = go.Figure()
            
            for i, color in enumerate(colors):
                mask = df_plot['color'] == color
                subset = df_plot[mask]
                
                if len(subset) > 0:
                    labels = ['Lowest 20%', '20-40%', '40-60%', '60-80%', 'Top 20%']
                    
                    fig.add_trace(go.Scatter(
                        x=subset['lon'],
                        y=subset['lat'],
                        mode='markers',
                        marker=dict(
                            size=subset['area'] / df['area'].max() * 30,
                            color=color,
                            opacity=0.7,
                            sizemode='diameter'
                        ),
                        name=labels[i],
                        text=subset.apply(lambda row: f"Price: ${row['price']:,.0f}<br>Area: {row['area']:.0f}<br>Type: {row['type']}<br>Neighborhood: {row['neighborhood']}", axis=1),
                        hovertemplate='%{text}<extra></extra>'
                    ))
            
            fig.update_layout(
                height=500,
                xaxis_title="Longitude",
                yaxis_title="Latitude",
                template="plotly_dark",
                title=f"All {len(df)} Properties",
                showlegend=True,
                xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', scaleanchor="x", scaleratio=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    # Display summary statistics
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Properties", len(df))
    with col2:
        st.metric("Average Price", f"${df['price'].mean():,.0f}")
    with col3:
        st.metric("Average Area", f"{df['area'].mean():.0f}")
    with col4:
        st.metric("Price Range", f"${df['price'].max() - df['price'].min():,.0f}")
    
    # Show sample of the data
    st.subheader("📋 Sample Property Details")
    display_df = df.head(10)[['neighborhood', 'type', 'price', 'area', 'lat', 'lon']].copy()
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:,.0f}")
    display_df['area'] = display_df['area'].apply(lambda x: f"{x:.0f}")
    st.dataframe(display_df, use_container_width=True)
    
    if len(df) > 10:
        st.info(f"Showing first 10 properties. Total: {len(df)} properties found.")
