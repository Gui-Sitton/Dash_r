import streamlit as st
import streamlit_authenticator as stauth
import folium
import plotly.express as px
import pandas as pd
from streamlit_folium import folium_static
import json
from pathlib import Path
from folium.plugins import HeatMap
import cx_Oracle
import os
from dotenv import load_dotenv
# ----------------------------------------
# Configuração de Autenticação (ATUALIZADA)
# ----------------------------------------
names = ["Guilherme Sitton"]
usernames= ["GSitton"]
# Pegando os valores diretamente dos secrets do Streamlit
secret_key = st.secrets["SECRET_KEY"]
hashed_passwords = st.secrets["HASH"]

authenticator = stauth.Authenticate(
    names, usernames, hashed_passwords, "Dados Rico", "abcdef", cookie_expiry_days=7
)

# ----------------------------------------
# Login
# ----------------------------------------
name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status:
    authenticator.logout("Logout", "sidebar")
    st.sidebar.success(f"Bem-vindo, {name}!")

    # Adicione seu dashboard aqui
    st.title("Dados Rico")

    # Credenciais do Banco
    USER = st.secrets["ORACLE_USER"]
    PASSWORD = st.secrets["ORACLE_PASSWORD"]
    DSN = st.secrets["ORACLE_DSN"]
    
    # Conectar ao Oracle
    def conectar_oracle():
        conn = cx_Oracle.connect(USER, PASSWORD, DSN)
        return conn

    # Consulta SQL
    def buscar_dados():
        conn = conectar_oracle()
        df = pd.read_sql("SELECT * FROM VENDAS_RICO", conn)
        conn.close()
        return df
    df = buscar_dados()

    #arrumar colunas



    df = df[df["ID"] != 19]
    df = df.dropna(subset=['VALOR_DE_VENDA'])
    df['DATA_VENDA'] = pd.to_datetime(df['DATA_VENDA'], dayfirst=True)
    df['MES_VENDA'] = df['DATA_VENDA'].dt.to_period('M').astype(str)

    # Limpeza dos valores
    df['VALOR_DE_VENDA'] = (
        df['VALOR_DE_VENDA']
            .str.strip()  # Remove espaços extras
            .str.replace(r'R\$|\.', '', regex=True)  # Remove "R$" e pontos de milhar
            .str.replace(',', '.')  # Substitui a vírgula decimal por ponto
            .astype(float)  # Converte para float
            .astype(int)  # Converte para int (removendo casas decimais)
    )

    # Dicionário com as coordenadas
    coordenadas = {
        "Araraquara": (-21.7944, -48.1756),
        "Fazenda Souza": (-29.0940, -51.1790),
        "Antonio Prado": (-28.8583, -51.2883),
        "Sao Gabriel": (-30.3333, -54.3167),
        "Caxias do Sul": (-29.1678, -51.1794),
        "Alta Feliz": (-29.3825, -51.3125),
        "Itati": (-29.4972, -50.1014),
        "Sao Marcos": (-28.9678, -51.0697),
        "Montenegro": (-29.6828, -51.4678),
        "Senador Canedo": (-16.7086, -49.0917),
        "Sao Simao": (-18.9969, -50.5478),
        "Goiania": (-16.6864, -49.2643),
        "Pinto Bandeira": (-29.0994, -51.4508),
        "Auriflama": (-20.6831, -50.5578),
        "Alvorada": (-29.9911, -51.0803),
        "Porto Alegre": (-30.0346, -51.2177),
        "Gaviao Peixoto": (-21.8361, -48.4958),
        "Uruacu": (-14.5236, -49.1397)
    }

    df['Latitude'] = df['CIDADE'].map(lambda x: coordenadas.get(x, (None, None))[0])
    df['Longitude'] = df['CIDADE'].map(lambda x: coordenadas.get(x, (None, None))[1])
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Filtros Interativos
    st.sidebar.header("Filtros")
    estados = st.sidebar.multiselect("Selecione os Estados", df['ESTADO'].unique(), key="estados")
    clientes = st.sidebar.multiselect("Selecione os Tipos de Clientes", df['TIPO_CLIENTE'].unique(), key="clientes")
    produtos = st.sidebar.multiselect("Selecione os Produtos", df['PRODUTO'].unique(), key="produtos")

    # Criação do filtro de data na sidebar
    start_date = st.sidebar.date_input("Data de Início", df['DATA_VENDA'].min())
    end_date = st.sidebar.date_input("Data de Fim", df['DATA_VENDA'].max())

    # Filtrando o dataframe com base nas datas selecionadas
    df_filtered = df[(df['DATA_VENDA'] >= pd.to_datetime(start_date)) & (df['DATA_VENDA'] <= pd.to_datetime(end_date))]

    # Aplicando os outros filtros
    if estados:
        df_filtered = df_filtered[df_filtered['ESTADO'].isin(estados)]
    if clientes:
        df_filtered = df_filtered[df_filtered['TIPO_CLIENTE'].isin(clientes)]
    if produtos:
        df_filtered = df_filtered[df_filtered['PRODUTO'].isin(produtos)]

    # Mapa de Calor
    st.header("Mapa de Calor de Vendas")
    m = folium.Map(location=[-15.788497, -47.879873], zoom_start=4)
    heat_data = [[row['Latitude'], row['Longitude'], row['VALOR_DE_VENDA']] for _, row in df_filtered.iterrows()]
    HeatMap(heat_data).add_to(m)
    folium_static(m)

    # Treemap das Top 10 CIDADEs
    st.header("Top 10 CIDADEs com Maiores Vendas")
    df_top10 = df_filtered.groupby('CIDADE')['VALOR_DE_VENDA'].sum().reset_index()
    df_top10 = df_top10.sort_values(by='VALOR_DE_VENDA', ascending=False).head(10)
    fig_treemap = px.treemap(df_top10, path=['CIDADE'], values='VALOR_DE_VENDA',
                          color='VALOR_DE_VENDA',
                          color_continuous_scale='blues')
    st.plotly_chart(fig_treemap)

    st.header("Tendência de Vendas ao Longo do Tempo")
    vendas_por_data = df_filtered.groupby('DATA_VENDA').agg({'VALOR_DE_VENDA': 'sum'}).reset_index()
    fig = px.line(vendas_por_data, x='DATA_VENDA', y='VALOR_DE_VENDA', title="Vendas ao Longo do Tempo")
    st.plotly_chart(fig)

    st.header("Distribuição de Vendas por Produto")
    vendas_por_produto = df_filtered.groupby('PRODUTO').agg({'VALOR_DE_VENDA': 'sum'}).reset_index()
    fig = px.bar(vendas_por_produto, x='PRODUTO', y='VALOR_DE_VENDA', title="Vendas por Produto")
    st.plotly_chart(fig)

    st.header("Distribuição de Vendas por Cliente")
    vendas_por_cliente = df_filtered.groupby('CLIENTE').agg({'VALOR_DE_VENDA': 'sum'}).reset_index()
    fig = px.pie(vendas_por_cliente, names='CLIENTE', values='VALOR_DE_VENDA', title="Vendas por Cliente")
    st.plotly_chart(fig)

    st.header("Tabela de Dados")
    st.write(df_filtered)
    st.write("Conteúdo restrito para usuários autenticados.")

elif authentication_status is False:
    st.error("Usuário/senha incorretos")
elif authentication_status is None:
    st.warning("Insira suas credenciais")
