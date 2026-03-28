import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Lavo e Levo - Cloud", page_icon="🧺", layout="wide")

# Conectando com a Planilha Google
# Você precisará configurar o link da planilha no menu "Secrets" do Streamlit Cloud
conn = st.connection("gsheets", type=GSheetsConnection)

# Carrega os dados existentes na planilha
df = conn.read(ttl="0") # ttl="0" força a leitura de dados novos toda vez

st.title("🧺 LAVANDERIA LAVO E LEVO - BANCO DE DADOS NUVEM")

# --- FUNÇÃO PARA SALVAR NA PLANILHA ---
def salvar_mudancas(dataframe):
    conn.update(data=dataframe)
    st.cache_data.clear()

# --- OPERAÇÃO ---
with st.expander("➕ NOVO LOTE (RECEBIMENTO)", expanded=True):
    with st.form("entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cli = col1.text_input("Cliente:")
        p_in = col2.number_input("Peso Entrada (kg):", 0.1)
        r1 = col1.text_input("Responsável Lavagem:")
        if st.form_submit_button("REGISTRAR NA PLANILHA"):
            if cli and r1:
                novo_id = len(df) + 1
                novo_dado = pd.DataFrame([{
                    "id": novo_id, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0,
                    "status": "Lavagem", "resp": r1, "entrada": "", "saida": "", 
                    "mot": "", "h_in": datetime.now().strftime("%H:%M"), "gaiola": ""
                }])
                df_atualizado = pd.concat([df, novo_dado], ignore_index=True)
                salvar_mudancas(df_atualizado)
                st.rerun()

st.write("---")
# FILA DE TRABALHO (Exemplo de avanço de etapa)
st.subheader("📋 Lotes Ativos")
df_ativos = df[df['status'] != "Entregue"]

for i, row in df_ativos.iterrows():
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** | Status: `{row['status']}`")
        if st.button(f"Avançar Lote {row['id']}", key=f"btn{row['id']}"):
            fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]
            idx = fluxo.index(row['status'])
            df.at[i, 'status'] = fluxo[idx + 1]
            salvar_mudancas(df)
            st.rerun()

if st.checkbox("📊 Ver Planilha Completa"):
    st.dataframe(df)
