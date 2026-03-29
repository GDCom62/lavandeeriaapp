import streamlit as st
import pandas as pd
from datetime import datetime

# 1. Configuração de Página e Estilo
st.set_page_config(page_title="Lavo e Levo V18", page_icon="🧺", layout="wide")

# Estilo para melhorar a aparência (Botões maiores e cores)
st.markdown("""
    <style>
    .stButton>button { width: 100%; height: 3em; background-color: #f0f2f6; border-radius: 10px; }
    .stDownloadButton>button { background-color: #00ff00; }
    </style>
    """, unsafe_allow_html=True)

# 2. Conexão Segura
from streamlit_gsheets import GSheetsConnection

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # Tentativa de leitura robusta
    df = conn.read(ttl=0)
    st.sidebar.success("✅ Sistema Online")
except Exception as e:
    st.error("❌ Erro de Conexão com o Banco de Dados.")
    st.info("Verifique se o link nos Secrets termina com 'tqx=out:csv' e se a planilha é pública.")
    st.stop()

# 3. Estrutura de Dados
cols = ["id", "cli", "p_in", "status", "resp", "itens", "h_entrada"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

# 4. Fluxo e Itens
LISTA_ROUPAS = ["LENÇOL SOLTEIRO", "LENÇOL CASAL", "FRONHA", "TOALHA BANHO", "TOALHA ROSTO", "PISO", "COBERTOR", "EDREDOM"]
FLUXO = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]

st.title("🧺 LAVANDERIA LAVO E LEVO")

# Abas Principais
tab_op, tab_hist = st.tabs(["🚀 Operação Industrial", "📊 Relatório e Histórico"])

with tab_op:
    # Cadastro de Lote
    with st.expander("➕ Novo Recebimento", expanded=True):
        with st.form("novo_lote"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Hospital / Cliente:")
            peso = c2.number_input("Peso Entrada (kg):", 0.1)
            if st.form_submit_button("REGISTRAR ENTRADA"):
                if cli:
                    novo_id = f"{datetime.now().year}-{len(df)+1:03d}"
                    novo_row = pd.DataFrame([{
                        "id": novo_id, "cli": cli.upper(), "p_in": peso, 
                        "status": "Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                        "itens": "", "resp": ""
                    }])
                    df = pd.concat([df, novo_row], ignore_index=True)
                    conn.update(data=df)
                    st.rerun()

    # Fila de Trabalho Ativa
    st.subheader("📋 Lotes em Processo")
    ativos = df[df['status'] != "Entregue"]
    
    for i, row in ativos.iterrows():
        idx = df[df['id'] == row['id']].index
        with st.container(border=True):
            col_txt, col_act = st.columns([2, 1])
            
            with col_txt:
                st.subheader(f"{row['cli']} | Lote: {row['id']}")
                st.write(f"**Status:** `{row['status']}` | **Peso:** {row['p_in']}kg")
                if row['itens']: st.info(f"📦 Itens: {row['itens']}")

            with col_act:
                # Se estiver em fase de contagem, mostra seleção de itens
                if row['status'] in ["Passadeira", "Dobragem", "Contagem"]:
                    item = st.selectbox("Peça:", LISTA_ROUPAS, key=f"it_{row['id']}")
                    qtd = st.number_input("Qtd:", 1, key=f"qt_{row['id']}")
                    if st.button("➕ Add Peça", key=f"add_{row['id']}"):
                        df.at[idx, 'itens'] = str(row['itens']) + f"{item}:{qtd}; "
                        conn.update(data=df)
                        st.rerun()
                
                # Botão de Avanço Colorido
                if st.button(f"➡️ Mover para Próxima Etapa", key=f"nx_{row['id']}"):
                    curr_idx = FLUXO.index(row['status'])
                    df.at[idx, 'status'] = FLUXO[curr_idx + 1]
                    conn.update(data=df)
                    st.rerun()

with tab_hist:
    st.dataframe(df, use_container_width=True)
    if st.button("🚨 Limpar Lotes Entregues"):
        df = df[df['status'] != "Entregue"]
        conn.update(data=df)
        st.rerun()
