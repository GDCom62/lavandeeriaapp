import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página e Estilo (Aparência Profissional)
st.set_page_config(page_title="Lavo e Levo V22", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; background-color: #007bff; color: white; font-weight: bold; }
    .stContainer { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧺 LAVANDERIA LAVO E LEVO - V22")

# 2. Conexão Blindada com Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
    st.sidebar.success("✅ Banco de Dados Conectado")
except Exception as e:
    st.error("❌ Erro de Conexão. Verifique os Secrets e a Planilha.")
    st.stop()

# Garantir colunas
cols = ["id", "cli", "p_in", "p_out", "status", "resp", "itens", "mot", "h_in"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

# 3. Operação (Fluxo de 7 Etapas)
tab_op, tab_rel = st.tabs(["🚀 Operação Industrial", "📊 Relatórios"])

with tab_op:
    with st.expander("➕ Novo Recebimento", expanded=True):
        with st.form("entrada", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("Hospital / Cliente:")
            peso = c2.number_input("Peso Entrada (kg):", 0.1)
            if st.form_submit_button("REGISTRAR LOTE"):
                if cliente:
                    novo_id = f"{datetime.now().year}-{len(df)+1:03d}"
                    novo_lote = pd.DataFrame([{
                        "id": novo_id, "cli": cliente.upper(), "p_in": peso, "p_out": 0.0,
                        "status": "Lavagem", "resp": "", "itens": "", "mot": "", 
                        "h_in": datetime.now().strftime("%H:%M")
                    }])
                    df = pd.concat([df, novo_lote], ignore_index=True)
                    conn.update(data=df)
                    st.rerun()

    # Fila de Trabalho
    st.subheader("📋 Lotes em Processamento")
    ativos = df[df['status'] != "Entregue"]
    
    for i, row in ativos.iterrows():
        idx = df[df['id'] == row['id']].index
        with st.container():
            col_info, col_btn = st.columns([3, 1])
            col_info.write(f"### {row['cli']} | Lote: {row['id']}")
            col_info.write(f"**Etapa:** `{row['status']}` | **Peso:** {row['p_in']}kg")
            
            # Botão de Avanço
            if col_btn.button(f"➡️ Avançar", key=f"next_{row['id']}"):
                fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]
                prox = fluxo[fluxo.index(row['status']) + 1]
                df.at[idx, 'status'] = prox
                conn.update(data=df)
                st.rerun()

with tab_rel:
    st.dataframe(df, use_container_width=True)
