import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página
st.set_page_config(page_title="Lavo e Levo V19", layout="wide")

st.title("🧺 LAVANDERIA LAVO E LEVO - V19")

# 2. Conexão Direta
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lendo sem cache para forçar a conexão
    df = conn.read(ttl=0)
    st.sidebar.success("✅ CONECTADO!")
except Exception as e:
    st.error(f"❌ ERRO 404: O sistema não encontrou a planilha.")
    st.info("Acesse os 'Secrets' no Streamlit Cloud e verifique se o link termina em /edit#gid=0")
    st.stop()

# 3. Operação Simples
st.subheader("🚀 Operação Ativa")
if not df.empty:
    st.dataframe(df, use_container_width=True)
else:
    st.info("A planilha está conectada, mas não há dados nela.")

# Botão de Teste para Gravar
if st.button("SALVAR TESTE DE CONEXÃO"):
    novo_dado = pd.DataFrame([{"id": len(df)+1, "cli": "TESTE", "status": "Lavagem"}])
    df_final = pd.concat([df, novo_dado], ignore_index=True)
    conn.update(data=df_final)
    st.success("Dados gravados na planilha!")
    st.rerun()
