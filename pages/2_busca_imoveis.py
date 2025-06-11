import streamlit as st
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
    
    st.write(f"Found {len(df)} properties")
    
    # Calculate quintiles
    q20 = df['price'].quantile(0.2)
    q40 = df['price'].quantile(0.4)
    q60 = df['price'].quantile(0.6)
    q80 = df['price'].quantile(0.8)
    
    # Separate data by quintiles
    quintile_1 = df[df['price'] <= q20].copy()  # Lowest 20%
    quintile_2 = df[(df['price'] > q20) & (df['price'] <= q40)].copy()  # 20-40%
    quintile_3 = df[(df['price'] > q40) & (df['price'] <= q60)].copy()  # 40-60%
    quintile_4 = df[(df['price'] > q60) & (df['price'] <= q80)].copy()  # 60-80%
    quintile_5 = df[df['price'] > q80].copy()  # Top 20%
    
    # Define colors and labels (your original scheme)
    colors = ['#102BE3', '#1F78B4', '#12DF11', '#FFEA2C', '#E31A1C']
    labels = ['🔵 Lowest 20%', '🔷 20-40%', '🟢 40-60%', '🟡 60-80%', '🔴 Top 20%']
    quintiles = [quintile_1, quintile_2, quintile_3, quintile_4, quintile_5]
    
    # BEAUTIFUL LAYERED MAP
    st.subheader("🌈 Beautiful Property Map - Layered by Price")
    
    # Create figure
    fig = go.Figure()
    
    # Add each quintile as a separate layer
    for i, (quintile_df, color, label) in enumerate(zip(quintiles, colors, labels)):
        if len(quintile_df) > 0:
            # Calculate size based on area (normalize to 5-25 range)
            sizes = quintile_df['area'] / df['area'].max() * 20 + 5
            
            fig.add_trace(go.Scatter(
                x=quintile_df['lon'],
                y=quintile_df['lat'],
                mode='markers',
                marker=dict(
                    size=sizes,
                    color=color,
                    opacity=0.8,
                    line=dict(width=1, color='white'),  # White border for better definition
                    sizemode='diameter'
                ),
                name=label,
                text=[
                    f"<b>{label}</b><br>" +
                    f"Price: ${price:,.0f}<br>" +
                    f"Area: {area:.0f}<br>" +
                    f"Type: {ptype}<br>" +
                    f"Neighborhood: {neighborhood}"
                    for price, area, ptype, neighborhood in zip(
                        quintile_df['price'], quintile_df['area'], 
                        quintile_df['type'], quintile_df['neighborhood']
                    )
                ],
                hovertemplate='%{text}<extra></extra>',
                showlegend=True
            ))
    
    # Enhance the plot aesthetics
    fig.update_layout(
        height=600,
        width=900,
        title=dict(
            text=f"Property Distribution in Florianópolis<br><sub>Total: {len(df)} properties</sub>",
            x=0.5,
            font=dict(size=20, color='white')
        ),
        xaxis=dict(
            title="Longitude",
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.3)',
            zeroline=False,
            color='white'
        ),
        yaxis=dict(
            title="Latitude", 
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.3)',
            scaleanchor="x",
            scaleratio=1,
            zeroline=False,
            color='white'
        ),
        plot_bgcolor='rgba(20,20,30,1)',  # Dark blue background
        paper_bgcolor='rgba(10,10,15,1)',  # Even darker outer background
        font=dict(color='white'),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(0,0,0,0.5)',
            bordercolor='white',
            borderwidth=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # PRICE DISTRIBUTION LEGEND
    st.subheader("💎 Price Range Details")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    cols = [col1, col2, col3, col4, col5]
    
    for col, quintile_df, color, label in zip(cols, quintiles, colors, labels):
        with col:
            count = len(quintile_df)
            if count > 0:
                avg_price = quintile_df['price'].mean()
                min_price = quintile_df['price'].min()
                max_price = quintile_df['price'].max()
                
                # Create a colored container
                st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, {color}20, {color}40);
                    border-left: 4px solid {color};
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                ">
                    <h4 style="color: {color}; margin: 0;">{label}</h4>
                    <p style="margin: 5px 0; color: white;"><b>{count}</b> properties</p>
                    <p style="margin: 5px 0; color: #ccc; font-size: 12px;">
                        ${min_price:,.0f} - ${max_price:,.0f}<br>
                        Avg: ${avg_price:,.0f}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="
                    background: rgba(128,128,128,0.1);
                    border-left: 4px solid #666;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 10px;
                ">
                    <h4 style="color: #666; margin: 0;">{label}</h4>
                    <p style="margin: 5px 0; color: #666;">No properties</p>
                </div>
                """, unsafe_allow_html=True)
    
    # ALTERNATIVE RELIABLE MAP (Streamlit native)
    st.subheader("🗺️ Reliable Interactive Map")
    
    simple_map_data = df[['lat', 'lon', 'area']].copy()
    simple_map_data.columns = ['latitude', 'longitude', 'area']
    simple_map_data = simple_map_data.reset_index(drop=True)
    simple_map_data['size'] = (simple_map_data['area'] / simple_map_data['area'].max()) * 50
    
    st.map(simple_map_data, 
           latitude='latitude',
           longitude='longitude', 
           size='size')
    
    # SUMMARY STATISTICS
    st.subheader("📊 Summary Statistics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Total Properties", len(df))
    with col2:
        st.metric("Average Price", f"${df['price'].mean():,.0f}")
    with col3:
        st.metric("Median Price", f"${df['price'].median():,.0f}")
    with col4:
        st.metric("Average Area", f"{df['area'].mean():.0f} m²")
    with col5:
        st.metric("Price/m²", f"${(df['price']/df['area']).mean():,.0f}")
    
    # SAMPLE DATA
    st.subheader("📋 Sample Properties")
    
    display_df = df.head(15)[['neighborhood', 'type', 'price', 'area', 'lat', 'lon']].copy()
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:,.0f}")
    display_df['area'] = display_df['area'].apply(lambda x: f"{x:.0f} m²")
    display_df['lat'] = display_df['lat'].apply(lambda x: f"{x:.6f}")
    display_df['lon'] = display_df['lon'].apply(lambda x: f"{x:.6f}")
    
    st.dataframe(display_df, use_container_width=True)
    
    if len(df) > 15:
        st.info(f"Showing first 15 properties out of {len(df)} total properties found.")
