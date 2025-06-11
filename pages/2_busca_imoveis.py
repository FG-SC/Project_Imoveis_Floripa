import streamlit as st
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
    
    # Calculate price quintiles for color categorization
    q20 = df['price'].quantile(0.2)
    q40 = df['price'].quantile(0.4)
    q60 = df['price'].quantile(0.6)
    q80 = df['price'].quantile(0.8)
    
    # Categorize properties by price
    df['price_category'] = pd.cut(df['price'], 
                                 bins=[df['price'].min()-1, q20, q40, q60, q80, df['price'].max()],
                                 labels=['🔵 Lowest 20%', '🔷 20-40%', '🟢 40-60%', '🟡 60-80%', '🔴 Top 20%'])
    
    # MAIN MAP - All properties
    st.subheader("🗺️ All Properties")
    
    simple_map_data = df[['lat', 'lon', 'area']].copy()
    simple_map_data.columns = ['latitude', 'longitude', 'area']
    simple_map_data = simple_map_data.reset_index(drop=True)
    simple_map_data['size'] = (simple_map_data['area'] / simple_map_data['area'].max()) * 50
    
    st.map(simple_map_data, 
           latitude='latitude',
           longitude='longitude', 
           size='size')
    
    # COLOR-CODED BREAKDOWN
    st.subheader("🌈 Properties by Price Range")
    
    # Create tabs for each price category
    categories = ['🔵 Lowest 20%', '🔷 20-40%', '🟢 40-60%', '🟡 60-80%', '🔴 Top 20%']
    tab1, tab2, tab3, tab4, tab5 = st.tabs(categories)
    
    tabs = [tab1, tab2, tab3, tab4, tab5]
    
    for i, (tab, category) in enumerate(zip(tabs, categories)):
        with tab:
            category_df = df[df['price_category'] == category].copy()
            
            if len(category_df) > 0:
                st.write(f"**{len(category_df)} properties** in this price range")
                st.write(f"**Price range**: ${category_df['price'].min():,.0f} - ${category_df['price'].max():,.0f}")
                st.write(f"**Average price**: ${category_df['price'].mean():,.0f}")
                
                # Create map for this category
                cat_map_data = category_df[['lat', 'lon', 'area']].copy()
                cat_map_data.columns = ['latitude', 'longitude', 'area']
                cat_map_data = cat_map_data.reset_index(drop=True)
                cat_map_data['size'] = (cat_map_data['area'] / df['area'].max()) * 50  # Use global max for consistency
                
                st.map(cat_map_data, 
                       latitude='latitude',
                       longitude='longitude', 
                       size='size')
                
                # Show sample properties in this category
                st.write("**Sample properties:**")
                sample_display = category_df.head(5)[['neighborhood', 'type', 'price', 'area']].copy()
                sample_display['price'] = sample_display['price'].apply(lambda x: f"${x:,.0f}")
                sample_display['area'] = sample_display['area'].apply(lambda x: f"{x:.0f}")
                st.dataframe(sample_display, use_container_width=True)
            else:
                st.write("No properties in this price range")
    
    # SUMMARY SECTION
    st.subheader("📊 Price Distribution Summary")
    
    # Create columns for each category with counts and percentages
    col1, col2, col3, col4, col5 = st.columns(5)
    cols = [col1, col2, col3, col4, col5]
    
    for col, category in zip(cols, categories):
        with col:
            count = len(df[df['price_category'] == category])
            percentage = (count / len(df)) * 100
            min_price = df[df['price_category'] == category]['price'].min() if count > 0 else 0
            max_price = df[df['price_category'] == category]['price'].max() if count > 0 else 0
            
            st.metric(
                label=category,
                value=f"{count} properties",
                delta=f"{percentage:.1f}%"
            )
            if count > 0:
                st.caption(f"${min_price:,.0f} - ${max_price:,.0f}")
    
    # OVERALL STATISTICS
    st.subheader("📈 Overall Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Properties", len(df))
    with col2:
        st.metric("Average Price", f"${df['price'].mean():,.0f}")
    with col3:
        st.metric("Median Price", f"${df['price'].median():,.0f}")
    with col4:
        st.metric("Average Area", f"{df['area'].mean():.0f}")
    
    # PRICE HISTOGRAM (simple bar chart)
    st.subheader("📊 Price Distribution")
    
    price_ranges = df['price_category'].value_counts().sort_index()
    st.bar_chart(price_ranges)
    
    # SAMPLE DATA TABLE
    st.subheader("📋 Sample Properties")
    display_df = df.head(10)[['neighborhood', 'type', 'price', 'area', 'price_category']].copy()
    display_df['price'] = display_df['price'].apply(lambda x: f"${x:,.0f}")
    display_df['area'] = display_df['area'].apply(lambda x: f"{x:.0f}")
    st.dataframe(display_df, use_container_width=True)
    
    if len(df) > 10:
        st.info(f"Showing first 10 properties. Total: {len(df)} properties found.")
