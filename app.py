import streamlit as st
import pandas as pd
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .status-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #ffffff; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .metric-container { background-color: #f1f3f5; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #dee2e6; }
    </style>
    """, unsafe_allow_html=True)

# 2. Configurações de Máquinas e Fluxo
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50, "LAVADORA 05 (10kg)": 10
}
ETAPAS = ["Lavagem", "Secagem", "Passadeira/Dobragem", "Empacotamento", "Gaiola", "Entregue"]

# 3. Conexão com Google Sheets
# IMPORTANTE: Garanta que o link da planilha esteja correto aqui ou nas Secrets
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
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
st.title("🧺 SISTEMA INDUSTRIAL LAVO E LEVO - V26")
tab1, tab2, tab3, tab4 = st.tabs(["📥 Sala 1: Recebimento", "🧼 Sala 1: Lavagem", "⚙️ Sala 2/3: Produção", "📊 Gaiola & Admin"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Entrada de Lote")
        c1, c2, c3 = st.columns(3)
        cliente = c1.text_input("Hospital / Cliente")
        peso = c2.number_input("Peso (kg)", 0.1, 500.0, step=0.1)
        obs = c3.text_input("Obs. Entrada (ex: Rasgos)")
        if st.form_submit_button("REGISTRAR LOTE"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo = pd.DataFrame([{
                    "id": novo_id, "cli": cliente.upper(), "p_in": peso,
                    "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(), "detalhe_itens": obs
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df)
                st.toast("Lote Registrado!", icon="✅")
                time.sleep(1)
                st.rerun()

# --- ABA 2: SALA DE LAVAGEM (CARGA MISTA) ---
with tab2:
    st.subheader("Carregamento das Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        c1, c2 = st.columns([1.5, 1])
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        lotes_lavar = c1.multiselect("Selecione os Hospitais para esta carga:", espera['id'].tolist(),
                                     format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)")
        
        peso_total = df[df['id'].isin(lotes_lavar)]['p_in'].sum()
        limite = MAQUINAS[maq_sel]
        
        c2.markdown(f"<div class='metric-container'><h3>Carga Atual: {peso_total}kg / {limite}kg</h3></div>", unsafe_allow_html=True)
        op_lav = c2.text_input("Operador Responsável", key="op_lav")

        if st.button("🚀 INICIAR CICLO CONJUNTO") and lotes_lavar and op_lav:
            if peso_total <= limite:
                for lid in lotes_lavar:
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'], df.loc[idx, 'maq'], df.loc[idx, 'resp'] = "Secagem", maq_sel, op_lav.upper()
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                conn.update(data=df)
                st.success(f"Lavagem iniciada na {maq_sel}!")
                time.sleep(1)
                st.rerun()
            else: st.error("Peso acima da capacidade!")
    else: st.info("Nenhum lote aguardando lavagem.")

# --- ABA 3: LINHA DE PRODUÇÃO (SALAS 2 E 3) ---
with tab3:
    st.subheader("Processamento Ativo")
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2])
            c1.markdown(f"**{row['cli']}** | ID: `{row['id']}`\n\nPeso: {row['p_in']}kg | Origem: {row['maq']}")
            
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            c2.metric("⏱️ Tempo", f"{minutos} min")
            c2.write(f"Etapa: `{row['status']}`")

            idx_f = ETAPAS.index(row['status']) if row['status'] in ETAPAS else 0
            prox = ETAPAS[idx_f + 1]
            op_f = c3.text_input("Operador", key=f"op_{row['id']}")
            det_f = c3.text_input("Checklist de Peças", key=f"it_{row['id']}") if row['status'] == "Passadeira/Dobragem" else ""

            if c3.button(f"➡️ Confirmar {prox}", key=f"btn_{row['id']}"):
                if op_f:
                    df.at[i, 'status'], df.at[i, 'resp'], df.at[i, 'etapa_inicio'] = prox, op_f.upper(), datetime.now().isoformat()
                    if det_f: df.at[i, 'detalhe_itens'] = det_f
                    conn.update(data=df); time.sleep(1); st.rerun()
                else: st.error("Informe o operador!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: GAIOLA E ADMIN ---
with tab4:
    st.subheader("Expedição na Gaiola (Saída)")
    gaiola = df[df['status'] == "Gaiola"]
    if not gaiola.empty:
        for c in gaiola['cli'].unique():
            with st.expander(f"📦 CLIENTE: {c}", expanded=True):
                lotes_c = gaiola[gaiola['cli'] == c]
                st.write(f"Peso Total: {lotes_c['p_in'].sum()}kg | Lotes: {len(lotes_c)}")
                if st.button(f"Entregar para Motorista: {c}", key=f"ent_{c}"):
                    df.loc[df['cli'] == c, 'status'] = "Entregue"
                    conn.update(data=df); time.sleep(1); st.rerun()

    st.divider()
    st.subheader("⚙️ Administração de Dados")
    c_ad1, c_ad2 = st.columns(2)
    if c_ad1.button("🧹 Limpar Lotes Entregues"):
        df = df[df['status'] != "Entregue"]
        conn.update(data=df); st.success("Histórico limpo!"); time.sleep(1); st.rerun()
    if c_ad2.button("🚨 RESET TOTAL (NOVO MÊS)"):
        df_new = pd.DataFrame(columns=cols)
        conn.update(data=df_new); st.warning("Tudo apagado!"); time.sleep(1); st.rerun()
    
    st.write("**Produtividade por Operador (kg):**")
    if not df.empty and 'resp' in df.columns:
        st.bar_chart(df.groupby('resp')['p_in'].sum())
