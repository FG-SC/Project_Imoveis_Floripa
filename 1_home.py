import streamlit as st
import requests
import pandas as pd
import numpy as np
import unicodedata
import re
import random
from math import ceil
import time
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import plotly.express as px
import warnings

# Suppress specific warnings
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)

# Dicionários de mapeamento conforme especificado no prompt
ESTADOS_BRASIL = {
    'Acre': 'ac', 'Alagoas': 'al', 'Amapá': 'ap', 'Amazonas': 'am', 'Bahia': 'ba', 
    'Ceará': 'ce', 'Distrito Federal': 'df', 'Espírito Santo': 'es', 'Goiás': 'go', 
    'Maranhão': 'ma', 'Mato Grosso': 'mt', 'Mato Grosso do Sul': 'ms', 'Minas Gerais': 'mg', 
    'Pará': 'pa', 'Paraíba': 'pb', 'Paraná': 'pr', 'Pernambuco': 'pe', 'Piauí': 'pi', 
    'Rio de Janeiro': 'rj', 'Rio Grande do Norte': 'rn', 'Rio Grande do Sul': 'rs', 
    'Rondônia': 'ro', 'Roraima': 'rr', 'Santa Catarina': 'sc', 'São Paulo': 'sp', 
    'Sergipe': 'se', 'Tocantins': 'to'
}

TIPOS_IMOVEIS = {
    'Apartamentos': 'apartamentos',
    'Casas': 'casas',
    'Casas em Condomínio': 'casas-em-condominio',
    'Kitnets e Estúdios': 'kitnet',
    'Flats': 'flat',
    'Coberturas': 'coberturas',
    'Lofts': 'loft',
    'Chácaras': 'chacaras',
    'Terrenos': 'terrenos',
    'Terrenos em Condomínio': 'terrenos-em-condominio'
}

TIPOS_TRANSACAO = {
    'Venda': 'a-venda',
    'Aluguel': 'para-alugar'
}

# Dicionário corrigido conforme especificações
FILTRO_TIPO_IMOVEL_ID = {
    'Apartamento': 1,
    'Casas & Sobrados': 4,
    'Casa em condomínio': 25,
    'Kitnets & Estúdios': 16,
    'Flat': 10,
    'Loft': 13,
    'Cobertura': 20,
    'Sítios & Chácaras': 5,
    'Terreno/Lote': 18,
    'Terreno em condomínio': 26,
}

# Enhanced User-Agent rotation for better scraping reliability
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
]

def get_random_user_agent():
    """Returns a random User-Agent string from the predefined list."""
    return random.choice(USER_AGENTS)

def get_cities(imovel='apartamentos', transacao='a-venda', estado='sc'):
    """
    Função para buscar cidades disponíveis conforme especificado no prompt.
    """
    headers = {
        'accept': '*/*', 'accept-language': 'en-US,en;q=0.5',
        'referer': f'https://www.chavesnamao.com.br/{imovel}-{transacao}/{estado}/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    params = {
        'viewport': 'desktop', 'prerender': 'true',
        'level1': f'{imovel}-{transacao}', 'level2': f'{estado}', 'limit': '150',
    }
    try:
        response = requests.get(
            'https://www.chavesnamao.com.br/api/realestate/aggregations/navigationFilters/',
            params=params, headers=headers, timeout=10
        )
        response.raise_for_status()
        data = response.json().get('data', {}).get('items', [])
        if not data:
            return pd.DataFrame(columns=['title'])
        df = pd.DataFrame(data)
        return df[['title']]
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar cidades: {e}")
        return pd.DataFrame(columns=['title'])

def clean_portuguese_name(name):
    """
    Enhanced function to normalize and clean Portuguese names for URL formatting.
    Handles multi-word city names and special characters more robustly.
    """
    if not isinstance(name, str):
        return ""
    
    # Normalize unicode characters (removes accents)
    normalized_name = unicodedata.normalize('NFKD', name)
    
    # Convert to ASCII, removing any remaining special characters
    cleaned_name = normalized_name.encode('ascii', 'ignore').decode('utf-8')
    
    # Convert to lowercase
    cleaned_name = cleaned_name.lower()
    
    # Replace spaces with hyphens
    cleaned_name = cleaned_name.replace(' ', '-')
    
    # Remove any characters that aren't letters, numbers, or hyphens
    cleaned_name = re.sub(r'[^a-z0-9-]+', '', cleaned_name)
    
    # Replace multiple consecutive hyphens with single hyphen
    cleaned_name = re.sub(r'-+', '-', cleaned_name)
    
    # Remove leading/trailing hyphens
    cleaned_name = cleaned_name.strip('-')
    
    return cleaned_name

def call_navigation_filters_api(level1, level2, level3=None):
    """
    CORRECTED: Makes a call to the navigationFilters API endpoint ONLY.
    This endpoint is used for:
    1. Getting city structure (zones/neighborhoods) - without level3
    2. Getting neighborhoods from a specific zone - with level3=zone_url
    """
    headers = {'User-Agent': get_random_user_agent()}
    
    url = f'https://www.chavesnamao.com.br/api/realestate/aggregations/navigationFilters/?viewport=desktop&level1={level1}&level2={level2}'
    if level3:
        # Extract clean level3 value from URL
        level3_clean = level3.strip('/').split('/')[-1]
        url += f"&level3={level3_clean}"
    
    # Debug: Show the URL being called
    if level3:
        st.write(f"  🔗 Buscando bairros da zona: {level3.strip('/').split('/')[-1]}")
    else:
        st.write(f"  🔗 Verificando estrutura da cidade...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Check if response is valid JSON
        try:
            json_data = response.json()
        except ValueError as e:
            st.warning(f"Resposta da API não é JSON válido: {e}")
            return pd.DataFrame()
        
        data = json_data.get('data', {}).get('items', [])
        
        if not data:
            st.write(f"  🔭 Nenhum item encontrado")
            return pd.DataFrame()
        
        # Debug: Show count of items returned
        st.write(f"  📦 {len(data)} itens encontrados")
        
        df = pd.DataFrame(data)
        
        # Remove parents column to avoid processing issues
        if 'parents' in df.columns:
            df = df.drop(columns=['parents'])
        
        return df
            
    except requests.exceptions.Timeout:
        st.warning(f"Timeout na chamada da API")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        st.warning(f"Erro na chamada da API: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Erro inesperado: {e}")
        return pd.DataFrame()

def get_neighborhoods_from_zone(state, city, property_type, transaction, zone_url):
    """
    CORRECTED: Gets neighborhoods from a specific zone using the navigationFilters API.
    This function implements the correct logic for zone-based cities.
    """
    level1 = f"{property_type}-{transaction}"
    level2 = f"{state.lower()}-{clean_portuguese_name(city)}"
    
    # CRITICAL: Use the navigationFilters endpoint with level3=zone_url
    neighborhoods_df = call_navigation_filters_api(level1, level2, zone_url)
    
    if neighborhoods_df.empty:
        return pd.DataFrame()
    
    # Filter for valid neighborhoods with ads
    if 'adsCount' in neighborhoods_df.columns and not neighborhoods_df['adsCount'].isna().all():
        neighborhoods_filtered = neighborhoods_df[neighborhoods_df['adsCount'] > 0].copy()
        if not neighborhoods_filtered.empty:
            return neighborhoods_filtered
    
    # Fallback: return all items if no adsCount filtering worked
    return neighborhoods_df

def get_ads(state, city, property_type, transaction, neighborhood_url, page=1, subtipo_ids=None):
    """
    CORRECTED: Fetches ads from a specific neighborhood using the listing API ONLY.
    This is the ONLY function that should use the listing/items endpoint.
    """
    headers = {'User-Agent': get_random_user_agent()}
    
    level1 = f"{property_type}-{transaction}"
    level2 = f"{state.lower()}-{clean_portuguese_name(city)}"
    
    # CRITICAL: Extract only the neighborhood name from the URL
    # Remove zone prefixes like "zona-oeste/" to get just the neighborhood
    neighborhood_clean = neighborhood_url.strip('/').split('/')[-1]
    
    # CORRECTED: Use the LISTING API endpoint (not navigationFilters) for ads
    url = (f'https://www.chavesnamao.com.br/api/realestate/listing/items/?'
           f'level1={level1}&'
           f'level2={level2}&'
           f'level3={neighborhood_clean}&'
           f'pg={page}&'
           f'viewport=desktop')
    
    # Add subtipo filter if provided
    if subtipo_ids and len(subtipo_ids) > 0:
        filtro_param = '+'.join(subtipo_ids)
        url += f"&filtro=tim:[{filtro_param}]"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return format_json_to_df(response)
    except requests.exceptions.RequestException as e:
        if page == 1:  # Only show warning for first page
            st.warning(f"Erro ao buscar anúncios de {neighborhood_clean}, página {page}: {e}")
        return pd.DataFrame()

def get_all_neighborhoods(state, city, property_type, transaction):
    """
    CORRECTED: Implements the exact two-stage collection logic as specified.
    
    Stage 1: Check city structure using navigationFilters API (without level3)
    Stage 2a: If zones exist, collect neighborhoods from each zone using navigationFilters API (with level3=zone)
    Stage 2b: If no zones, return direct neighborhoods from stage 1
    """
    
    # Stage 1: Initial call to detect city structure
    st.info("🔍 Etapa 1: Verificando estrutura da cidade...")
    
    level1 = f"{property_type}-{transaction}"
    level2 = f"{state.lower()}-{clean_portuguese_name(city)}"
    
    # STEP 1: Call navigationFilters API without level3
    initial_df = call_navigation_filters_api(level1, level2)
    
    if initial_df.empty:
        st.error("❌ Nenhum dado retornado para a cidade especificada.")
        return pd.DataFrame()
    
    # Debug: Show what we found
    if 'category' in initial_df.columns:
        categories = initial_df['category'].value_counts()
        st.write(f"📋 Categorias encontradas: {dict(categories)}")
        
        # Show sample data for debugging
        with st.expander("🔍 Debug: Dados da chamada inicial"):
            display_cols = ['name', 'url', 'category', 'adsCount'] if all(col in initial_df.columns for col in ['name', 'url', 'category', 'adsCount']) else initial_df.columns.tolist()
            st.dataframe(initial_df[display_cols].head(10))
    
    # STEP 2: Check if city has zone-based structure
    has_zones = False
    if 'category' in initial_df.columns:
        has_zones = initial_df['category'].str.lower().str.contains('zona', na=False).any()
    
    if has_zones:
        # IF: ZONE-BASED CITY - Two-stage process
        st.success("🏙️ Cidade com estrutura de zonas detectada!")
        st.info("🔄 Etapa A: Coletando bairros de cada zona")
        
        # Get all zones from initial call
        zones_df = initial_df[initial_df['category'].str.lower().str.contains('zona', na=False)].copy()
        
        # Filter zones with ads if possible
        if 'adsCount' in zones_df.columns and not zones_df['adsCount'].isna().all():
            zones_with_ads = zones_df[zones_df['adsCount'] > 0]
            if not zones_with_ads.empty:
                zones_df = zones_with_ads
                st.write(f"🎯 Filtrando para {len(zones_df)} zonas com anúncios")
        
        if zones_df.empty:
            st.warning("⚠️ Nenhuma zona encontrada.")
            return pd.DataFrame()
        
        st.write(f"🗺️ Processando {len(zones_df)} zonas")
        
        # ETAPA A: Collect neighborhoods from each zone
        all_neighborhoods = []
        
        for idx, zone_row in zones_df.iterrows():
            zone_url = zone_row['url']
            zone_name = zone_row.get('name', zone_url)
            zone_ads = zone_row.get('adsCount', 'N/A')
            
            st.write(f"📍 Zona: {zone_name} ({zone_ads} anúncios)")
            
            # CRITICAL: Use the corrected function that calls navigationFilters with level3
            neighborhoods_df = get_neighborhoods_from_zone(state, city, property_type, transaction, zone_url)
            
            if not neighborhoods_df.empty:
                # Filter for neighborhoods with adsCount > 0 as specified
                if 'adsCount' in neighborhoods_df.columns:
                    neighborhoods_filtered = neighborhoods_df[neighborhoods_df['adsCount'] > 0].copy()
                    if not neighborhoods_filtered.empty:
                        neighborhoods_df = neighborhoods_filtered
                        st.write(f"  🎯 Filtrando para {len(neighborhoods_df)} bairros com anúncios")
                
                if not neighborhoods_df.empty:
                    # Add zone metadata
                    neighborhoods_df['zone_name'] = zone_name
                    neighborhoods_df['zone_url'] = zone_url
                    
                    all_neighborhoods.append(neighborhoods_df)
                    st.write(f"  ✅ {len(neighborhoods_df)} bairros coletados")
                    
                else:
                    st.write(f"  ⚠️ Nenhum bairro com anúncios nesta zona")
            else:
                st.write(f"  ❌ Nenhum bairro encontrado nesta zona")
            
            # Rate limiting
            time.sleep(0.8)
        
        # Combine all neighborhoods from all zones
        if all_neighborhoods:
            final_neighborhoods = pd.concat(all_neighborhoods, ignore_index=True)
            st.success(f"✅ Etapa A concluída: {len(final_neighborhoods)} bairros coletados de {len(zones_df)} zonas")
            
            # Show summary
            with st.expander("📊 Resumo dos bairros por zona"):
                if 'zone_name' in final_neighborhoods.columns:
                    summary = final_neighborhoods.groupby('zone_name').size().reset_index(name='neighborhoods_count')
                    st.dataframe(summary)
            
            return final_neighborhoods
        else:
            st.error("❌ Nenhum bairro encontrado em qualquer zona.")
            return pd.DataFrame()
    
    else:
        # ELSE: DIRECT NEIGHBORHOOD CITY - One-stage process
        st.success("🏘️ Cidade com bairros diretos detectada!")
        
        # Filter for neighborhoods
        neighborhoods_df = initial_df.copy()
        
        # Try filtering by category if available
        if 'category' in initial_df.columns:
            potential_neighborhoods = initial_df[
                initial_df['category'].str.lower().str.contains('neighborhood', na=False)
            ].copy()
            if not potential_neighborhoods.empty:
                neighborhoods_df = potential_neighborhoods
        
        # Filter by adsCount > 0 if available
        if 'adsCount' in neighborhoods_df.columns:
            neighborhoods_with_ads = neighborhoods_df[neighborhoods_df['adsCount'] > 0].copy()
            if not neighborhoods_with_ads.empty:
                neighborhoods_df = neighborhoods_with_ads
                st.write(f"🎯 Filtrando para {len(neighborhoods_df)} bairros com anúncios")
        
        if not neighborhoods_df.empty:
            st.success(f"✅ {len(neighborhoods_df)} bairros encontrados")
        else:
            st.warning("⚠️ Nenhum bairro encontrado.")
        
        return neighborhoods_df

def format_json_to_df(response_obj):
    """MODIFICADO: Formata a resposta JSON da API em um DataFrame pandas e captura property_url + condominium value."""
    items_data = response_obj.json().get('items', [])
    if not items_data:
        return pd.DataFrame()
    
    df = pd.json_normalize(items_data)
    
    rename_map = {
        'area.total': 'area_total', 'area.useful': 'area_useful',
        'bathrooms.count': 'bathrooms_count', 'bedrooms.count': 'bedrooms_count',
        'garages.count': 'garages_count', 'suites.count': 'suites_count',
        'prices.iptuValue': 'prices_iptuValue', 'prices.main': 'prices_main',
        'prices.rawPrice': 'prices_rawPrice', 'prices.condominiumFee': 'prices_condominiumValue',
        'location.neighborhood.name': 'location_neighborhood_name',
        'realtyType.name': 'realtyType_name', 'location.city.name': 'location_city_name',
        'location.state.acronym': 'location_state_acronym',
        'location.geoposition.lat': 'lat', 'location.geoposition.lon': 'lon'
    }
    df.rename(columns=rename_map, inplace=True)
    
    # MODIFICAÇÃO: Capturar URL do imóvel para recomendações
    if 'url' in df.columns:
        df['property_url'] = df['url']
    else:
        df['property_url'] = np.nan
    
    essential_cols = list(rename_map.values()) + ['id', 'privativeItems', 'commonItems', 'property_url']
    for col in essential_cols:
        if col not in df.columns:
            df[col] = np.nan
            
    return df

def calculate_adjusted_price_per_sqm(df, transaction_type):
    """
    Calcula o preço por m² de forma inteligente, considerando o tipo de transação.
    Para aluguéis, soma o aluguel, condomínio e IPTU.
    """
    df_copy = df.copy()

    # Garantir que colunas de custo extra existam e preencher NaNs com 0
    if 'prices_condominiumValue' not in df_copy.columns:
        df_copy['prices_condominiumValue'] = 0
    if 'prices_iptuValue' not in df_copy.columns:
        df_copy['prices_iptuValue'] = 0
        
    df_copy['prices_condominiumValue'].fillna(0, inplace=True)
    df_copy['prices_iptuValue'].fillna(0, inplace=True)

    # Lógica condicional
    if transaction_type == 'para-alugar':
        # Custo total mensal = aluguel + condomínio + IPTU
        total_monthly_cost = df_copy['prices_rawPrice'] + df_copy['prices_condominiumValue'] + df_copy['prices_iptuValue']
        df_copy['preco_m2'] = total_monthly_cost / df_copy['area_useful']
    else: # para 'a-venda'
        df_copy['preco_m2'] = df_copy['prices_rawPrice'] / df_copy['area_useful']
    
    # Substituir infinitos ou NaNs resultantes de divisão por zero
    df_copy['preco_m2'].replace([np.inf, -np.inf], np.nan, inplace=True)
    df_copy['preco_m2'].fillna(0, inplace=True)
    
    return df_copy

def find_similar_properties(user_input, all_data, top_n=3):
    """NOVA FUNÇÃO: Encontra imóveis similares baseado nas características do usuário."""
    if all_data is None or all_data.empty:
        return pd.DataFrame()
    
    # Filtrar por bairro e tipo de imóvel
    filtered_df = all_data[
        (all_data['location_neighborhood_name'] == user_input['bairro']) &
        (all_data['realtyType_name'] == user_input['tipo_imovel'])
    ].copy()
    
    if filtered_df.empty:
        return pd.DataFrame()
    
    # Calcular score de similaridade
    def calculate_similarity_score(row):
        score = 0
        # Área útil (peso base)
        if pd.notna(row['area_useful']) and user_input['area_useful'] > 0:
            score += abs(row['area_useful'] - user_input['area_useful'])
        
        # Quartos (peso alto)
        if pd.notna(row['bedrooms_count']):
            score += abs(row['bedrooms_count'] - user_input['bedrooms_count']) * 10
        
        # Banheiros (peso médio)  
        if pd.notna(row['bathrooms_count']):
            score += abs(row['bathrooms_count'] - user_input['bathrooms_count']) * 5
        
        # Garagens (peso médio)
        if pd.notna(row['garages_count']):
            score += abs(row['garages_count'] - user_input['garages_count']) * 5
        
        return score
    
    filtered_df['similarity_score'] = filtered_df.apply(calculate_similarity_score, axis=1)
    
    # Ordenar por similaridade (menor score = mais similar)
    similar_properties = filtered_df.sort_values('similarity_score').head(top_n)
    
    return similar_properties

def process_features(df):
    """
    Processa e cria features booleanas para 'privativeItems' e 'commonItems'.
    Usa uma abordagem mais eficiente para evitar warnings de performance.
    """
    df_processed = df.copy()

    def get_item_names(items_list):
        if not isinstance(items_list, list): 
            return set()
        names = set()
        for item in items_list:
            if isinstance(item, dict) and 'name' in item:
                names.add(item['name'])
        return names

    df_processed['_privative_set'] = df_processed['privativeItems'].apply(get_item_names)
    df_processed['_common_set'] = df_processed['commonItems'].apply(get_item_names)
    
    # Collect all unique features
    all_features = set()
    for s in df_processed['_privative_set']: 
        all_features.update(s)
    for s in df_processed['_common_set']: 
        all_features.update(s)
    
    # Create feature columns more efficiently using pd.concat
    feature_cols = []
    feature_data = {}
    
    for feature in sorted(list(all_features)):
        col_name = 'feature_' + clean_portuguese_name(feature)
        
        # Verificar se a coluna já existe antes de criar
        if col_name not in feature_data and col_name not in df_processed.columns:
            feature_cols.append(col_name)
            
            # Create feature column data
            feature_data[col_name] = df_processed.apply(
                lambda row: 1 if feature in row['_privative_set'] or feature in row['_common_set'] else 0,
                axis=1
            )
    
    # Add all feature columns at once using pd.concat to avoid performance warning
    if feature_data:
        features_df = pd.DataFrame(feature_data, index=df_processed.index)
        df_processed = pd.concat([df_processed, features_df], axis=1)
    
    # Clean up temporary columns
    df_processed.drop(columns=['privativeItems', 'commonItems', '_privative_set', '_common_set'], inplace=True)
    
    return df_processed, feature_cols

def calculate_mape(y_true, y_pred):
    """
    Calculate Mean Absolute Percentage Error (MAPE).
    Handles division by zero by filtering out zero values in y_true.
    """
    # Convert to numpy arrays for safety
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    # Filter out samples where y_true is zero to avoid division by zero
    mask = y_true != 0
    if mask.sum() == 0:
        return np.nan  # Return NaN if all true values are zero
    
    y_true_filtered = y_true[mask]
    y_pred_filtered = y_pred[mask]
    
    mape = np.mean(np.abs((y_true_filtered - y_pred_filtered) / y_true_filtered)) * 100
    return mape

def clean_currency_string(value):
    """
    Converte uma string de moeda (ex: 'R$ 1.500,50') para float.
    Retorna 0.0 se a conversão falhar.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            # Remove 'R$', espaços, e o separador de milhares '.'
            # Substitui a vírgula decimal por um ponto
            cleaned_value = value.replace('R$', '').strip().replace('.', '').replace(',', '.')
            return float(cleaned_value)
        except (ValueError, TypeError):
            return 0.0
    return 0.0

def clean_data(df):
    """
    Limpa o DataFrame final antes do treinamento e plotagem.
    Implementa tratamento robusto para valores monetários.
    """
    df_cleaned = df.copy()
    
    # Colunas monetárias que precisam de limpeza especial
    currency_cols = ['prices_rawPrice', 'prices_condominiumValue', 'prices_iptuValue']
    
    for col in currency_cols:
        if col in df_cleaned.columns:
            # Aplicar a função de limpeza de string ANTES da conversão numérica
            df_cleaned[col] = df_cleaned[col].apply(clean_currency_string)

    # Definir colunas numéricas que devem existir
    expected_numeric_cols = ['area_total', 'area_useful', 'bathrooms_count', 'bedrooms_count', 
                           'garages_count', 'suites_count', 'prices_rawPrice', 'lat', 'lon',
                           'prices_condominiumValue', 'prices_iptuValue']
    
    # Converter para numérico, tratando colunas ausentes
    for col in expected_numeric_cols:
        if col in df_cleaned.columns:
            df_cleaned[col] = pd.to_numeric(df_cleaned[col], errors='coerce')
        else:
            df_cleaned[col] = np.nan

    # Drop de linhas com dados essenciais faltando
    essential_cols = ['prices_rawPrice', 'area_useful']

    df_cleaned.dropna(subset=essential_cols, inplace=True)
    
    # Remoção de outliers
    outlier_cols = ['prices_rawPrice', 'area_useful', 'lat', 'lon']
    for col in outlier_cols:
        if col in df_cleaned.columns and not df_cleaned[col].empty:
            q_low = df_cleaned[col].quantile(0.0001)
            q_high = df_cleaned[col].quantile(0.9999)
            df_cleaned = df_cleaned[(df_cleaned[col] >= q_low) & (df_cleaned[col] <= q_high)]
        
    return df_cleaned

def plot_geo_data(df):
    """
    Plota os imóveis em um mapa georreferenciado com centralização dinâmica.
    Usa scatter_map (nova função) em vez da obsoleta scatter_mapbox.
    """
    df_plot = df.copy()
    
    # Check if we have the required columns
    if 'lat' not in df_plot.columns or 'lon' not in df_plot.columns:
        st.warning("Dados de localização não disponíveis para gerar o mapa.")
        return
    
    # Remove rows with invalid coordinates
    df_plot = df_plot.dropna(subset=['lat', 'lon'])
    df_plot = df_plot[(df_plot['lat'] != 0) & (df_plot['lon'] != 0)]
    
    if df_plot.empty:
        st.warning("Nenhum dado de localização válido encontrado.")
        return
    
    # Calculate price percentiles
    if 'prices_rawPrice' in df_plot.columns:
        df_plot['price_percentile'] = df_plot['prices_rawPrice'].rank(pct=True)
        color_column = 'price_percentile'
        color_scale = ['blue', 'green', 'yellow', 'orange', 'red']
    else:
        # Fallback if price data is not available
        color_column = None
        color_scale = None
    
    # Set size column
    size_column = 'area_useful' if 'area_useful' in df_plot.columns else None
    
    # Calculate map center dynamically
    center_lat = df_plot['lat'].mean()
    center_lon = df_plot['lon'].mean()
    
    # Calculate appropriate zoom level based on coordinate spread
    lat_range = df_plot['lat'].max() - df_plot['lat'].min()
    lon_range = df_plot['lon'].max() - df_plot['lon'].min()
    max_range = max(lat_range, lon_range)
    
    # Determine zoom level based on coordinate spread
    if max_range > 1:
        zoom = 8
    elif max_range > 0.5:
        zoom = 10
    elif max_range > 0.1:
        zoom = 11
    elif max_range > 0.05:
        zoom = 12
    else:
        zoom = 13
    
    # Create hover data
    hover_data = {}
    if 'prices_rawPrice' in df_plot.columns:
        hover_data["prices_rawPrice"] = ":,.2f"
    if 'area_useful' in df_plot.columns:
        hover_data["area_useful"] = True
    if color_column:
        hover_data["price_percentile"] = False
    hover_data.update({"lat": False, "lon": False})
    
    # Create the map using the new scatter_map function
    try:
        fig = px.scatter_map(
            df_plot,
            lat="lat",
            lon="lon",
            color=color_column,
            size=size_column,
            color_continuous_scale=color_scale,
            size_max=15,
            zoom=zoom,
            center={"lat": center_lat, "lon": center_lon},
            map_style="open-street-map",
            hover_name="location_neighborhood_name" if 'location_neighborhood_name' in df_plot.columns else None,
            hover_data=hover_data,
            labels={"prices_rawPrice": "Preço (R$)", "price_percentile": "Percentil de Preço"}
        )
        
        fig.update_layout(
            margin={"r":0,"t":0,"l":0,"b":0},
            legend_title_text='Percentil de Preço' if color_column else None
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.warning(f"Erro ao gerar o mapa: {e}")
        st.info("Tentando usar método alternativo de visualização...")
        
        # Fallback to basic scatter plot if map fails
        if 'prices_rawPrice' in df_plot.columns:
            fig_fallback = px.scatter(
                df_plot, 
                x="lon", 
                y="lat", 
                color="prices_rawPrice",
                size="area_useful" if size_column else None,
                title="Distribuição dos Imóveis por Coordenadas",
                labels={"lon": "Longitude", "lat": "Latitude", "prices_rawPrice": "Preço (R$)"}
            )
            st.plotly_chart(fig_fallback, use_container_width=True)

def safe_fillna_columns(df, columns, fill_value=0):
    """
    Safely fills NaN values for specified columns, handling cases where columns don't exist.
    """
    for col in columns:
        if col in df.columns:
            df[col] = df[col].fillna(fill_value)
        else:
            # Create column with fill_value if it doesn't exist
            df[col] = fill_value
    return df

def build_url_with_filters(tipo_imovel, transacao, sigla_estado, cidade_slug, filtros_selecionados=None):
    """
    Constrói a URL final conforme especificações do prompt.
    """
    # URL base
    url_base = f"https://www.chavesnamao.com.br/{tipo_imovel}-{transacao}/{sigla_estado}-{cidade_slug}"
    
    # Adicionar parâmetro de filtro se houver subtipos selecionados
    if filtros_selecionados:
        ids_filtros = []
        for filtro in filtros_selecionados:
            if filtro in FILTRO_TIPO_IMOVEL_ID:
                ids_filtros.append(str(FILTRO_TIPO_IMOVEL_ID[filtro]))
        
        if ids_filtros:
            filtro_param = '+'.join(ids_filtros)
            url_base += f"/?filtro=tim:[{filtro_param}]"
    
    return url_base

def initialize_session_state():
    """Inicializa todas as variáveis de session state necessárias."""
    if 'model' not in st.session_state:
        st.session_state.model = None
    if 'trained_region' not in st.session_state:
        st.session_state.trained_region = ""
    if 'feature_names' not in st.session_state:
        st.session_state.feature_names = None
    if 'numerical_features' not in st.session_state:
        st.session_state.numerical_features = None
    if 'categorical_features' not in st.session_state:
        st.session_state.categorical_features = None
    if 'neighborhoods' not in st.session_state:
        st.session_state.neighborhoods = []
    if 'df_cleaned' not in st.session_state:
        st.session_state.df_cleaned = None
    if 'model_metrics' not in st.session_state:
        st.session_state.model_metrics = {}
    if 'cities_df' not in st.session_state:
        st.session_state.cities_df = pd.DataFrame()
    if 'last_selection' not in st.session_state:
        st.session_state.last_selection = {}
    if 'property_types' not in st.session_state:
        st.session_state.property_types = []
    if 'transaction_type' not in st.session_state:
        st.session_state.transaction_type = 'a-venda'

def aba_coleta_treinamento():
    """Aba 1: Coleta e Treinamento"""
    st.header("🔧 Configuração da Busca e Treinamento")
    
    # Passo 1: Seleções Principais
    col1, col2, col3 = st.columns(3)
    
    with col1:
        estado_selecionado = st.selectbox(
            "Selecione o Estado",
            options=list(ESTADOS_BRASIL.keys()),
            index=list(ESTADOS_BRASIL.keys()).index('São Paulo') if 'São Paulo' in ESTADOS_BRASIL else 0
        )
        sigla_estado = ESTADOS_BRASIL[estado_selecionado]
    
    with col2:
        tipo_imovel_nome = st.selectbox(
            "Tipo de Imóvel",
            options=list(TIPOS_IMOVEIS.keys()),
            index=0
        )
        tipo_imovel = TIPOS_IMOVEIS[tipo_imovel_nome]
    
    with col3:
        transacao_nome = st.selectbox(
            "Tipo de Transação",
            options=list(TIPOS_TRANSACAO.keys()),
            index=0
        )
        transacao = TIPOS_TRANSACAO[transacao_nome]
        # Armazenar o tipo de transação no session state
        st.session_state.transaction_type = transacao

    # Verificar se as seleções principais mudaram
    current_selection = {
        'estado': sigla_estado,
        'tipo_imovel': tipo_imovel,
        'transacao': transacao
    }
    
    selection_changed = current_selection != st.session_state.last_selection
    
    # Buscar cidades se a seleção mudou ou se não temos cidades carregadas
    if selection_changed or st.session_state.cities_df.empty:
        with st.spinner("Buscando cidades disponíveis..."):
            st.session_state.cities_df = get_cities(
                imovel=tipo_imovel,
                transacao=transacao,
                estado=sigla_estado
            )
            st.session_state.last_selection = current_selection
    
    # Passo 2: Seleção de Cidade (Dinâmica)
    if not st.session_state.cities_df.empty:
        cidades_disponiveis = sorted(st.session_state.cities_df['title'].tolist())
        cidade_selecionada = st.selectbox(
            "Selecione a Cidade",
            options=cidades_disponiveis,
            index=0
        )
        cidade_slug = clean_portuguese_name(cidade_selecionada)
    else:
        st.error("Nenhuma cidade encontrada para a combinação selecionada.")
        return

    # Passo 3: Filtros Opcionais
    st.subheader("🏠 Filtros Opcionais")
    
    col_filtros1, col_filtros2 = st.columns([2, 1])
    
    with col_filtros1:
        subtipos_selecionados = st.multiselect(
            "Selecione um ou mais tipos de imóveis residenciais (opcional)",
            options=list(FILTRO_TIPO_IMOVEL_ID.keys()),
            help="Este filtro permite refinar a busca por subtipos específicos de imóveis."
        )
    
    with col_filtros2:
        max_pages_per_neighborhood = st.number_input(
            "Máx. páginas por bairro",
            min_value=1,
            max_value=99,
            value=2,
            help="Número máximo de páginas a serem coletadas por bairro. Mais páginas = mais dados, mas coleta mais lenta."
        )

    # Mostrar prévia da URL que será construída
    url_construida = build_url_with_filters(
        tipo_imovel, transacao, sigla_estado, cidade_slug, subtipos_selecionados
    )
    
    with st.expander("🔗 Prévia da URL de Busca"):
        st.code(url_construida)

    # Warning for high page numbers
    if max_pages_per_neighborhood > 5:
        st.warning("⚠️ Atenção: Coletar mais de 5 páginas por bairro pode levar muito tempo. A coleta pode demorar mais de 10 minutos dependendo da quantidade de bairros.")

    if st.button("🚀 Buscar Dados e Treinar Modelo", use_container_width=True):
        with st.spinner("Processando... Isso pode levar alguns minutos."):
            try:
                # Usar as variáveis selecionadas diretamente (sem parsing de URL)
                state = sigla_estado
                city = cidade_slug
                property_type = tipo_imovel
                transaction = transacao
                
                st.session_state.trained_region = f"{cidade_selecionada}, {estado_selecionado}"
                st.info(f"🎯 Buscando dados para: {tipo_imovel_nome} para {transacao_nome.lower()} em {cidade_selecionada}/{estado_selecionado}")

                # Mostrar URL construída
                if subtipos_selecionados:
                    st.info(f"🏠 Filtros aplicados: {', '.join(subtipos_selecionados)}")

                # FIXED: Use the corrected neighborhood collection logic
                neighborhood_df = get_all_neighborhoods(state, city, property_type, transaction)
                
                if neighborhood_df.empty:
                    st.error("❌ Nenhum bairro com anúncios encontrado. Verifique se a região selecionada possui imóveis disponíveis.")
                    return

                # Show preview of neighborhoods found
                # ETAPA B: Collect ads from all neighborhoods using the correct API
                st.subheader("🏠 Etapa B: Coletando Anúncios dos Bairros")
                
                # NOVA FUNCIONALIDADE: Converter subtipos selecionados para IDs
                ids_selecionados = []
                if subtipos_selecionados:
                    ids_selecionados = [str(FILTRO_TIPO_IMOVEL_ID[nome]) for nome in subtipos_selecionados if nome in FILTRO_TIPO_IMOVEL_ID]
                    st.info(f"🏠 Aplicando filtros de subtipos: {', '.join(subtipos_selecionados)} (IDs: {', '.join(ids_selecionados)})")
                
                all_ads = []
                progress_bar = st.progress(0)
                total_neighborhoods = len(neighborhood_df)

                st.info(f"Coletando até {max_pages_per_neighborhood} página(s) de {total_neighborhoods} bairros...")

                # Track scraping statistics
                successful_scrapes = 0
                failed_scrapes = 0
                total_ads_collected = 0

                for i, row in enumerate(neighborhood_df.itertuples()):
                    neighborhood_url = row.url
                    neighborhood_name = getattr(row, 'name', neighborhood_url)
                    ads_count = getattr(row, 'adsCount', 0)
                    zone_name = getattr(row, 'zone_name', '') if hasattr(row, 'zone_name') else ''
                    
                    # Calculate pages to scrape based on user input and available ads
                    estimated_pages = ceil(ads_count / 15) if ads_count > 0 else 1
                    pages_to_scrape = min(max_pages_per_neighborhood, max(1, estimated_pages))
                    
                    # Track ads collected for this neighborhood
                    ads_collected_this_neighborhood = 0
                    
                    # CRITICAL: Use the corrected ads collection function with subtipo filters
                    for page in range(1, pages_to_scrape + 1):
                        ads_df = get_ads(state, city, property_type, transaction, neighborhood_url, page, subtipo_ids=ids_selecionados)
                        if not ads_df.empty:
                            all_ads.append(ads_df)
                            ads_collected_this_neighborhood += len(ads_df)
                        
                        # Rate limiting
                        time.sleep(0.7)
                    
                    # Update statistics
                    if ads_collected_this_neighborhood > 0:
                        successful_scrapes += 1
                        total_ads_collected += ads_collected_this_neighborhood
                    else:
                        failed_scrapes += 1
                    
                    # Enhanced progress display with zone info if available
                    zone_info = f" (Zona: {zone_name})" if zone_name else ""
                    progress_text = f"🏠 {neighborhood_name}{zone_info} - {ads_collected_this_neighborhood} anúncios ({i+1}/{total_neighborhoods})"
                    progress_bar.progress((i + 1) / total_neighborhoods, text=progress_text)

                # Summary of scraping results
                st.success(f"🎉 Coleta finalizada! {successful_scrapes} bairros com dados, {failed_scrapes} sem dados")
                st.info(f"📊 Total coletado: {total_ads_collected} anúncios")

                if not all_ads:
                    st.error("❌ Não foi possível coletar nenhum anúncio. Verifique a conectividade ou tente uma região diferente.")
                    return

                # Combine and deduplicate collected data
                final_df = pd.concat(all_ads, ignore_index=True)
                final_df = final_df[final_df['prices_rawPrice']>0].reset_index(drop=True)

                # NOVO: Filtro rigoroso para manter apenas imóveis da cidade selecionada
                if 'location_city_name' in final_df.columns:
                    initial_count = len(final_df)
                    
                    # Normalizar nomes das cidades do dataframe para comparar com o slug
                    final_df['cleaned_city_name'] = final_df['location_city_name'].apply(clean_portuguese_name)
                    
                    # A variável 'city' já contém o nome limpo da cidade selecionada pelo usuário
                    final_df = final_df[final_df['cleaned_city_name'] == city].copy()
                    
                    # Limpar coluna temporária
                    final_df.drop(columns=['cleaned_city_name'], inplace=True)
                    
                    filtered_count = len(final_df)
                    removed_count = initial_count - filtered_count
                    
                    if removed_count > 0:
                        st.warning(f"🧹 Foram removidos {removed_count} anúncios de cidades vizinhas para garantir a precisão da análise.")
                
                # Handle deduplication safely
                if 'id' in final_df.columns:
                    initial_count = len(final_df)
                    final_df = final_df.drop_duplicates(subset=['id'])
                    duplicates_removed = initial_count - len(final_df)
                    if duplicates_removed > 0:
                        st.info(f"🔄 Removidas {duplicates_removed} duplicatas")
                

                # Preencher valores nulos com string vazia para o filtro funcionar
                final_df['location.street.name'].fillna('', inplace=True)

                # Manter apenas as linhas onde o nome da rua, após remover espaços, não está vazio
                final_df = final_df[final_df['location.street.name'].str.strip() != ''].copy()

                st.success(f"✅ Processamento concluído! {len(final_df)} anúncios únicos coletados.")

                # Process features and clean data
                with st.spinner("Processando características dos imóveis..."):
                    df_processed, feature_cols = process_features(final_df)
                    df_cleaned = clean_data(df_processed)
                    
                    # Armazenar o dataframe limpo no session state
                    st.session_state.df_cleaned = df_cleaned

                # Check if we have enough data for training
                if len(df_cleaned) < 50:
                    st.warning(f"⚠️ Apenas {len(df_cleaned)} amostras válidas. O modelo pode não ser preciso e/ou pode crashar a aplicação.")
                   
                # Prepare features for machine learning - robust approach
                st.subheader("🤖 Treinando Modelo de Machine Learning")
                
                TARGET_VARIABLE = 'prices_rawPrice'

                # Define base numerical features
                base_numerical_features = ['area_total', 'area_useful', 'bathrooms_count', 'bedrooms_count', 'garages_count', 'suites_count']

                # Only include existing feature columns
                existing_feature_cols = [col for col in feature_cols if col in df_cleaned.columns]
                existing_feature_cols = list(set(existing_feature_cols))  # Remove duplicates

                numerical_features = base_numerical_features + existing_feature_cols
                existing_numerical_features = [col for col in numerical_features if col in df_cleaned.columns]
                existing_numerical_features = list(set(existing_numerical_features))  # Remove duplicates

                # IMPORTANTE: Adicionar realtyType_name como feature categórica
                categorical_features = ['location_neighborhood_name', 'realtyType_name']
                existing_categorical_features = [col for col in categorical_features if col in df_cleaned.columns]
                
                # Ensure target variable exists
                if TARGET_VARIABLE not in df_cleaned.columns:
                    st.error(f"Variável alvo '{TARGET_VARIABLE}' não encontrada nos dados coletados.")
                    return

                # Safe column handling - add missing columns and fill NaN values
                df_cleaned = safe_fillna_columns(df_cleaned, existing_numerical_features, 0)
                df_cleaned = safe_fillna_columns(df_cleaned, existing_categorical_features, 'missing')
                
                # Prepare data for training
                all_features = existing_numerical_features + existing_categorical_features
                all_features = list(set(all_features))  # Remove duplicates

                # Remove duplicated columns from DataFrame if any
                duplicated_cols = df_cleaned.columns[df_cleaned.columns.duplicated()]
                if len(duplicated_cols) > 0:
                    df_cleaned = df_cleaned.loc[:, ~df_cleaned.columns.duplicated()]

                X = df_cleaned[all_features]
                y = df_cleaned[TARGET_VARIABLE]

                # Remove any remaining NaN values from target
                mask = ~y.isna()
                X = X[mask]
                y = y[mask]

                if len(X) == 0:
                    st.error("Nenhum dado válido restante após a limpeza.")
                    return

                # Create preprocessing pipelines
                numerical_transformer = Pipeline(steps=[('scaler', StandardScaler())])
                categorical_transformer = Pipeline(steps=[('onehot', OneHotEncoder(handle_unknown='ignore'))])

                transformers = []
                if existing_numerical_features:
                    transformers.append(('num', numerical_transformer, existing_numerical_features))
                if existing_categorical_features:
                    transformers.append(('cat', categorical_transformer, existing_categorical_features))

                if not transformers:
                    st.error("Nenhuma feature válida encontrada para treinar o modelo.")
                    return

                preprocessor = ColumnTransformer(transformers=transformers)

                # Create and train the model
                model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
                pipeline = Pipeline(steps=[('preprocessor', preprocessor), ('regressor', model)])

                # Split and train
                with st.spinner("Treinando modelo..."):
                    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                    pipeline.fit(X_train, y_train)

                # Evaluate model performance
                y_pred = pipeline.predict(X_test)
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                
                # Calculate MAPE (Mean Absolute Percentage Error)
                mape = calculate_mape(y_test, y_pred)

                # NOVA FUNCIONALIDADE: Fazer predições em todo o conjunto de dados
                with st.spinner("Gerando predições para análise..."):
                    # Filtrar apenas os dados que têm todas as features necessárias
                    mask_all_features = ~df_cleaned[all_features].isna().any(axis=1)
                    df_for_prediction = df_cleaned[mask_all_features].copy()
                    
                    if len(df_for_prediction) > 0:
                        X_all = df_for_prediction[all_features]
                        predictions = pipeline.predict(X_all)
                        
                        # Adicionar predições ao DataFrame
                        df_for_prediction['predicted_price'] = predictions
                        df_for_prediction['price_diff_pct'] = (df_for_prediction['prices_rawPrice'] - df_for_prediction['predicted_price']) / df_for_prediction['predicted_price']
                        
                        # Atualizar o session_state com as predições
                        st.session_state.df_cleaned = df_for_prediction
                        
                        st.success(f"✅ Predições geradas para {len(df_for_prediction)} imóveis")

                # Display model performance with MAPE
                st.subheader("📈 Performance do Modelo Treinado")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Erro Médio Absoluto (MAE)", f"R$ {mae:,.2f}")
                    
                with col2:
                    st.metric("R² Score", f"{r2:.3f}")
                    if r2 > 0.8:
                        st.success("Excelente!")
                    elif r2 > 0.6:
                        st.info("Bom")
                    else:
                        st.warning("Pode melhorar")
                        
                with col3:
                    if not np.isnan(mape):
                        st.metric("MAPE", f"{mape:.2f}%")
                        if mape < 15:
                            st.success("Excelente!")
                        elif mape < 25:
                            st.info("Bom")
                        else:
                            st.warning("Pode melhorar")
                    else:
                        st.metric("MAPE", "N/A")
                        
                with col4:
                    st.metric("Amostras Treinadas", f"{len(df_cleaned):,}")

                # Store model and metadata in session state
                st.session_state.model = pipeline
                st.session_state.feature_names = X.columns.tolist()
                st.session_state.numerical_features = existing_numerical_features
                st.session_state.categorical_features = existing_categorical_features
                st.session_state.neighborhoods = sorted(df_cleaned['location_neighborhood_name'].unique().tolist()) if 'location_neighborhood_name' in df_cleaned.columns else []
                
                # Armazenar tipos de imóveis únicos encontrados nos dados
                if 'realtyType_name' in df_cleaned.columns:
                    st.session_state.property_types = sorted([pt for pt in df_cleaned['realtyType_name'].unique() if pd.notna(pt)])

                # Armazenar métricas do modelo
                st.session_state.model_metrics = {
                    'mae': mae,
                    'r2': r2,
                    'mape': mape,
                    'samples': len(df_cleaned)
                }

                st.success("✅ Modelo treinado com sucesso! Agora você pode usar as abas 'Análise de Mercado' e 'Buscador de Imóveis'.")

            except Exception as e:
                st.error(f"❌ Ocorreu um erro durante o processamento: {e}")
                st.write("Detalhes do erro:")
                st.exception(e)

def aba_analise_mercado():
    """MODIFICADA: Aba 2: Análise de Mercado (EDA) com cálculo ajustado de preço/m²"""
    st.header("📊 Análise de Mercado e Dados Exploratórios")
    
    if st.session_state.model is None or st.session_state.df_cleaned is None:
        st.info("📋 Por favor, treine um modelo na aba 'Coleta e Treinamento' primeiro.")
        st.markdown("""
        ### Como começar:
        1. Vá para a aba **"Coleta e Treinamento"**
        2. Configure os filtros de busca (Estado, Cidade, etc.)
        3. Clique em **"Buscar Dados e Treinar Modelo"**
        4. Retorne a esta aba para ver as análises
        """)
        return
    
    st.success(f"✅ Modelo ativo para: **{st.session_state.trained_region}**")
    
    # Mostrar métricas do modelo
    if st.session_state.model_metrics:
        st.subheader("📈 Métricas do Modelo")
        col1, col2, col3, col4 = st.columns(4)
        
        metrics = st.session_state.model_metrics
        with col1:
            st.metric("MAE", f"R$ {metrics.get('mae', 0):,.2f}")
        with col2:
            st.metric("R² Score", f"{metrics.get('r2', 0):.3f}")
        with col3:
            mape = metrics.get('mape', np.nan)
            if not np.isnan(mape):
                st.metric("MAPE", f"{mape:.2f}%")
            else:
                st.metric("MAPE", "N/A")
        with col4:
            st.metric("Amostras", f"{metrics.get('samples', 0):,}")
    
    # Distribuição Geográfica
    st.subheader("🗺️ Distribuição Geográfica dos Imóveis")
    if st.session_state.df_cleaned is not None and not st.session_state.df_cleaned.empty:
        plot_geo_data(st.session_state.df_cleaned)
    else:
        st.warning("Dados não disponíveis para visualização.")
    
    # NOVO GRÁFICO 1: Top 15 Bairros com Menor Preço por m² (com cálculo ajustado)
    if st.session_state.df_cleaned is not None:
        df = st.session_state.df_cleaned.copy()
        
        if 'prices_rawPrice' in df.columns and 'area_useful' in df.columns and 'location_neighborhood_name' in df.columns:

            st.write(" ")
            st.write(" ")
            st.write(" ")

            st.subheader("💰 Bairros com Menor Custo por Metro Quadrado (R$/m²)")
            
            # Usar o cálculo ajustado de preço por m²
            df_with_adjusted_price = calculate_adjusted_price_per_sqm(df, st.session_state.transaction_type)
            
            # Filtrar para área_useful > 0
            df_filtered = df_with_adjusted_price[df_with_adjusted_price['area_useful'] > 0].copy()
            
            if not df_filtered.empty:
                # Agrupar por bairro e calcular preço médio por m², pegar os 15 menores
                neighborhood_price_per_sqm = df_filtered.groupby('location_neighborhood_name')['preco_m2'].mean().reset_index()
                top_15_cheapest = neighborhood_price_per_sqm.nsmallest(15, 'preco_m2')
                
                # Criar gráfico de barras horizontal
                title_suffix = " (Aluguel + Cond. + IPTU)" if st.session_state.transaction_type == 'para-alugar' else ""
                fig_price_per_sqm = px.bar(
                    top_15_cheapest,
                    x='preco_m2',
                    y='location_neighborhood_name',
                    orientation='h',
                    title=f"Top 15 Bairros com Menor Preço Médio por m²{title_suffix}",
                    labels={'preco_m2': 'Preço por m² (R$)', 'location_neighborhood_name': 'Bairro'},
                    color='preco_m2',
                    color_continuous_scale='RdYlGn_r'
                )
                fig_price_per_sqm.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_price_per_sqm, use_container_width=True)

    
    # NOVO GRÁFICO 2: Top 15 Bairros por Volume de Anúncios
    if st.session_state.df_cleaned is not None:
        if 'location_neighborhood_name' in df.columns and 'realtyType_name' in df.columns:
            st.subheader("📊 Concentração de Imóveis por Bairro")
            
            # Encontrar os 15 bairros com maior contagem de imóveis
            top_15_neighborhoods = df['location_neighborhood_name'].value_counts().nlargest(15).index.tolist()
            
            # Filtrar dataframe para conter apenas os imóveis desses top 15 bairros
            df_top_15 = df[df['location_neighborhood_name'].isin(top_15_neighborhoods)].copy()
            
            if not df_top_15.empty:
                # Criar gráfico de barras empilhadas
                fig_volume = px.bar(
                    df_top_15,
                    x='location_neighborhood_name',
                    color='realtyType_name',
                    title="Volume de Anúncios nos Top 15 Bairros",
                    labels={'count': 'Quantidade de Imóveis', 'location_neighborhood_name': 'Bairro', 'realtyType_name': 'Tipo de Imóvel'}
                )
                fig_volume.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_volume, use_container_width=True)
    
    # Estatísticas descritivas dos dados
    if st.session_state.df_cleaned is not None:
        st.subheader("📋 Estatísticas dos Dados Coletados")
        
        df = st.session_state.df_cleaned
        
        # Estatísticas básicas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if 'prices_rawPrice' in df.columns:
                avg_price = df['prices_rawPrice'].mean()
                st.metric("Preço Médio", f"R$ {avg_price:,.2f}")
        
        with col2:
            if 'area_useful' in df.columns:
                avg_area = df['area_useful'].mean()
                st.metric("Área Média", f"{avg_area:.1f} m²")
        
        with col3:
            total_properties = len(df)
            st.metric("Total de Imóveis", f"{total_properties:,}")
        
        # Distribuição por tipo de imóvel
        if 'realtyType_name' in df.columns:
            st.subheader("🏠 Distribuição por Tipo de Imóvel")
            type_counts = df['realtyType_name'].value_counts()
            
            col_pie, col_bar = st.columns(2)
            
            with col_pie:
                fig_pie = px.pie(
                    values=type_counts.values,
                    names=type_counts.index,
                    title="Proporção por Tipo"
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_bar:
                fig_bar = px.bar(
                    x=type_counts.index,
                    y=type_counts.values,
                    title="Quantidade por Tipo",
                    labels={'x': 'Tipo de Imóvel', 'y': 'Quantidade'}
                )
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # Distribuição de preços
        if 'prices_rawPrice' in df.columns:
            st.subheader("💰 Distribuição de Preços")
            
            fig_hist = px.histogram(
                df,
                x='prices_rawPrice',
                nbins=50,
                title="Distribuição dos Preços",
                labels={'prices_rawPrice': 'Preço (R$)', 'count': 'Frequência'}
            )
            st.plotly_chart(fig_hist, use_container_width=True)

def aba_buscador_imoveis():
    """NOVA ABA EVOLUÍDA: Buscador de Imóveis com análises inteligentes."""
    st.header("🔎 Buscador de Imóveis")

    if st.session_state.df_cleaned is None or st.session_state.df_cleaned.empty:
        st.info("📋 Por favor, colete os dados na aba 'Coleta e Treinamento' para usar o buscador.")
        return

    df = st.session_state.df_cleaned.copy()
    
    # Verificar se temos predições disponíveis
    has_predictions = 'predicted_price' in df.columns and 'price_diff_pct' in df.columns
    
    if not has_predictions:
        st.warning("⚠️ Predições do modelo não encontradas. Algumas funcionalidades analíticas podem estar limitadas.")
    
    # Calcular médias por bairro (para comparativo)
    df_with_adjusted_price = calculate_adjusted_price_per_sqm(df, st.session_state.transaction_type)
    medias_bairro = df_with_adjusted_price.groupby('location_neighborhood_name')[['preco_m2', 'bedrooms_count', 'bathrooms_count']].mean()
    
    # --- FILTROS NA SIDEBAR ---
    st.sidebar.header("🔍 Filtros do Buscador")

    # Filtro de Preço
    min_price = int(df['prices_rawPrice'].min())
    max_price = int(df['prices_rawPrice'].max())
    price_range = st.sidebar.slider(
        "Faixa de Preço (R$)",
        min_value=min_price,
        max_value=max_price,
        value=(min_price, max_price)
    )

    # Filtro de Área Útil
    min_area = int(df['area_useful'].min())
    max_area = int(df['area_useful'].max())
    area_range = st.sidebar.slider(
        "Faixa de Área Útil (m²)",
        min_value=min_area,
        max_value=max_area,
        value=(min_area, max_area)
    )

    # Filtro de Bairro
    all_neighborhoods = sorted(df['location_neighborhood_name'].unique())
    selected_neighborhoods = st.sidebar.multiselect(
        "Bairros",
        options=all_neighborhoods,
        default=[]
    )

    # Filtro de Quartos
    all_bedrooms = sorted(df['bedrooms_count'].unique())
    selected_bedrooms = st.sidebar.multiselect(
        "Número de Quartos",
        options=all_bedrooms,
        default=[]
    )

    # NOVO FILTRO ANALÍTICO
    if has_predictions:
        analise_preco = st.sidebar.selectbox(
            "Análise de Preço (Anúncio vs. Modelo)",
            options=[
                "Todos os imóveis",
                "Abaixo do preço (Oportunidades)", 
                "Preço Justo",
                "Acima do preço"
            ]
        )

    # --- APLICANDO FILTROS ---
    df_filtrado = df[
        (df['prices_rawPrice'] >= price_range[0]) & (df['prices_rawPrice'] <= price_range[1]) &
        (df['area_useful'] >= area_range[0]) & (df['area_useful'] <= area_range[1])
    ]

    if selected_neighborhoods:
        df_filtrado = df_filtrado[df_filtrado['location_neighborhood_name'].isin(selected_neighborhoods)]
    
    if selected_bedrooms:
        df_filtrado = df_filtrado[df_filtrado['bedrooms_count'].isin(selected_bedrooms)]

    # Aplicar filtro analítico se disponível
    if has_predictions and analise_preco != "Todos os imóveis":
        if analise_preco == "Abaixo do preço (Oportunidades)":
            df_filtrado = df_filtrado[df_filtrado['price_diff_pct'] < -0.10]
        elif analise_preco == "Preço Justo":
            df_filtrado = df_filtrado[(df_filtrado['price_diff_pct'] >= -0.10) & (df_filtrado['price_diff_pct'] <= 0.10)]
        elif analise_preco == "Acima do preço":
            df_filtrado = df_filtrado[df_filtrado['price_diff_pct'] > 0.10]

    # --- OPÇÕES DE ORDENAÇÃO ---
    df_filtrado = calculate_adjusted_price_per_sqm(df_filtrado, st.session_state.transaction_type)

    sort_options = {
        'Preço (menor ao maior)': ('prices_rawPrice', True),
        'Preço (maior ao menor)': ('prices_rawPrice', False),
        'Preço/m² (menor ao maior)': ('preco_m2', True),
        'Área Útil (maior para menor)': ('area_useful', False)
    }
    
    sort_selection = st.selectbox("Ordenar por:", options=list(sort_options.keys()))
    sort_column, ascending_order = sort_options[sort_selection]
    df_filtrado = df_filtrado.sort_values(by=sort_column, ascending=ascending_order)

    # --- EXIBIÇÃO DOS RESULTADOS ---
    st.write(f"**{len(df_filtrado)} imóveis encontrados**")
    st.markdown("---")

    if df_filtrado.empty:
        st.warning("Nenhum imóvel encontrado com os filtros aplicados.")
    else:
        for _, imovel in df_filtrado.iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:

                    preco = imovel.get('prices_rawPrice', 0)
                    area = imovel.get('area_useful', 0)
                    preco_m2 = imovel.get('preco_m2', 0)
                    tipo = imovel.get('realtyType_name', 'N/A')
                    bairro = imovel.get('location_neighborhood_name', 'N/A')
                    
                    st.subheader(f"{tipo} em {bairro}")
                                        # Mostrar preço adequado dependendo do tipo de transação
                    if st.session_state.transaction_type == 'para-alugar':
                        cond_value = imovel.get('prices_condominiumValue', 0)
                        iptu_value = imovel.get('prices_iptuValue', 0)
                        
                        # Os valores já são float, então a soma é direta
                        total_monthly = preco + cond_value + iptu_value
                        
                        st.markdown(f"💰 **Aluguel: R\$** {preco:,.2f} | **Custo Total Mensal: R\$** {total_monthly:,.2f}")
                        if cond_value > 0 or iptu_value > 0:
                            st.caption(f"Inclui: Cond. R\$ {cond_value:,.2f} + IPTU R\$ {iptu_value:,.2f}")
                    else:
                        st.markdown(f"💰 **Preço de Venda: R\$** {preco:,.2f}")
                    st.markdown(f"📏 **Área:** {area:.0f} m²  |  💱 **Preço/m²: R\$**  {preco_m2:,.2f}")
                    
                    quartos = imovel.get('bedrooms_count', 0)
                    banheiros = imovel.get('bathrooms_count', 0)
                    garagens = imovel.get('garages_count', 0)
                    st.markdown(f"**🛏️ Quartos:** {quartos:.0f} | **🚿 Banheiros:** {banheiros:.0f} | **🚗 Garagens:** {garagens:.0f}")

                    # NOVA FUNCIONALIDADE: Exibir preço estimado e indicador visual
                    if has_predictions and 'predicted_price' in imovel and pd.notna(imovel['predicted_price']):
                        predicted_price = imovel['predicted_price']
                        price_diff_pct = imovel.get('price_diff_pct', 0)
                        
                        st.markdown(f"🎯 **Preço Estimado pelo Modelo:** R$ {predicted_price:,.2f}")
                        
                        # Indicador visual baseado na diferença percentual
                        if price_diff_pct < -0.10:
                            st.success("🎯 Oportunidade: Abaixo do preço estimado!")
                        elif price_diff_pct > 0.10:
                            st.warning("⚠️ Atenção: Acima do preço estimado.")
                        else:
                            st.info("✅ Preço justo.")

                with col2:
                    st.write("") # Espaçamento
                    st.write("") # Espaçamento
                    property_url = imovel.get('property_url', '')
                    if property_url and pd.notna(property_url):
                        url_completa = f"https://www.chavesnamao.com.br{property_url}"
                        st.link_button("Ver Anúncio Original", url_completa)
                    else:
                        st.caption("Link indisponível")

                # NOVA FUNCIONALIDADE: Comparativo com a média do bairro
                if bairro in medias_bairro.index:
                    with st.expander("🔍 Comparativo no Bairro"):
                        col_a, col_b, col_c = st.columns(3)
                        
                        # Preço por m²
                        media_preco_m2 = medias_bairro.loc[bairro, 'preco_m2']
                        diff_preco_m2 = preco_m2 - media_preco_m2
                        
                        with col_a:
                            st.metric(
                                "Preço/m² vs. Média do Bairro",
                                f"R$ {preco_m2:,.2f}",
                                delta=f"{diff_preco_m2:+,.2f}",
                                help=f"Média no bairro: R$ {media_preco_m2:,.2f}"
                            )
                        
                        # Quartos
                        media_quartos = medias_bairro.loc[bairro, 'bedrooms_count']
                        diff_quartos = quartos - media_quartos
                        
                        with col_b:
                            st.metric(
                                "Quartos vs. Média do Bairro",
                                f"{quartos:.0f}",
                                delta=f"{diff_quartos:+.1f}",
                                help=f"Média no bairro: {media_quartos:.1f}"
                            )
                        
                        # Banheiros
                        media_banheiros = medias_bairro.loc[bairro, 'bathrooms_count']
                        diff_banheiros = banheiros - media_banheiros
                        
                        with col_c:
                            st.metric(
                                "Banheiros vs. Média do Bairro",
                                f"{banheiros:.0f}",
                                delta=f"{diff_banheiros:+.1f}",
                                help=f"Média no bairro: {media_banheiros:.1f}"
                            )
                
                st.markdown("---")

def aba_calculadora():
    """MODIFICADA: Aba 4: Calculadora de Preços com funcionalidade de recomendação"""
    st.header("💰 Calculadora de Preços de Imóveis")
    
    if st.session_state.model is None:
        st.info("📋 Por favor, treine um modelo na aba 'Coleta e Treinamento' primeiro.")
        st.markdown("""
        ### Como começar:
        1. Vá para a aba **"Coleta e Treinamento"**
        2. Configure os filtros de busca (Estado, Cidade, etc.)
        3. Clique em **"Buscar Dados e Treinar Modelo"**
        4. Retorne a esta aba para usar a calculadora
        """)
        return
    
    st.success(f"✅ Calculadora ativa para: **{st.session_state.trained_region}**")
    
    with st.form("prediction_form"):
        st.markdown("Preencha os dados do imóvel para obter uma estimativa de preço.")
        
        # Property characteristics input
        col1, col2, col3 = st.columns(3)
        
        with col1:
            area_util = st.number_input("Área Útil (m²)", min_value=10, max_value=1000, value=70)
            quartos = st.number_input("Quartos", min_value=0, max_value=10, value=2)
            
            # NOVO: Seletor de Tipo de Imóvel
            if st.session_state.property_types:
                tipo_imovel_selecionado = st.selectbox(
                    "Tipo do Imóvel",
                    options=st.session_state.property_types,
                    help="Escolha o tipo de imóvel que corresponde ao que você deseja avaliar."
                )
            else:
                tipo_imovel_selecionado = st.text_input(
                    "Tipo do Imóvel", 
                    value="Apartamento",
                    help="Digite o tipo de imóvel (ex: Apartamento, Casa, etc.)"
                )
        
        with col2:
            area_total = st.number_input("Área Total (m²)", min_value=10, max_value=1000, value=90)
            banheiros = st.number_input("Banheiros", min_value=0, max_value=10, value=2)
            
            if st.session_state.neighborhoods:
                bairro_selecionado = st.selectbox("Bairro", st.session_state.neighborhoods)
            else:
                bairro_selecionado = st.text_input("Bairro", value="Centro")
        
        with col3:
            suites = st.number_input("Suítes", min_value=0, max_value=10, value=1)
            garagens = st.number_input("Vagas de Garagem", min_value=0, max_value=10, value=1)
        
        # Additional features selection
        st.subheader("🏠 Características Adicionais")
        features_selecionadas = []
        
        if st.session_state.numerical_features:
            feature_cols_form = [col for col in st.session_state.numerical_features if col.startswith('feature_')]
            
            if feature_cols_form:
                num_cols = 4
                cols = st.columns(num_cols)
                for i, feature_col in enumerate(sorted(feature_cols_form)):
                    feature_name = feature_col.replace('feature_', '').replace('-', ' ').title()
                    if cols[i % num_cols].checkbox(feature_name, key=feature_col):
                        features_selecionadas.append(feature_col)

        submitted = st.form_submit_button("💰 Calcular Preço", use_container_width=True)

        if submitted:
            # Prepare input data for prediction
            input_data = {
                'area_total': [area_total], 
                'area_useful': [area_util],
                'bathrooms_count': [banheiros], 
                'bedrooms_count': [quartos],
                'garages_count': [garagens], 
                'suites_count': [suites],
                'location_neighborhood_name': [bairro_selecionado],
                'realtyType_name': [tipo_imovel_selecionado]
            }
            
            # Add feature columns
            if st.session_state.numerical_features:
                feature_cols_form = [col for col in st.session_state.numerical_features if col.startswith('feature_')]
                for col in feature_cols_form:
                    input_data[col] = [1 if col in features_selecionadas else 0]
            
            # Create DataFrame and ensure column order matches training data
            input_df = pd.DataFrame(input_data)
            # Reindex to match training data columns order
            input_df = input_df.reindex(columns=st.session_state.feature_names, fill_value=0)

            # Make prediction
            try:
                prediction = st.session_state.model.predict(input_df)
                
                # Display prediction result with enhanced formatting
                st.success(f"🎯 **Preço Estimado do Imóvel: R$ {prediction[0]:,.2f}**")
                st.caption("⚠️ Esta é uma estimativa baseada nos dados coletados e no modelo treinado. O valor real pode variar conforme condições específicas do imóvel e do mercado.")
                
                # Additional prediction insights
                with st.expander("📋 Detalhes da Predição"):
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.write(f"**🏠 Área Útil:** {area_util} m²")
                        st.write(f"**💰 Preço por m²:** R$ {prediction[0]/area_util:,.2f}/m²")
                        st.write(f"**📍 Bairro:** {bairro_selecionado}")
                        st.write(f"**🏗️ Tipo:** {tipo_imovel_selecionado}")
                        
                    with col_b:
                        st.write(f"**🛏️ Quartos:** {quartos}")
                        st.write(f"**🚿 Banheiros:** {banheiros}")
                        st.write(f"**🚗 Garagens:** {garagens}")
                        st.write(f"**🛏 Suítes:** {suites}")
                        
                    if features_selecionadas:
                        feature_names = [f.replace('feature_', '').replace('-', ' ').title() for f in features_selecionadas]
                        st.write(f"**✨ Características Especiais:** {', '.join(feature_names)}")
                
                # NOVA FUNCIONALIDADE: Recomendação de Imóveis Similares
                user_input_similarity = {
                    'bairro': bairro_selecionado,
                    'tipo_imovel': tipo_imovel_selecionado,
                    'area_useful': area_util,
                    'bedrooms_count': quartos,
                    'bathrooms_count': banheiros,
                    'garages_count': garagens
                }
                
                similar_properties = find_similar_properties(user_input_similarity, st.session_state.df_cleaned, top_n=3)
                
                if not similar_properties.empty:
                    st.subheader("✨ Encontramos estes imóveis similares para você:")
                    
                    for idx, imovel in similar_properties.iterrows():
                        col_info, col_link = st.columns([3, 1])
                        
                        with col_info:
                            preco = imovel.get('prices_rawPrice', 0)
                            area = imovel.get('area_useful', 0)
                            quartos_imovel = imovel.get('bedrooms_count', 0)
                            banheiros_imovel = imovel.get('bathrooms_count', 0)
                            
                            st.write(f"**💰 Preço:** R$ {preco:,.2f}")
                            st.write(f"**📏 Área:** {area:.0f} m² | **🛏️ Quartos:** {quartos_imovel:.0f} | **🚿 Banheiros:** {banheiros_imovel:.0f}")
                            
                            if area > 0:
                                preco_m2 = preco / area
                                st.write(f"**💱 Preço/m²:** R$ {preco_m2:,.2f}")
                        
                        with col_link:
                            property_url = imovel.get('property_url', '')
                            if property_url and pd.notna(property_url):
                                # Construir URL completa
                                url_completa = f"https://www.chavesnamao.com.br{property_url}"
                                st.markdown(f"[Ver anúncio]({url_completa})")
                            else:
                                st.write("Link indisponível")
                        
                        st.markdown("---")
                
            except Exception as e:
                st.error(f"❌ Erro ao calcular a predição: {e}")
                st.exception(e)

# Função principal do Streamlit
def main():
    st.set_page_config(layout="wide", page_title="Precificador de Imóveis")
    st.title("🏠 Precificador de Imóveis - Chaves na Mão")
    st.markdown("Sistema completo de análise de mercado imobiliário com machine learning.")

    # Inicializar session state
    initialize_session_state()

    # Criar abas - MODIFICADO: Adicionada quarta aba
    tab1, tab2, tab3, tab4 = st.tabs([
        "🔧 Coleta e Treinamento", 
        "📊 Análise de Mercado", 
        "🔎 Buscador de Imóveis",
        "💰 Calculadora de Preços"
    ])

    with tab1:
        aba_coleta_treinamento()

    with tab2:
        aba_analise_mercado()

    with tab3:
        aba_buscador_imoveis()

    with tab4:
        aba_calculadora()

if __name__ == '__main__':
    main()
