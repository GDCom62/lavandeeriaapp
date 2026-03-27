import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Nome do arquivo de salvamento (simples para o Windows não bloquear)
ARQUIVO = "dados_lavanderia.csv"

# Função para carregar dados salvos
def carregar():
    if os.path.exists(ARQUIVO):
        try:
            return pd.read_csv(ARQUIVO).to_dict('records')
        except: return []
    return []

# Inicializa a memória
if "banco" not in st.session_state:
    st.session_state.banco = carregar()

st.title("🧺 LAVO E LEVO")

# --- CADASTRO ---
with st.expander("➕ NOVO RECEBIMENTO", expanded=True):
    cli = st.text_input("Cliente:")
    peso = st.number_input("Peso (kg):", 0.1)
    if st.button("SALVAR"):
        if cli:
            novo = {"cli": cli.upper(), "p_in": peso, "status": "Lavagem", "data": datetime.now().strftime("%H:%M")}
            st.session_state.banco.append(novo)
            pd.DataFrame(st.session_state.banco).to_csv(ARQUIVO, index=False)
            st.success("Salvo com sucesso!")
            st.rerun()

st.write("---")

# --- LISTA ---
for i, item in enumerate(st.session_state.banco):
    if item['status'] != "Entregue":
        with st.container(border=True):
            st.write(f"**{item['cli']}** | Status: `{item['status']}`")
            if st.button(f"Avançar Lote {i}", key=f"b{i}"):
                fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]
                item['status'] = fluxo[fluxo.index(item['status']) + 1]
                pd.DataFrame(st.session_state.banco).to_csv(ARQUIVO, index=False)
                st.rerun()

if st.checkbox("📊 Ver Relatório"):
    st.dataframe(pd.DataFrame(st.session_state.banco))
