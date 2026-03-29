import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Lavo e Levo V22", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    .stContainer { border: 1px solid #ddd; padding: 10px; border-radius: 10px; margin-bottom: 10px; background-color: #f9f9f9; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO DIRETA SEM SECRETS ---
# COPIE O ID DA SUA PLANILHA E COLE ABAIXO:
ID_PLANILHA = "COLE_AQUI_O_ID_DA_SUA_PLANILHA" 
URL_CSV = f"https://docs.google.com{ID_PLANILHA}/export?format=csv"

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        return pd.read_csv(URL_CSV)
    except Exception as e:
        st.error(f"Erro ao ler planilha: {e}")
        return pd.DataFrame(columns=["id", "cli", "p_in", "status", "resp", "data"])

df = carregar_dados()

st.title("🧺 LAVANDERIA LAVO E LEVO - V22")
st.write("---")

if df.empty:
    st.warning("⚠️ Planilha vazia ou link incorreto. Verifique o ID no código.")
else:
    st.success("✅ CONEXÃO ESTABELECIDA!")

# --- OPERAÇÃO ---
with st.expander("➕ NOVO LOTE", expanded=True):
    with st.form("entrada"):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente:")
        peso = c2.number_input("Peso (kg):", 0.1)
        if st.form_submit_button("REGISTRAR"):
            st.info("Para gravar dados na nuvem com segurança total, precisamos da chave JSON. Por enquanto, teste a LEITURA acima.")

st.write("---")
st.subheader("📋 Lotes na Planilha")
st.dataframe(df, use_container_width=True)
