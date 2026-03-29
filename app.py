import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração de Página
st.set_page_config(page_title="Lavo e Levo V5", layout="wide")

# TITULO PARA SABER QUE O CODIGO NOVO CARREGOU
st.title("🧺 LAVANDERIA LAVO E LEVO - V5 (MODO RECUPERAÇÃO)")

# Tenta carregar a planilha via Pandas (Modo mais simples que existe)
# Substitua o ID abaixo pelo ID da sua planilha (o código entre /d/ e /edit)
ID_PLANILHA = "COLE_AQUI_O_ID_DA_SUA_PLANILHA"
URL = f"https://docs.google.com{ID_PLANILHA}/export?format=csv"

try:
    df = pd.read_csv(URL)
    st.success("✅ CONEXÃO COM A PLANILHA OK!")
except Exception as e:
    st.error("❌ AINDA SEM CONEXÃO: O Google está bloqueando o acesso.")
    st.info("Certifique-se de que a planilha foi 'Publicada na Web' e o link está correto.")
    st.stop()

# --- OPERAÇÃO ---
with st.expander("➕ NOVO LOTE", expanded=True):
    cli = st.text_input("Cliente:")
    peso = st.number_input("Peso (kg):", 0.1)
    if st.button("REGISTRAR"):
        # No modo público, o Streamlit só consegue LER. 
        # Para GRAVAR, precisamos da conexão GSheets ativa.
        st.warning("Conexão de leitura estabelecida. Para gravar, o erro 404 nos Secrets precisa ser resolvido.")

st.write("---")
st.subheader("Dados da Planilha:")
st.dataframe(df)
