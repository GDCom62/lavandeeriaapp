import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configuração que evita erros de rede
st.set_page_config(page_title="Lavo e Levo V5", layout="wide")

st.title("🧺 LAVANDERIA LAVO E LEVO - V5")

# Tenta a conexão oficial
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Lendo a planilha (força leitura sem cache)
    df = conn.read(ttl=0)
    st.success("✅ CONEXÃO ESTABELECIDA!")
except Exception as e:
    st.error(f"❌ ERRO DE CONEXÃO: {e}")
    st.info("Acesse sua planilha, clique em COMPARTILHAR e mude para QUALQUER PESSOA COM O LINK -> EDITOR.")
    st.stop()

# --- OPERAÇÃO SIMPLIFICADA PARA TESTE ---
with st.form("teste_entrada"):
    cliente = st.text_input("Nome do Cliente para Teste:")
    if st.form_submit_button("SALVAR TESTE"):
        if cliente:
            # Cria um novo dado
            novo_df = pd.DataFrame([{"cli": cliente.upper(), "status": "Lavagem"}])
            # Tenta salvar na planilha
            df_final = pd.concat([df, novo_df], ignore_index=True)
            conn.update(data=df_final)
            st.rerun()

st.write("---")
st.subheader("Dados da Planilha:")
st.dataframe(df)
