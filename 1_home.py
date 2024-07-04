import streamlit as st
import pandas as pd
import plotly.express as px
import webbrowser
import gspread
from oauth2client.service_account import ServiceAccountCredentials

if 'data' not in st.session_state:
    imoveis_df = pd.read_csv('imoveis_chaves_na_mao_limpos.csv', index_col=0)
    st.session_state['data'] = imoveis_df

if 'data2' not in st.session_state:
    para_alugar_df = pd.read_csv('imoveis_para_aluguel_chaves_e_zap.csv', index_col=0)
    st.session_state['data2'] = para_alugar_df

if 'user' not in st.session_state:
    CLIENT_SECRET_FILE = 'client_secret.json'
    scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CLIENT_SECRET_FILE, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open('DB_users').worksheet("pgn1")
    users = spreadsheet.get_all_records()
    st.session_state['user'] = users

st.sidebar.markdown("Desenvolvido por [Felipe Gabriel](https://www.linkedin.com/in/felipe-gabriel0/)")

st.markdown(""" # Projeto Imóveis Floripa

Introdução: Esse projeto consiste em fazer do zero uma análise em Python do mercado imobiliário de Florianópolis, Santa Catarina.
Os dados são públicos e foram coletados no dia 23/06/2024 dos portais [chaves na mao](https://www.chavesnamao.com.br/) e [zap imoveis](https://www.zapimoveis.com.br/), portanto estão sujeitos a oscilações de preços.

Avisos: 
- Esse projeto é para fins educacionais apenas! Não visando o lucro e portanto não me responsabilizo por quaisquer decisões que venham a ser tomadas pelos usuários. Faça sua própria pesquisa.
- Em caso de erros no app, retorne para a home.
            
## Ele está dividido em 5 Partes (ainda a serem gravadas)
            
- Parte 1: Coleta dos dados dos sites [Parte 1](link_youtube). 
- Parte 2: Coleta de estabelecimentos no Places API do Google Maps [Parte 2](link_youtube). 
- Parte 3: Data Cleaning + EDA [Parte 3](link_youtube). 
- Parte 4: Análise e Regressão de preços e aluguéis dos imóveis com Pycaret [Parte 4](link_youtube). 
- Parte 5: Dashboards em Streamlit com estatísticas e ferramenta de buscas [Parte 5](link_youtube). 

Abaixo, teremos uma breve __Análise Exploratória__  dos dados de imóveis na região
""")

imoveis_df = st.session_state['data']

df = imoveis_df[['area', 'preço', 'tipo', 'bairro' ]].copy()
cols_with_sum_10 = []
for index in df['tipo'].value_counts().index:
    if df['tipo'].value_counts()[index] > 20:
        cols_with_sum_10.append(index)
df = df[df['tipo'].isin(cols_with_sum_10)]

df['tipo'] = df['tipo'].replace({'flat': 'apartamento',
                                 'loft': 'apartamento',
                                 'cobertura':'apartamento',
                                 'kitnet':'apartamento',
                                 'casa-em-condominio': 'casa',
                                 'casa-comercial': 'casa',
                                 'fazenda': 'casa',
                                 'chacara': 'casa',
                                 'terreno-em-condominio': 'terreno',
                                 'terreno-comercial': 'terreno',
                                 'sala-comercial':'ponto-comercial',
})

para_alugar_df = st.session_state['data2']
df2 = para_alugar_df[['area', 'preço', 'tipo', 'bairro' ]].copy()

cols_with_sum_10 = []
for index in df2['tipo'].value_counts().index:
    if df2['tipo'].value_counts()[index] > 20:
        cols_with_sum_10.append(index)
df2 = df2[df2['tipo'].isin(cols_with_sum_10)]

df2['tipo'] = df2['tipo'].replace({'flat': 'apartamento',
                                 'loft': 'apartamento',
                                 'cobertura':'apartamento',
                                 'kitnet':'apartamento',
                                 'casa-em-condominio': 'casa',
                                 'casa-comercial': 'casa',
                                 'fazenda': 'casa',
                                 'chacara': 'casa',
                                 'terreno-em-condominio': 'terreno',
                                 'terreno-comercial': 'terreno',
                                 'sala-comercial':'ponto-comercial',
})



fig1 = px.sunburst(df, path=['tipo', 'bairro'])
mean_price_df = df.groupby(['tipo','bairro'])['preço'].median().reset_index()
mean_price_df = mean_price_df.sort_values('preço', ascending=False)
fig2 = px.sunburst(mean_price_df, path=['tipo', 'bairro'], values='preço')

fig3 = px.sunburst(df2, path=['tipo', 'bairro'])
mean_price_df = df2.groupby(['tipo','bairro'])['aluguel_total'].median().reset_index()
mean_price_df = mean_price_df.sort_values('aluguel_total', ascending=False)
fig4 = px.sunburst(mean_price_df, path=['tipo', 'bairro'], values='aluguel_total')

from plotly.subplots import make_subplots
fig = make_subplots(rows=2, cols=2, specs=[[{"type": "sunburst"}, {"type": "sunburst"}],
                                            [{"type": "sunburst"}, {"type": "sunburst"}]],
                    subplot_titles=('Bairros com mais Imóveis à venda', 
                                    'Bairros mais caros à venda (mediana)', 
                                    'Bairros com mais Imóveis para aluguel', 
                                    'Bairros com aluguel mais caros (mediana)'))
fig.add_trace(fig1.data[0], row=1, col=1)
fig.add_trace(fig2.data[0], row=1, col=2)
fig.add_trace(fig3.data[0], row=2, col=1)
fig.add_trace(fig4.data[0], row=2, col=2)

fig.update_layout(
    autosize=True,
    width=800,  # adjust the width as needed
    height=800,  # adjust the height as needed
)
st.plotly_chart(fig, use_container_width=True)

