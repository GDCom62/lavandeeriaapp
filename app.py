import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página e Estética Industrial
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .status-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f8f9fa; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .metric-container { background-color: #e9ecef; padding: 10px; border-radius: 5px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# 2. Configurações do Parque de Máquinas
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120,
    "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60,
    "LAVADORA 04 (50kg)": 50,
    "LAVADORA 05 (10kg)": 10
}
ETAPAS = ["Lavagem", "Secagem", "Passadeira/Dobragem", "Empacotamento", "Gaiola", "Entregue"]

# 3. Conexão com Google Sheets
URL_PLANILHA = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    # Garantir colunas essenciais
    cols = ["id", "cli", "p_in", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada"]
    if df is None or df.empty:
        df = pd.DataFrame(columns=cols)
    else:
        for c in cols:
            if c not in df.columns: df[c] = ""
            
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# 4. Interface Principal
st.title("🧺 GESTÃO INDUSTRIAL LAVO E LEVO - V26")
tab1, tab2, tab3, tab4 = st.tabs(["📥 Recebimento", "🧼 Sala de Lavagem", "⚙️ Linha de Produção", "📊 Gaiola & KPIs"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("entrada", clear_on_submit=True):
        st.subheader("Entrada de Lote")
        c1, c2, c3 = st.columns([2,1,2])
        cliente = c1.text_input("Hospital / Cliente")
        peso = c2.number_input("Peso (kg)", 0.1)
        obs = c3.text_input("Observação de Entrada")
        if st.form_submit_button("REGISTRAR ENTRADA"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo = pd.DataFrame([{
                    "id": novo_id, "cli": cliente.upper(), "p_in": peso,
                    "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(), "detalhe_itens": obs
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df)
                st.rerun()

# --- ABA 2: SALA DE LAVAGEM (CARGA MISTA) ---
with tab2:
    st.subheader("Carregamento de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        c1, c2 = st.columns(2)
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        lotes_ids = c1.multiselect("Selecione os lotes para esta máquina:", espera['id'].tolist(),
                                   format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)")
        
        peso_total = df[df['id'].isin(lotes_ids)]['p_in'].sum()
        limite = MAQUINAS[maq_sel]
        
        c2.markdown(f"<div class='metric-container'><h3>Peso da Carga: {peso_total}kg / {limite}kg</h3></div>", unsafe_allow_html=True)
        op_lav = c2.text_input("Operador da Lavagem", key="op_lav")

        if st.button("🚀 INICIAR LAVAGEM") and lotes_ids and op_lav:
            if peso_total <= limite:
                for lid in lotes_ids:
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'] = "Secagem" # Próxima etapa
                    df.loc[idx, 'maq'] = maq_sel
                    df.loc[idx, 'resp'] = op_lav.upper()
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                conn.update(data=df)
                st.success(f"Máquina {maq_sel} iniciada!")
                st.rerun()
            else: st.error("Peso excede a capacidade da máquina!")
    else: st.info("Nenhum lote aguardando lavagem.")

# --- ABA 3: LINHA DE PRODUÇÃO (SALA 2 E 3) ---
with tab3:
    st.subheader("Processamento e Separação")
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    
    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2])
            
            c1.markdown(f"**{row['cli']}** | ID: `{row['id']}`\n\nPeso: {row['p_in']}kg | Origem: {row['maq']}")
            
            # Cronômetro
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            c2.metric("⏱️ Tempo", f"{minutos} min")
            c2.write(f"Etapa: `{row['status']}`")

            # Ação
            idx = ETAPAS.index(row['status']) if row['status'] in ETAPAS else 0
            prox = ETAPAS[idx + 1]
            op_atual = c3.text_input("Operador Responsável", key=f"op_{row['id']}")
            
            checklist = ""
            if row['status'] == "Passadeira/Dobragem":
                checklist = c3.text_input("Checklist (ex: 20 Lençóis, 5 Fronhas)", key=f"it_{row['id']}")

            if c3.button(f"➡️ Confirmar {prox}", key=f"btn_{row['id']}"):
                if op_atual:
                    df.at[i, 'status'] = prox
                    df.at[i, 'resp'] = op_atual.upper()
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    if checklist: df.at[i, 'detalhe_itens'] = checklist
                    conn.update(data=df)
                    st.rerun()
                else: st.error("Informe o operador!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: GAIOLA E KPIs ---
with tab4:
    st.subheader("Expedição Final (Gaiola)")
    na_gaiola = df[df['status'] == "Gaiola"]
    if not na_gaiola.empty:
        clientes = na_gaiola['cli'].unique()
        for c in clientes:
            with st.expander(f"📦 CLIENTE: {c} - (Pronto para Entrega)", expanded=True):
                lotes_c = na_gaiola[na_gaiola['cli'] == c]
                st.write(f"Total de Lotes: {len(lotes_c)} | Peso Total: {lotes_c['p_in'].sum()}kg")
                if st.button(f"DAR BAIXA: Entrega Realizada {c}", key=f"ent_{c}"):
                    df.loc[df['cli'] == c, 'status'] = "Entregue"
                    conn.update(data=df)
                    st.rerun()
    
    st.divider()
    st.subheader("Produtividade (kg processados por operador)")
    if not df.empty:
        prod = df.groupby('resp')['p_in'].sum().sort_values(ascending=False)
        st.bar_chart(prod)
        st.write("**Histórico Geral:**")
        st.dataframe(df, use_container_width=True)
