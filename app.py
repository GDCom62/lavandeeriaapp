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
    .lavadora-header { background-color: #28a745; color: white; padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Configurações
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50, "LAVADORA 05 (10kg)": 10
}
ETAPAS = ["Lavagem", "Secagem", "Passadeira/Dobragem", "Empacotamento", "Gaiola", "Entregue"]
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0HA"

# 3. Conexão Corrigida
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    # Lista de colunas que DEVEM ser texto para evitar o erro TypeError
    cols_texto = ["id", "cli", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada"]
    # Lista de colunas que DEVEM ser números
    cols_num = ["p_in", "p_lavagem"]

    if df is None or df.empty:
        df = pd.DataFrame(columns=cols_texto + cols_num)
    
    # FORÇAR TIPAGEM: Isso impede o erro de "Invalid value for dtype"
    for c in cols_texto:
        if c not in df.columns:
            df[c] = ""
        df[c] = df[c].astype(str).replace("nan", "") # Garante que tudo vira texto limpo

    for c in cols_num:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()


# 4. Interface Principal
st.title("🧺 SISTEMA INDUSTRIAL LAVO E LEVO - V26")
tab1, tab2, tab3, tab4 = st.tabs(["📥 1. Recebimento", "🧼 2. Lavagem Fracionada", "⚙️ 3. Produção", "📊 4. Administração"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Entrada de Lote (Peso Bruto)")
        c1, c2, c3 = st.columns(3)
        cliente = c1.text_input("Hospital / Cliente")
        peso_bruto = c2.number_input("Peso Total Recebido (kg)", 0.1, 1000.0, step=0.1)
        obs = c3.text_input("Observação")
        if st.form_submit_button("REGISTRAR ENTRADA"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo = pd.DataFrame([{
                    "id": novo_id, "cli": cliente.upper(), "p_in": peso_bruto, "p_lavagem": 0.0,
                    "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(), "detalhe_itens": obs
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df)
                st.toast("Lote Registrado!", icon="✅")
                time.sleep(1); st.rerun()

# --- ABA 2: LAVAGEM FRACIONADA ---
with tab2:
    st.subheader("Configurar Carga da Lavadora")
    espera = df[df['status'] == "Aguardando Lavagem"]
    
    if not espera.empty:
        c1, c2 = st.columns([1.5, 1])
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        limite = MAQUINAS[maq_sel]
        
        lotes_lavar = c1.multiselect("Selecione os Clientes para esta carga:", espera['id'].tolist(),
                                     format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} (Disponível: {df[df['id']==x]['p_in'].values[0]}kg)")
        
        # Dicionário temporário para guardar os pesos informados pelo colaborador
        pesos_informados = {}
        peso_total_carga = 0.0
        
        if lotes_lavar:
            st.markdown("---")
            st.write("⚖️ **Indique quanto de cada cliente vai na máquina agora:**")
            for lid in lotes_lavar:
                cli_nome = df[df['id'] == lid]['cli'].values[0]
                p_max = df[df['id'] == lid]['p_in'].values[0]
                # Campo de input de peso por cliente
                p_input = st.number_input(f"Quilos do {cli_nome} (Máx: {p_max}kg)", 0.0, float(p_max), float(p_max), key=f"p_{lid}")
                pesos_informados[lid] = p_input
                peso_total_carga += p_input

        # Painel de Controle de Peso
        c2.markdown(f"<div class='metric-container'><h3>Carga Total: {peso_total_carga:.1f}kg / {limite}kg</h3></div>", unsafe_allow_html=True)
        op_lav = c2.text_input("Operador da Lavagem", key="op_lav")
        
        if peso_total_carga > limite:
            c2.error(f"⚠️ EXCESSO DE PESO: {peso_total_carga - limite:.1f}kg acima do limite!")

        if st.button("🚀 INICIAR CICLO CONJUNTO"):
            if lotes_lavar and op_lav and peso_total_carga <= limite:
                for lid, p_val in pesos_informados.items():
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'] = "Secagem"
                    df.loc[idx, 'maq'] = maq_sel
                    df.loc[idx, 'resp'] = op_lav.upper()
                    df.loc[idx, 'p_lavagem'] = p_val # Salva quanto foi pra máquina
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                conn.update(data=df)
                st.success(f"Lavagem iniciada com {peso_total_carga}kg total!")
                time.sleep(1); st.rerun()
    else:
        st.info("Nenhum lote aguardando lavagem.")

# --- ABA 3: PRODUÇÃO ---
with tab3:
    st.subheader("Processamento Ativo")
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2])
            c1.markdown(f"**{row['cli']}**\n\n**Peso na Máquina:** {row['p_lavagem']}kg\nOrigem: {row['maq']}")
            
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            c2.metric("⏱️ Tempo", f"{minutos} min")
            c2.write(f"Etapa: `{row['status']}`")

            idx_f = ETAPAS.index(row['status']) if row['status'] in ETAPAS else 0
            prox = ETAPAS[idx_f + 1]
            op_f = c3.text_input("Operador", key=f"op_{row['id']}")
            det_f = c3.text_input("Peças (Ex: 20 Lençóis)", key=f"it_{row['id']}") if row['status'] == "Passadeira/Dobragem" else ""

            if c3.button(f"➡️ Confirmar {prox}", key=f"btn_{row['id']}"):
                if op_f:
                    df.at[i, 'status'], df.at[i, 'resp'], df.at[i, 'etapa_inicio'] = prox, op_f.upper(), datetime.now().isoformat()
                    if det_f: df.at[i, 'detalhe_itens'] = det_f
                    conn.update(data=df); time.sleep(1); st.rerun()
                else: st.error("Informe o operador!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: ADMIN ---
with tab4:
    st.subheader("Gaiola e Histórico")
    gaiola = df[df['status'] == "Gaiola"]
    if not gaiola.empty:
        for c in gaiola['cli'].unique():
            with st.expander(f"📦 CLIENTE: {c}", expanded=True):
                lotes_c = gaiola[gaiola['cli'] == c]
                st.write(f"Peso Total: {lotes_c['p_lavagem'].sum()}kg")
                if st.button(f"Entregar {c}", key=f"ent_{c}"):
                    df.loc[df['cli'] == c, 'status'] = "Entregue"; conn.update(data=df); time.sleep(1); st.rerun()
    
    st.divider()
    if st.button("🧹 Limpar Entregues"):
        df = df[df['status'] != "Entregue"]; conn.update(data=df); st.rerun()
