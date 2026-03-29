import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração Visual
st.set_page_config(page_title="Lavo e Levo V24", page_icon="🧺", layout="wide")

# --- CONEXÃO DIRETA (MUDA O ID ABAIXO) ---
ID_PLANILHA = "COLE_AQUI_O_ID_DA_SUA_PLANILHA"
URL_CSV = f"https://docs.google.com{ID_PLANILHA}/export?format=csv"

@st.cache_data(ttl=0)
def carregar_dados():
    try:
        return pd.read_csv(URL_CSV)
    except:
        return pd.DataFrame(columns=["id", "cli", "p_in", "status", "resp", "itens", "h_in"])

df = carregar_dados()

st.title("🧺 LAVANDERIA LAVO E LEVO - V24")

if not df.empty:
    st.sidebar.success("✅ PLANILHA CONECTADA")
else:
    st.sidebar.error("❌ ERRO DE CONEXÃO")
    st.stop()

# --- OPERAÇÃO (FLUXO 7 ETAPAS) ---
tab1, tab2 = st.tabs(["🚀 Operação", "📊 Relatórios"])

with tab1:
    with st.expander("➕ NOVO RECEBIMENTO", expanded=True):
        cli = st.text_input("Hospital:")
        peso = st.number_input("Peso (kg):", 0.1)
        if st.button("GERAR LOTE"):
            st.info("Para GRAVAR, use o link de formulário do Google ou a Service Account. Este modo é para LEITURA estável.")

    st.subheader("📋 Fila de Trabalho")
    for i, row in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            col_a, col_b = st.columns([3,1])
            col_a.write(f"**Lote: {row['id']} - {row['cli']}**")
            col_a.caption(f"Etapa: {row['status']} | Peso: {row['p_in']}kg")
            
            # Navegação de Etapas
            fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]
            if row['status'] in fluxo:
                if col_b.button(f"➡️ Próxima", key=f"btn_{i}"):
                    st.warning("Botão de ação: Requer permissão de escrita JSON.")

with tab2:
    st.write("**Histórico de Produção:**")
    st.dataframe(df)
