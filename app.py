import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

# Estilo Industrial
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .status-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f8f9fa; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧺 SISTEMA LAVANDERIA - V26")

# 2. Conexão com Google Sheets
# Substitua o link abaixo pelo link da sua planilha se não estiver nas Secrets
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_PLANILHA, ttl="0")
    
    # Garantir que colunas essenciais existam
    cols_necessarias = ["id", "cli", "p_in", "status", "maquina", "resp", "detalhe_itens", "h_in", "etapa_inicio"]
    for col in cols_necessarias:
        if col not in df.columns:
            df[col] = None
            
    st.sidebar.success("✅ Sistema Online")
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

# 3. Navegação por Abas
tab1, tab2, tab3, tab4 = st.tabs(["📥 Entrada", "🧼 Lavagem (Máquinas)", "🚀 Fluxo de Produção", "📊 Histórico"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("novo_lote", clear_on_submit=True):
        st.subheader("Registrar Novo Lote")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome do Hospital / Cliente")
        peso = c2.number_input("Peso Total (kg)", 0.1)
        obs_ini = st.text_input("Observação de Entrada")
        
        if st.form_submit_button("GERAR LOTE"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo_lote = pd.DataFrame([{
                    "id": novo_id, 
                    "cli": cliente.upper(), 
                    "p_in": peso, 
                    "status": "Aguardando Lavagem",
                    "h_in": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(),
                    "detalhe_itens": obs_ini
                }])
                df = pd.concat([df, novo_lote], ignore_index=True)
                conn.update(data=df)
                st.success(f"Lote {novo_id} criado!")
                st.rerun()

# --- ABA 2: MÁQUINAS (LAVAGEM CONJUNTA) ---
with tab2:
    st.subheader("Gestão de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    
    if not espera.empty:
        c1, c2 = st.columns([2, 1])
        lotes_selecionados = c1.multiselect(
            "Selecione os lotes para a mesma máquina:", 
            espera['id'].tolist(),
            format_func=lambda x: f"ID {x} - {df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)"
        )
        
        maquina = c2.selectbox("Máquina:", ["MÁQUINA 01", "MÁQUINA 02", "MÁQUINA 03", "MÁQUINA 04"])
        operador = c2.text_input("Operador da Lavagem", key="op_lav")

        if st.button("🚀 INICIAR LAVAGEM CONJUNTA"):
            if lotes_selecionados and operador:
                for lid in lotes_selecionados:
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'] = "Secagem" # Move para a próxima etapa após lavagem
                    df.loc[idx, 'maquina'] = maquina
                    df.loc[idx, 'resp'] = operador.upper()
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                
                conn.update(data=df)
                st.balloons()
                st.rerun()
            else:
                st.warning("Selecione os lotes e informe o operador!")
    else:
        st.info("Nenhum lote aguardando lavagem.")

# --- ABA 3: FLUXO DE PRODUÇÃO (TIME REAL) ---
with tab3:
    st.subheader("Acompanhamento de Etapas")
    # Filtra o que está em processo (exceto entrada e entregue)
    em_processo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue"])]
    
    fluxo_etapas = ["Secagem", "Passadeira", "Dobragem", "Empacotamento", "Gaiola", "Entregue"]

    for i, row in em_processo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            col_info, col_tempo, col_acao = st.columns([2, 1, 2])
            
            # Info do Lote
            col_info.markdown(f"**{row['cli']}** (ID: {row['id']})")
            col_info.caption(f"Status Atual: `{row['status']}` | Máquina: {row.get('maquina', 'N/A')}")
            
            # Cronômetro
            inicio = datetime.fromisoformat(str(row['etapa_inicio']))
            decorrido = (datetime.now() - inicio).total_seconds() // 60
            col_tempo.metric("⏱️ Tempo", f"{int(decorrido)} min")
            
            # Ação de Avanço
            idx_atual = fluxo_etapas.index(row['status']) if row['status'] in fluxo_etapas else 0
            proximo = fluxo_etapas[idx_atual + 1] if idx_atual + 1 < len(fluxo_etapas) else "Entregue"
            
            op_resp = col_acao.text_input("Operador", key=f"resp_{row['id']}")
            
            # Checklist Especial para Dobragem/Passadeira
            itens_contagem = ""
            if row['status'] in ["Passadeira", "Dobragem"]:
                itens_contagem = col_acao.text_input("Contagem (Ex: 10 Lençóis, 5 Fronhas)", key=f"itens_{row['id']}")

            if col_acao.button(f"➡️ Mover para {proximo}", key=f"btn_{row['id']}"):
                if op_resp:
                    df.at[i, 'status'] = proximo
                    df.at[i, 'resp'] = op_resp.upper()
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    if itens_contagem:
                        df.at[i, 'detalhe_itens'] = itens_contagem
                    
                    conn.update(data=df)
                    st.rerun()
                else:
                    st.error("Informe o Operador!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: HISTÓRICO ---
with tab4:
    st.subheader("Histórico Geral")
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Relatório CSV", csv, "lavanderia_v26.csv", "text/csv")
