import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página e Estética Industrial
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #007bff; color: white; font-weight: bold; }
    .stContainer { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f9f9f9; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧺 LAVANDERIA LAVO E LEVO - V26")

# 2. CONEXÃO API (Leitura e Escrita)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
    st.sidebar.success("✅ API CONECTADA")
except Exception as e:
    st.error("❌ Erro de API: Verifique os Secrets e se a planilha está como EDITOR.")
    st.stop()

# Garantir colunas básicas
cols = ["id", "cli", "p_in", "status", "resp", "itens", "h_in"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

# 3. OPERAÇÃO (O Fluxo que você aprovou)
tab1, tab2 = st.tabs(["🚀 Operação (7 Etapas)", "📊 Relatórios"])

with tab1:
    # Cadastro
    with st.expander("➕ Novo Recebimento", expanded=True):
        with st.form("entrada", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cliente = c1.text_input("Hospital / Cliente:")
            peso = c2.number_input("Peso (kg):", 0.1)
            if st.form_submit_button("REGISTRAR LOTE"):
                if cliente:
                    novo_id = f"{datetime.now().year}-{len(df)+1:03d}"
                    novo = pd.DataFrame([{"id": novo_id, "cli": cliente.upper(), "p_in": peso, "status": "Lavagem", "h_in": datetime.now().strftime("%H:%M")}])
                    df = pd.concat([df, novo], ignore_index=True)
                    conn.update(data=df)
                    st.rerun()

    # Fila de Trabalho
    st.subheader("📋 Lotes em Processo")
    for i, row in df[df['status'] != "Entregue"].iterrows():
        idx = df[df['id'] == row['id']].index
        with st.container():
            col_info, col_act = st.columns()
            col_info.write(f"### {row['cli']} | Lote: {row['id']}")
            col_info.write(f"**Etapa:** `{row['status']}` | **Peso:** {row['p_in']}kg")
            
            # Escolha do Colaborador para a próxima fase
            fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]
            proxima = fluxo[fluxo.index(row['status']) + 1]
            novo_resp = col_act.text_input("Quem assume?", key=f"resp_{row['id']}")
            
            if col_act.button(f"➡️ Mover p/ {proxima}", key=f"btn_{row['id']}"):
                if novo_resp:
                    df.at[idx, 'status'] = proxima
                    df.at[idx, 'resp'] = novo_resp
                    conn.update(data=df)
                    st.rerun()
                else:
                    st.warning("Digite o nome do responsável!")

with tab2:
    st.write("**Histórico Geral:**")
    st.dataframe(df, use_container_width=True)
