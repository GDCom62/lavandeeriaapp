import streamlit as st
import pandas as pd
from datetime import datetime
import time
from streamlit_gsheets import GSheetsConnection

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .status-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #ffffff; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .metric-container { background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #dee2e6; }
    .alerta-tempo { color: #d9534f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR ---
st.sidebar.title("👤 Área do Colaborador")
turno_ativo = st.sidebar.selectbox("Selecione seu Turno:", ["Manhã (07:00 - 15:30)", "Tarde (11:30 - 20:00)"])
operador_logado = st.sidebar.text_input("Seu Nome (Operador):").upper()

if not operador_logado:
    st.sidebar.warning("⚠️ Digite seu nome para operar.")

# 2. CONFIGURAÇÕES E URL (Ajustada para exportação direta)
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50, "LAVADORA 05 (10kg)": 10
}
# FORMATO DE URL PARA EVITAR ERRO DE CONEXÃO
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0"

# 3. CONEXÃO E LIMPEZA DE DADOS
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    if df_raw is None or df_raw.empty:
        cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
        df = pd.DataFrame(columns=cols)
    else:
        df = df_raw.copy()
        # Forçar tipos de dados para evitar TypeError
        for c in ["id", "cli", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]:
            df[c] = df[c].astype(str).replace(['nan', 'None'], '')
        for n in ["p_in", "p_lavagem"]:
            df[n] = pd.to_numeric(df[n], errors='coerce').fillna(0.0)
except Exception as e:
    st.error(f"Erro de Conexão: {e}")
    st.stop()

# 4. INTERFACE PRINCIPAL
st.title("🧺 SISTEMA INDUSTRIAL LAVO E LEVO - V26")
tab1, tab2, tab3, tab4 = st.tabs(["📥 1. Recebimento", "🧼 2. Lavagem", "⚙️ 3. Produção", "📊 4. Admin/Relatórios"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Entrada de Lote (Peso Sujo)")
        c1, c2, c3 = st.columns(3)
        cliente = c1.text_input("Hospital / Cliente")
        peso_bruto = c2.number_input("Peso Total Sujo (kg)", 0.1, 2000.0, step=0.1)
        obs = c3.text_input("Obs. Geral")
        if st.form_submit_button("REGISTRAR ENTRADA"):
            if cliente and operador_logado:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo = pd.DataFrame([{
                    "id": str(novo_id), "cli": cliente.upper(), "p_in": float(peso_bruto), "p_lavagem": 0.0,
                    "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(), "detalhe_itens": obs,
                    "resp": operador_logado, "turno": turno_ativo, "maq": ""
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df); st.cache_data.clear(); st.rerun()
            else: st.error("Preencha o cliente e seu nome!")

# --- ABA 2: LAVAGEM ---
with tab2:
    st.subheader("Carregamento de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        c1, c2 = st.columns([1.5, 1])
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        lotes_lavar = c1.multiselect("Selecione os Hospitais:", espera['id'].tolist(),
                                    format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)")
        
        peso_total_carga = 0.0
        if lotes_lavar:
            for lid in lotes_lavar:
                peso_lote = float(df[df['id'] == lid]['p_in'].values[0])
                peso_total_carga += peso_lote
            
            c2.markdown(f"<div class='metric-container'><h3>Carga: {peso_total_carga:.1f} / {MAQUINAS[maq_sel]}kg</h3></div>", unsafe_allow_html=True)
            if st.button("🚀 INICIAR LAVAGEM"):
                if peso_total_carga <= MAQUINAS[maq_sel] + 10:
                    for lid in lotes_lavar:
                        idx = df[df['id'] == lid].index
                        df.loc[idx, 'status'], df.loc[idx, 'maq'], df.loc[idx, 'etapa_inicio'] = "Lavagem", maq_sel, datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
                else: st.error("Peso acima do limite!")

# --- ABA 3: PRODUÇÃO, CONFERÊNCIA E GAIOLA ---
with tab3:
    st.subheader("⚙️ Fluxo Ativo e Conferência")
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    
    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2.5])
            
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            
            c1.markdown(f"**{row['cli']}** | ID: `{row['id']}`")
            c1.caption(f"Peso Entrada: {row['p_in']}kg | Status: {row['status']}")
            
            c2.markdown(f"⏱️ **{minutos} min**")
            if c2.button("↩️ Reverter", key=f"rev_{row['id']}"):
                mapa = {"Lavagem":"Aguardando Lavagem", "Secagem":"Lavagem", "Passadeira":"Secagem", "Dobragem":"Secagem"}
                df.at[i, 'status'] = mapa.get(row['status'], row['status'])
                conn.update(data=df); st.cache_data.clear(); st.rerun()

            if row['status'] == "Lavagem":
                if c3.button("🌀 Enviar p/ SECAGEM", key=f"s_{row['id']}"):
                    df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Secagem", datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            elif row['status'] == "Secagem":
                with c3.expander("📝 Relatar Itens p/ Passadeira ou Dobra"):
                    col_a, col_b = st.columns(2)
                    q1 = col_a.number_input("Lençol", 0, 999, key=f"l_{row['id']}")
                    q2 = col_a.number_input("Fronha", 0, 999, key=f"f_{row['id']}")
                    q3 = col_b.number_input("Toalha", 0, 999, key=f"t_{row['id']}")
                    q4 = col_b.number_input("Campo", 0, 999, key=f"c_{row['id']}")
                    out = st.number_input("Outros", 0, 999, key=f"o_{row['id']}")
                    resumo = f"L:{q1}, F:{q2}, T:{q3}, C:{q4}, O:{out}"
                    
                    b1, b2 = st.columns(2)
                    if b1.button("🧣 Passadeira", key=f"p_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'], df.at[i, 'etapa_inicio'] = "Passadeira", resumo, datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                    if b2.button("🧺 Dobragem", key=f"d_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'], df.at[i, 'etapa_inicio'] = "Dobragem", resumo, datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()

            elif row['status'] in ["Passadeira", "Dobragem"]:
                with c3.expander("⚖️ PESAGEM FINAL E GAIOLA"):
                    peso_saida = st.number_input("Peso Limpo (kg)", 0.1, 1000.0, float(row['p_in']), key=f"ps_{row['id']}")
                    gaiola_n = st.text_input("Número da Gaiola:", key=f"gn_{row['id']}")
                    if st.button("🏁 Finalizar p/ GAIOLA", key=f"f_{row['id']}"):
                        if gaiola_n:
                            df.at[i, 'p_lavagem'], df.at[i, 'maq'], df.at[i, 'status'], df.at[i, 'etapa_inicio'] = peso_saida, f"GAIOLA {gaiola_n}", "Gaiola", datetime.now().isoformat()
                            conn.update(data=df); st.cache_data.clear(); st.rerun()
                        else: st.warning("Informe a Gaiola!")
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📦 Expedição (Saída Motorista)")
    gaiolas = df[df['status'] == "Gaiola"]
    for i, r in gaiolas.iterrows():
        with st.expander(f"🚚 {r['maq']} - {r['cli']} ({r['p_lavagem']}kg)"):
            st.write(f"Itens: {r['detalhe_itens']}")
            if st.button("CONFIRMAR SAÍDA", key=f"out_{r['id']}"):
                df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Entregue", datetime.now().isoformat()
                conn.update(data=df); st.cache_data.clear(); st.rerun()

# --- ABA 4: ADMIN / RELATÓRIOS ---
with tab4:
    st.subheader("📊 Comparativo Entrada vs Saída")
    if not df.empty:
        df_fin = df[df['status'].isin(["Gaiola", "Entregue"])].copy()
        if not df_fin.empty:
            df_fin['Variação'] = df_fin['p_lavagem'] - df_fin['p_in']
            st.dataframe(df_fin[['cli', 'p_in', 'p_lavagem', 'Variação', 'maq', 'detalhe_itens']], use_container_width=True)
            st.metric("Total kg Limpo (Hoje)", f"{df_fin['p_lavagem'].sum():.1f} kg")
    
    if st.sidebar.button("🗑️ Limpar Planilha"):
        if st.sidebar.checkbox("Confirmar?"):
            df_vazio = pd.DataFrame(columns=df.columns)
            conn.update(data=df_vazio); st.cache_data.clear(); st.rerun()

# AUTO-REFRESH DO CRONÔMETRO
time.sleep(60)
st.rerun()
