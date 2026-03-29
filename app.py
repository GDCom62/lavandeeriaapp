import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Configuração de Página e Estilo Visual (Cores e Botões Grandes)
st.set_page_config(page_title="Lavo e Levo V20", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3.5em; font-weight: bold; border: 2px solid #007bff; }
    .stExpander { border: 1px solid #007bff; border-radius: 10px; background-color: white; }
    [data-testid="stMetricValue"] { color: #007bff; }
    </style>
    """, unsafe_allow_html=True)

# 2. Conexão Direta (Blindada)
from streamlit_gsheets import GSheetsConnection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    st.sidebar.success("✅ SISTEMA CONECTADO")
except Exception as e:
    st.error("❌ ERRO 404: O GOOGLE BLOQUEOU O ACESSO.")
    st.info("💡 SOLUÇÃO: Na planilha, clique em ARQUIVO -> COMPARTILHAR -> PUBLICAR NA WEB. Depois clique em PUBLICAR.")
    st.stop()

# 3. Cabeçalhos e Fluxo
if df is None or df.empty:
    df = pd.DataFrame(columns=["id", "cli", "p_in", "status", "itens", "data"])

FLUXO = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]

st.title("🧺 LAVANDERIA LAVO E LEVO - V20")
st.write("---")

# 4. OPERAÇÃO (Design Melhorado)
col_input, col_fila = st.columns([1, 2])

with col_input:
    st.subheader("➕ Novo Lote")
    with st.form("entrada", clear_on_submit=True):
        cli = st.text_input("Hospital / Cliente:")
        peso = st.number_input("Peso (kg):", 0.1)
        if st.form_submit_button("REGISTRAR ENTRADA"):
            if cli:
                novo_id = f"{datetime.now().year}-{len(df)+1:03d}"
                novo_dado = pd.DataFrame([{"id": novo_id, "cli": cli.upper(), "p_in": peso, "status": "Lavagem", "data": datetime.now().strftime("%H:%M"), "itens": ""}])
                df = pd.concat([df, novo_dado], ignore_index=True)
                conn.update(data=df)
                st.rerun()

with col_fila:
    st.subheader("📋 Fila Ativa")
    ativos = df[df['status'] != "Entregue"]
    
    for i, row in ativos.iterrows():
        idx_planilha = df[df['id'] == row['id']].index
        with st.container(border=True):
            c1, c2 = st.columns([2, 1])
            c1.markdown(f"### {row['cli']}")
            c1.write(f"**Lote:** {row['id']} | **Peso:** {row['p_in']}kg")
            c1.info(f"📍 Etapa: **{row['status']}**")
            
            # Botão de Avanço Estilizado
            if c2.button(f"➡️ AVANÇAR", key=f"btn_{row['id']}"):
                proxima = FLUXO[FLUXO.index(row['status']) + 1]
                df.at[idx_planilha, 'status'] = proxima
                conn.update(data=df)
                st.rerun()
            
            # Área de Peças (Só aparece no processamento)
            if row['status'] in ["Passadeira", "Dobragem", "Contagem"]:
                peca = st.text_input("Peça:", key=f"p_{row['id']}")
                if st.button("➕ Add", key=f"add_{row['id']}"):
                    df.at[idx_planilha, 'itens'] = str(row['itens']) + f"{peca}; "
                    conn.update(data=df)
                    st.rerun()
