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
    .metric-container { background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #dee2e6; }
    .alerta-tempo { color: #d9534f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: SELEÇÃO DE TURNO ---
st.sidebar.title("👤 Área do Colaborador")
turno_ativo = st.sidebar.selectbox("Selecione seu Turno:", ["Manhã (07:00 - 15:30)", "Tarde (11:30 - 20:00)"])
operador_logado = st.sidebar.text_input("Seu Nome (Operador):").upper()

if not operador_logado:
    st.sidebar.warning("⚠️ Digite seu nome para operar.")

# 2. Configurações
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50, "LAVADORA 05 (10kg)": 10
}
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0" # Certifique-se de usar a URL correta ou ID

# 3. Conexão e Limpeza de Dados (Anti-TypeError)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df_raw = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    if df_raw is None or df_raw.empty:
        cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
        df = pd.DataFrame(columns=cols)
    else:
        df = df_raw.copy()
        # Blindagem contra TypeError: Força colunas de texto a serem strings e números a serem floats
        cols_texto = ["id", "cli", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
        for col in cols_texto:
            if col in df.columns:
                df[col] = df[col].astype(str).replace(['nan', 'None', '0.0', '0', '0.1'], '')
        
        cols_num = ["p_in", "p_lavagem"]
        for col in cols_num:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                
    st.sidebar.success("✅ Conexão OK!")
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

# 4. Interface Principal
st.title("🧺 SISTEMA INDUSTRIAL LAVO E LEVO - V26")
tab1, tab2, tab3, tab4 = st.tabs(["📥 1. Recebimento", "🧼 2. Lavagem", "⚙️ 3. Produção", "📊 4. Dashboards"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Entrada de Lote")
        c1, c2, c3 = st.columns(3)
        cliente = c1.text_input("Hospital / Cliente")
        peso_bruto = c2.number_input("Peso Total (kg)", 0.1, 1000.0, step=0.1)
        obs = c3.text_input("Obs. Entrada")
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
            else: st.error("Informe o cliente e seu nome!")

# --- ABA 2: LAVAGEM FRACIONADA ---
with tab2:
    st.subheader("Carregamento de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        c1, c2 = st.columns([1.5, 1])
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        limite = float(MAQUINAS[maq_sel])
        
        lotes_lavar = c1.multiselect(
            "Selecione os Lotes:", 
            espera['id'].tolist(),
            format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)"
        )
        
        pesos_informados = {}
        peso_total_carga = 0.0
        if lotes_lavar:
            for lid in lotes_lavar:
                linha = df[df['id'] == lid]
                p_sug = float(linha['p_in'].values[0])
                p_real = st.number_input(f"Peso de {linha['cli'].values[0]} na máquina:", 0.1, p_sug + 50.0, p_sug, key=f"p_{lid}")
                pesos_informados[lid] = p_real
                peso_total_carga += p_real

        c2.markdown(f"<div class='metric-container'><h3>Carga: {peso_total_carga:.1f} / {limite}kg</h3></div>", unsafe_allow_html=True)
        
        if st.button("🚀 INICIAR LAVAGEM"):
            if lotes_lavar and operador_logado:
                if peso_total_carga <= limite + 5: # tolerância de 5kg
                    for lid, p_val in pesos_informados.items():
                        idx = df[df['id'] == str(lid)].index
                        df.loc[idx, 'status'] = "Lavagem"
                        df.loc[idx, 'maq'] = str(maq_sel)
                        df.loc[idx, 'resp'] = str(operador_logado)
                        df.loc[idx, 'p_lavagem'] = float(p_val)
                        df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
                else: st.error("Peso acima do limite da máquina!")

# --- ABA 3: PRODUÇÃO ---
# --- ABA 3: PRODUÇÃO COM REVERSÃO E QUANTIDADES ---
with tab3:
    st.subheader("⚙️ Processamento Ativo")
    
    # Filtra lotes que estão em Lavagem, Secagem, Passadeira ou Dobragem
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    
    if em_fluxo.empty:
        st.info("Nenhum lote em processamento no momento.")
    
    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2.5])
            
            # ⏱️ CÁLCULO DO CRONÔMETRO
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            estilo_t = "alerta-tempo" if minutos > 40 else ""
            
            # Coluna 1: Info do Cliente
            c1.markdown(f"**{row['cli']}** | ID: `{row['id']}`")
            c1.caption(f"Entrada: {row['h_entrada']} | Peso: {row['p_lavagem']}kg")
            if row['detalhe_itens']:
                c1.markdown(f"📝 *{row['detalhe_itens']}*")

            # Coluna 2: Status e Tempo
            c2.markdown(f"Etapa: **{row['status']}**")
            c2.markdown(f"<span class='{estilo_t}'>⏱️ {minutos} min</span>", unsafe_allow_html=True)
            
            # --- BOTÃO DE DESFAZER (REVERTER) ---
            if c2.button("↩️ Reverter", key=f"rev_{row['id']}", help="Volta para a etapa anterior"):
                status_atual = row['status']
                mapa_reversao = {
                    "Lavagem": "Aguardando Lavagem",
                    "Secagem": "Lavagem",
                    "Passadeira": "Secagem",
                    "Dobragem": "Secagem"
                }
                df.at[i, 'status'] = mapa_reversao.get(status_atual, status_atual)
                df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                conn.update(data=df); st.cache_data.clear(); st.rerun()

            # Coluna 3: Ações e Relatório de Peças
            if row['status'] == "Lavagem":
                if c3.button(f"🌀 Ir para SECAGEM", key=f"sec_{row['id']}"):
                    df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Secagem", datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            elif row['status'] == "Secagem":
                # LISTA PARA RELATAR QUANTIDADE
                with c3.expander("📊 Relatar Peças para Passadeira/Dobra"):
                    col_p1, col_p2 = st.columns(2)
                    q1 = col_p1.number_input("Lençóis", 0, 500, key=f"l_{row['id']}")
                    q2 = col_p1.number_input("Fronhas", 0, 500, key=f"f_{row['id']}")
                    q3 = col_p2.number_input("Toalhas", 0, 500, key=f"t_{row['id']}")
                    q4 = col_p2.number_input("Outros", 0, 500, key=f"o_{row['id']}")
                    
                    resumo = f"Lencol: {q1} | Fronha: {q2} | Toalha: {q3} | Outros: {q4}"
                    
                    st.divider()
                    b1, b2 = st.columns(2)
                    if b1.button("🧣 Passadeira", key=f"pas_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'] = "Passadeira", resumo
                        df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                    if b2.button("🧺 Dobragem", key=f"dob_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'] = "Dobragem", resumo
                        df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            elif row['status'] in ["Passadeira", "Dobragem"]:
                if c3.button(f"🏁 Finalizar p/ GAIOLA", key=f"fim_{row['id']}"):
                    df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Gaiola", datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    # CHECKOUT DA GAIOLA (Para lotes que já saíram do fluxo acima)
    st.divider()
    st.subheader("📦 Checkout de Gaiola")
    gaiola = df[df['status'] == "Gaiola"]
    for i, row in gaiola.iterrows():
        with st.expander(f"🚚 SAÍDA: {row['cli']} ({row['p_lavagem']}kg)"):
            st.write(f"Resumo: {row['detalhe_itens']}")
            if st.button("CONFIRMAR ENTREGA", key=f"ent_{row['id']}"):
                df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Entregue", datetime.now().isoformat()
                conn.update(data=df); st.cache_data.clear(); st.rerun()

# --- ABA 4: DASHBOARDS & ADMIN ---
with tab4:
    if not df.empty:
        # Cálculo de Tempo Médio
        def calc_tempo(row):
            try:
                hoje = datetime.now().date()
                entrada_dt = datetime.combine(hoje, datetime.strptime(row['h_entrada'], "%H:%M").time())
                fim_dt = datetime.fromisoformat(row['etapa_inicio']) if row['status'] == "Entregue" else datetime.now()
                return max(0, (fim_dt - entrada_dt).total_seconds() / 60)
            except: return 0

        df_aux = df.copy()
        df_aux['min_total'] = df_aux.apply(calc_tempo, axis=1)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Tempo Médio Fábrica", f"{df_aux['min_total'].mean():.0f} min")
        m2.metric("Total Processado", f"{df['p_in'].sum():.1f} kg")
        m3.metric("Lotes na Gaiola", len(df[df['status'] == "Gaiola"]))

        st.markdown("### 📈 Produtividade por Turno (kg)")
        prod_turno = df.groupby('turno')['p_in'].sum()
        st.bar_chart(prod_turno)
        
        st.markdown("### 📋 Histórico Geral")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Sem dados para exibir relatórios.")

    if st.sidebar.button("🗑️ Resetar Sistema"):
        if st.sidebar.checkbox("Confirmar exclusão?"):
            cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
            conn.update(data=pd.DataFrame(columns=cols)); st.cache_data.clear(); st.rerun()
