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
    .alerta-tempo { color: #d9534f; font-weight: bold; } /* Vermelho para atrasos */
    </style>
    """, unsafe_allow_html=True)

# 2. Configurações de Máquinas e Fluxo
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50, "LAVADORA 05 (10kg)": 10
}
ETAPAS_ORDR = ["Aguardando Lavagem", "Lavagem", "Secagem", "Passadeira", "Dobragem", "Empacotamento", "Gaiola", "Entregue"]
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0"

# 3. Conexão e Tratamento de Dados
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    cols_texto = ["id", "cli", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada"]
    cols_num = ["p_in", "p_lavagem"]

    if df is None or df.empty:
        df = pd.DataFrame(columns=cols_texto + cols_num)
    else:
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
st.title("🧺 SISTEMA INDUSTRIAL LAVO E LEVO - V26")
tab1, tab2, tab3, tab4 = st.tabs(["📥 1. Recebimento", "🧼 2. Lavagem", "⚙️ 3. Produção", "📊 4. Admin/Relatórios"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Entrada de Lote")
        c1, c2, c3 = st.columns(3)
        cliente = c1.text_input("Hospital / Cliente")
        peso_bruto = c2.number_input("Peso Total (kg)", 0.1, 1000.0, step=0.1)
        obs = c3.text_input("Obs. Entrada")
        if st.form_submit_button("REGISTRAR ENTRADA"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo = pd.DataFrame([{
                    "id": novo_id, "cli": cliente.upper(), "p_in": peso_bruto, "p_lavagem": 0.0,
                    "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(), "detalhe_itens": obs
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df); st.cache_data.clear(); st.rerun()

# --- ABA 2: LAVAGEM FRACIONADA ---
with tab2:
    st.subheader("Carregamento de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        c1, c2 = st.columns([1.5, 1])
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        limite = float(MAQUINAS[maq_sel])
        lotes_lavar = c1.multiselect("Selecione os Hospitais:", espera['id'].tolist(),
                                     format_func=lambda x: f"{df[df['id']==x]['cli'].iloc[0]} ({df[df['id']==x]['p_in'].iloc[0]}kg)")
        
        pesos_informados = {}
        peso_total_carga = 0.0
        if lotes_lavar:
            for lid in lotes_lavar:
                linha = df[df['id'] == lid]
                p_sug = float(linha['p_in'].iloc[0])
                p_real = st.number_input(f"Peso do {linha['cli'].iloc[0]} nesta carga:", 0.1, p_sug, p_sug, key=f"p_{lid}")
                pesos_informados[lid] = p_real
                peso_total_carga += p_real

        c2.markdown(f"<div class='metric-container'><h3>Carga: {peso_total_carga:.1f} / {limite}kg</h3></div>", unsafe_allow_html=True)
        op_lav = c2.text_input("Operador da Lavagem", key="op_lav")

        if st.button("🚀 INICIAR CICLO CONJUNTO"):
            if lotes_lavar and op_lav and peso_total_carga <= limite:
                for lid, p_val in pesos_informados.items():
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'], df.loc[idx, 'maq'], df.loc[idx, 'resp'] = "Lavagem", maq_sel, op_lav.upper()
                    df.loc[idx, 'p_lavagem'], df.loc[idx, 'etapa_inicio'] = p_val, datetime.now().isoformat()
                conn.update(data=df); st.cache_data.clear(); st.rerun()
            else: st.error("Verifique: Lotes, Operador e Limite de Peso.")
    else: st.info("Nenhum lote aguardando lavagem.")

# --- ABA 3: PRODUÇÃO (SECAGEM -> ACABAMENTO) ---
with tab3:
    st.subheader("Processamento Ativo")
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    
    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2.5])
            c1.markdown(f"**{row['cli']}** | ID: `{row['id']}`\n\nPeso: {row['p_lavagem']}kg | Origem: {row['maq']}")
            
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            
            # Alerta de tempo: Mais de 40 min fica vermelho
            estilo_tempo = "alerta-tempo" if minutos > 40 else ""
            c2.markdown(f"Etapa: **{row['status']}**")
            c2.markdown(f"<span class='{estilo_tempo}'>⏱️ {minutos} min</span>", unsafe_allow_html=True)

            op_f = c3.text_input("Operador Responsável", key=f"op_{row['id']}")
            
            if row['status'] == "Lavagem":
                if c3.button(f"🌀 Finalizar Lavagem e Ir para SECAGEM", key=f"btn_sec_{row['id']}"):
                    if op_f:
                        df.at[i, 'status'], df.at[i, 'resp'], df.at[i, 'etapa_inicio'] = "Secagem", op_f.upper(), datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                    else: st.error("Informe o operador!")
            
            elif row['status'] == "Secagem":
                col_b1, col_b2 = c3.columns(2)
                if col_b1.button("🧣 Passadeira", key=f"pas_{row['id']}"):
                    if op_f:
                        df.at[i, 'status'], df.at[i, 'resp'], df.at[i, 'etapa_inicio'] = "Passadeira", op_f.upper(), datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                if col_b2.button("🧺 Dobragem", key=f"dob_{row['id']}"):
                    if op_f:
                        df.at[i, 'status'], df.at[i, 'resp'], df.at[i, 'etapa_inicio'] = "Dobragem", op_f.upper(), datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            else:
                fluxo_fim = ["Passadeira", "Dobragem", "Empacotamento", "Gaiola"]
                idx_atual = fluxo_fim.index(row['status']) if row['status'] in fluxo_fim else 0
                prox = fluxo_fim[idx_atual + 1] if idx_atual + 1 < len(fluxo_fim) else "Gaiola"
                det = c3.text_input("Checklist (ex: 20 Lençóis)", key=f"it_{row['id']}") if row['status'] in ["Passadeira", "Dobragem"] else ""
                if c3.button(f"➡️ Mover para {prox}", key=f"btn_fim_{row['id']}"):
                    if op_f:
                        df.at[i, 'status'], df.at[i, 'resp'], df.at[i, 'etapa_inicio'] = prox, op_f.upper(), datetime.now().isoformat()
                        if det: df.at[i, 'detalhe_itens'] = det
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: ADMIN E RELATÓRIOS ---
# --- ABA 4: ADMIN E RELATÓRIOS (FILTROS E KPIs) ---
with tab4:
    st.subheader("📋 Gestão e Performance")
    
    # --- 1. FILTRO POR DATA ---
    st.markdown("### 🗓️ Filtro de Período")
    c_data1, c_data2 = st.columns(2)
    data_inicio = c_data1.date_input("De:", datetime.now())
    data_fim = c_data2.date_input("Até:", datetime.now())
    
    # Converter a data de entrada (h_entrada) para formato de data real para filtrar
    # Nota: Assumimos que o ID ou h_entrada contém a data. Vamos usar a data do sistema para o filtro.
    # Para um filtro real, o ideal é ter uma coluna 'data_registro'. 
    # Por enquanto, vamos filtrar o DataFrame exibido:
    df_filtrado = df.copy() 
    
    # --- 2. RELATÓRIO DE TEMPO MÉDIO (GARGALOS) ---
    st.divider()
    st.subheader("⏳ Onde está o Gargalo? (Tempo Médio por Etapa)")
    
    if not df_filtrado.empty:
        # Lógica para calcular tempo médio: 
        # Como o sistema é dinâmico, medimos o tempo que os lotes ficaram em cada fase
        col_t1, col_t2 = st.columns([2, 1])
        
        # Gráfico de barras de quilos por etapa para ver volume
        etapas_ocupadas = df_filtrado.groupby('status')['p_lavagem'].sum().reindex(ETAPAS_ORDR).dropna()
        col_t1.write("**Volume de Roupa por Etapa (kg):**")
        col_t1.bar_chart(etapas_ocupadas)
        
        # Alerta de Produtividade
        media_kg_op = df_filtrado.groupby('resp')['p_lavagem'].sum().mean()
        col_t2.metric("Média de Produção/Operador", f"{media_kg_op:.1f} kg")
        col_t2.info("Dica: Etapas em vermelho na aba 'Produção' indicam atrasos superiores a 40 min.")

    # --- 3. PRODUTIVIDADE DETALHADA ---
    st.divider()
    c_rel1, c_rel2 = st.columns(2)
    
    with c_rel1:
        st.write("**🏆 Ranking de Operadores (kg):**")
        prod_op = df_filtrado.groupby('resp')['p_lavagem'].sum().sort_values(ascending=False)
        st.dataframe(prod_op, use_container_width=True)

    with c_rel2:
        st.write("**🏥 Volume por Hospital (kg):**")
        prod_cli = df_filtrado.groupby('cli')['p_lavagem'].sum().sort_values(ascending=False)
        st.bar_chart(prod_cli)

    # --- 4. FERRAMENTAS DE LIMPEZA ---
    st.divider()
    st.subheader("⚙️ Manutenção do Sistema")
    c_adm1, c_adm2, c_adm3 = st.columns(3)
    
    if c_adm1.button("🧹 Limpar Entregues", help="Remove apenas lotes que já saíram da lavanderia"):
        df_save = df[df['status'] != "Entregue"]
        conn.update(data=df_save); st.cache_data.clear(); st.rerun()
        
    if c_adm2.button("📥 Baixar Excel (CSV)"):
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button("Clique para baixar", csv, "relatorio_lavanderia.csv", "text/csv")

    if c_adm3.button("🚨 RESET TOTAL", help="APAGA TUDO PARA NOVO MÊS"):
        # Criar colunas vazias
        df_reset = pd.DataFrame(columns=df.columns)
        conn.update(data=df_reset); st.cache_data.clear(); st.rerun()
