import streamlit as st
import streamlit_authenticator as stauth
import folium
import plotly.express as px
import pandas as pd
from streamlit_folium import folium_static
from pathlib import Path
from folium.plugins import HeatMap
import firebase_admin
from firebase_admin import credentials, firestore
import json
# ----------------------------------------
# Configuração de Autenticação (ATUALIZADA)
# ----------------------------------------
names = ["Guilherme Sitton","Agenor de Carvalho","Helana Onzi", "Márcio Onzi"]
usernames= ["GSitton","ACarvalho","HOnzi","MOnzi"]
# Pegando os valores diretamente dos secrets do Streamlit
secret_key = st.secrets["SECRET_KEY"]
hashed_passwords = st.secrets["HASH"]

authenticator = stauth.Authenticate(
    names, usernames, hashed_passwords, "Dados Rico", secret_key, cookie_expiry_days=7
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

        # 🔹 Inicializar Firebase no Streamlit
    if not firebase_admin._apps:
        # Carregar as credenciais JSON do Streamlit secrets
        
        # Em Dash.py, substitua:
        firebase_cred = st.secrets["firebase"]["credentials"]
        cred = credentials.Certificate(json.loads(firebase_cred))  # Remova replace()

    # Ou, carregue como dicionário diretamente:
        #cred = credentials.Certificate(st.secrets["firebase"].to_dict())
        
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # Função para carregar dados do Firestore
    def carregar_dados():
        docs = db.collection("dados").stream()
        dados = [doc.to_dict() for doc in docs]
        return pd.DataFrame(dados)

    df = carregar_dados()


    #arrumar colunas



    df = df[df["id"] != 19]
    df = df.dropna(subset=['Valor de venda'])
    df['Data Venda'] = pd.to_datetime(df['Data Venda'], dayfirst=True)
    df['Mês Venda'] = df['Data Venda'].dt.to_period('M').astype(str)

    # Limpeza dos valores
    df['Valor de venda'] = (
        df['Valor de venda']
            .str.strip()  # Remove espaços extras
            .str.replace(r'R\$|\.', '', regex=True)  # Remove "R$" e pontos de milhar
            .str.replace(',', '.')  # Substitui a vírgula decimal por ponto
            .astype(float)  # Converte para float
            .astype(int)  # Converte para int (removendo casas decimais)
    )

    # Dicionário com as coordenadas
    coordenadas = {
        "Caxias do Sul": (-29.1678, -51.1794),
        "Alta Feliz": (-29.3919, -51.3228),
        "Porto Alegre": (-30.0346, -51.2177),
        "Fazenda Souza": (-29.1833, -51.0500),
        "São Marcos": (-28.9675, -51.0678),
        "Antônio Prado": (-28.8563, -51.2789),
        "São Gabriel": (-30.3333, -54.3200),
        "Alvorada": (-29.9914, -51.0809),
        "Itati": (-29.4247, -50.1014),
        "Pinto Bandeira": (-29.0972, -51.4500),
        "Auriflama": (-20.6839, -50.5578),
        "Araraquara": (-21.7845, -48.1780),
        "Montenegro": (-29.6828, -51.4672),
        "Senador Canedo": (-16.7083, -49.0914),
        "São Simão": (-21.4736, -47.5511),
        "Goiânia": (-16.6864, -49.2643),
        "Flores da Cunha": (-29.0269, -51.1878),
        "Gavião Peixoto": (-21.8361, -48.4950),
        "Uruaçu": (-14.5233, -49.1397)
    }


    df['Latitude'] = df['Cidade'].map(lambda x: coordenadas.get(x, (None, None))[0])
    df['Longitude'] = df['Cidade'].map(lambda x: coordenadas.get(x, (None, None))[1])
    df = df.dropna(subset=['Latitude', 'Longitude'])

    # Filtros Interativos
    st.sidebar.header("Filtros")
    estados = st.sidebar.multiselect("Selecione os Estados", df['Estado'].unique(), key="estados")
    clientes = st.sidebar.multiselect("Selecione os Tipos de Clientes", df['Tipo Cliente'].unique(), key="clientes")
    produtos = st.sidebar.multiselect("Selecione os Produtos", df['Produto'].unique(), key="produtos")

    # Criação do filtro de data na sidebar
    start_date = st.sidebar.date_input("Data de Início", df['Data Venda'].min())
    end_date = st.sidebar.date_input("Data de Fim", df['Data Venda'].max())

    # Filtrando o dataframe com base nas datas selecionadas
    df_filtered = df[(df['Data Venda'] >= pd.to_datetime(start_date)) & (df['Data Venda'] <= pd.to_datetime(end_date))]

    # Aplicando os outros filtros
    if estados:
        df_filtered = df_filtered[df_filtered['Estado'].isin(estados)]
    if clientes:
        df_filtered = df_filtered[df_filtered['Tipo Cliente'].isin(clientes)]
    if produtos:
        df_filtered = df_filtered[df_filtered['Produto'].isin(produtos)]

    # Mapa de Calor
    st.header("Mapa de Calor de Vendas")
    m = folium.Map(location=[-15.788497, -47.879873], zoom_start=4)
    heat_data = [[row['Latitude'], row['Longitude'], row['Valor de venda']] for _, row in df_filtered.iterrows()]
    HeatMap(heat_data).add_to(m)
    folium_static(m)

    # Treemap das Top 10 CIDADEs
    st.header("Top 10 Cidades com Maiores Vendas")
    df_top10 = df_filtered.groupby('Cidade')['Valor de venda'].sum().reset_index()
    df_top10 = df_top10.sort_values(by='Valor de venda', ascending=False).head(10)
    fig_treemap = px.treemap(df_top10, path=['Cidade'], values='Valor de venda',
                          color='Valor de venda',
                          color_continuous_scale='blues')
    st.plotly_chart(fig_treemap)

    st.header("Tendência de Vendas ao Longo do Tempo")
    vendas_por_data = df_filtered.groupby('Data Venda').agg({'Valor de venda': 'sum'}).reset_index()
    fig = px.line(vendas_por_data, x='Data Venda', y='Valor de venda', title="Vendas ao Longo do Tempo")
    st.plotly_chart(fig)

    st.header("Distribuição de Vendas por Produto")
    vendas_por_produto = df_filtered.groupby('Produto').agg({'Valor de venda': 'sum'}).reset_index()
    fig = px.bar(vendas_por_produto, x='Produto', y='Valor de venda', title="Vendas por Produto")
    st.plotly_chart(fig)

    st.header("Distribuição de Vendas por Cliente")
    vendas_por_cliente = df_filtered.groupby('Cliente').agg({'Valor de venda': 'sum'}).reset_index()
    fig = px.pie(vendas_por_cliente, names='Cliente', values='Valor de venda', title="Vendas por Cliente")
    st.plotly_chart(fig)

    st.header("Tabela de Dados")
    st.write(df_filtered)
    st.write("Conteúdo restrito para usuários autenticados.")

elif authentication_status is False:
    st.error("Usuário/senha incorretos")
elif authentication_status is None:
    st.warning("Insira suas credenciais")
