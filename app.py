import streamlit as st
import pandas as pd
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página e Estilo
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
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0"

# 3. Conexão com Tratamento de Tipagem (Evita erro de Coluna Numérica vs Texto)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    cols_texto = ["id", "cli", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada"]
    cols_num = ["p_in", "p_lavagem"]

    if df is None or df.empty:
        df = pd.DataFrame(columns=cols_texto + cols_num)
    else:
        # Garante que colunas de texto sejam lidas como String e colunas de peso como Número
        for c in cols_texto:
            if c not in df.columns: df[c] = ""
            df[c] = df[c].astype(str).replace("nan", "")
        for c in cols_num:
            if c not in df.columns: df[c] = 0.0
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)

except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# 4. Interface Principal
st.title("🧺 GESTÃO INDUSTRIAL LAVO E LEVO - V26")
tab1, tab2, tab3, tab4 = st.tabs(["📥 1. Recebimento", "🧼 2. Lavagem Fracionada", "⚙️ 3. Produção", "📊 4. Admin/KPIs"])

# --- ABA 1: RECEBIMENTO (SALA 1) ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Entrada de Lote")
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
                st.cache_data.clear() # Limpa cache para ler o novo lote
                st.toast("Lote Registrado!", icon="✅")
                time.sleep(1); st.rerun()

# --- ABA 2: LAVAGEM FRACIONADA (SALA 1) ---
with tab2:
    st.subheader("Carregamento de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    
    if not espera.empty:
        c1, c2 = st.columns([1.5, 1])
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        limite = MAQUINAS[maq_sel]
        
        lotes_lavar = c1.multiselect("Selecione os Clientes:", espera['id'].tolist(),
                                     format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)")
        
        pesos_informados = {}
        peso_total_carga = 0.0
        
        if lotes_lavar:
            st.markdown("---")
            for lid in lotes_lavar:
                cli_nome = df[df['id'] == lid]['cli'].values[0]
                p_max = float(df[df['id'] == lid]['p_in'].values[0])
                p_input = st.number_input(f"Peso do {cli_nome} na máquina (kg):", 0.1, p_max, p_max, key=f"p_{lid}")
                pesos_informados[lid] = p_input
                peso_total_carga += p_input

        c2.markdown(f"<div class='metric-container'><h3>Carga: {peso_total_carga:.1f} / {limite}kg</h3></div>", unsafe_allow_html=True)
        op_lav = c2.text_input("Operador da Lavagem", key="op_lav")

        if st.button("🚀 INICIAR CICLO CONJUNTO"):
            if lotes_lavar and op_lav and peso_total_carga <= limite:
                for lid, p_val in pesos_informados.items():
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'] = "Secagem"
                    df.loc[idx, 'maq'] = maq_sel
                    df.loc[idx, 'resp'] = op_lav.upper()
                    df.loc[idx, 'p_lavagem'] = p_val
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                
                conn.update(data=df)
                st.cache_data.clear() # CRÍTICO: Força o sistema a ver a mudança
                st.success("Lavagem Iniciada!")
                time.sleep(1); st.rerun()
            else:
                st.error("Verifique: Lotes, Operador e Limite de Peso.")
    else:
        st.info("Nenhum lote aguardando lavagem.")

# --- ABA 3: PRODUÇÃO (SALAS 2 E 3) ---
with tab3:
    st.subheader("Processamento Ativo")
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2])
            c1.markdown(f"**{row['cli']}**\n\n**Peso Lavado:** {row['p_lavagem']}kg\nOrigem: {row['maq']}")
            
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            c2.metric("⏱️ Tempo", f"{minutos} min")
            c2.write(f"Etapa: `{row['status']}`")

            idx_f = ETAPAS.index(row['status']) if row['status'] in ETAPAS else 1
            prox = ETAPAS[idx_f + 1]
            op_f = c3.text_input("Operador Responsável", key=f"op_{row['id']}")
            det_f = c3.text_input("Lista de Peças", key=f"it_{row['id']}") if row['status'] == "Passadeira/Dobragem" else ""

            if c3.button(f"➡️ Mover para {prox}", key=f"btn_{row['id']}"):
                if op_f:
                    df.at[i, 'status'], df.at[i, 'resp'], df.at[i, 'etapa_inicio'] = prox, op_f.upper(), datetime.now().isoformat()
                    if det_f: df.at[i, 'detalhe_itens'] = det_f
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("Informe o operador!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: ADMIN E KPIs ---
with tab4:
    st.subheader("Expedição na Gaiola")
    na_gaiola = df[df['status'] == "Gaiola"]
    if not na_gaiola.empty:
        for c in na_gaiola['cli'].unique():
            with st.expander(f"📦 CLIENTE: {c}", expanded=True):
                lotes_c = na_gaiola[na_gaiola['cli'] == c]
                st.write(f"Peso Total: {lotes_c['p_lavagem'].sum()}kg")
                if st.button(f"Dar Baixa: Entrega {c}", key=f"ent_{c}"):
                    df.loc[df['cli'] == c, 'status'] = "Entregue"
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
    
    st.divider()
    st.subheader("Administração")
    c_ad1, c_ad2 = st.columns(2)
    if c_ad1.button("🧹 Limpar Histórico de Entregues"):
        df_limpo = df[df['status'] != "Entregue"]
        conn.update(data=df_limpo); st.cache_data.clear(); st.rerun()
    if c_ad2.button("🚨 RESET TOTAL (NOVO MÊS)"):
        df_reset = pd.DataFrame(columns=cols_texto + cols_num)
        conn.update(data=df_reset); st.cache_data.clear(); st.rerun()
    
    if not df.empty:
        st.write("**Produtividade (kg por Operador):**")
        st.bar_chart(df.groupby('resp')['p_lavagem'].sum())
