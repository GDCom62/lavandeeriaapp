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
ETAPAS_ORDR = ["Aguardando Lavagem", "Lavagem", "Secagem", "Passadeira", "Dobragem", "Empacotamento", "Gaiola", "Entregue"]
URL_PLANILHA = "https://google.com"

# 3. Conexão e Dados
## 3. CONEXÃO REVISADA E BLINDADA
try:
    # Tenta conectar usando as credenciais das Secrets
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Tenta ler a planilha. Se falhar aqui, o problema é permissão ou link.
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    # Se o Google retornar algo que não seja uma tabela, criamos uma vazia
    if df is None or not isinstance(df, pd.DataFrame):
        st.error("⚠️ Atenção: A planilha foi encontrada, mas não contém dados válidos.")
        cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
        df = pd.DataFrame(columns=cols)
    else:
        # Garante que todas as colunas existam para não travar o restante do app
        todas_cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
        for c in todas_cols:
            if c not in df.columns:
                df[c] = 0.0 if "p_" in c else ""
        
    st.sidebar.success("✅ Conexão com Google Sheets OK!")

except Exception as e:
    st.error(f"❌ FALHA NA CONEXÃO: {e}")
    st.info("💡 DICA: Verifique se o e-mail da Conta de Serviço é EDITOR na sua planilha do Google.")
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
            if cliente and operador_logado:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo = pd.DataFrame([{
                    "id": novo_id, "cli": cliente.upper(), "p_in": peso_bruto, "p_lavagem": 0.0,
                    "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(), "detalhe_itens": obs,
                    "resp": operador_logado, "turno": turno_ativo
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df); st.cache_data.clear(); st.rerun()
            else: st.error("Informe seu nome na barra lateral e o cliente!")

# --- ABA 2: LAVAGEM FRACIONADA ---
# --- ABA 2: LAVAGEM FRACIONADA ---
with tab2:
    st.subheader("Carregamento de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        c1, c2 = st.columns([1.5, 1])
        maq_sel = c1.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        limite = float(MAQUINAS[maq_sel])
        
        # Correção aqui: Usamos uma função simples para formatar o nome no seletor
        lotes_lavar = c1.multiselect(
            "Selecione os Hospitais:", 
            espera['id'].tolist(),
            format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)"
        )
        
        pesos_informados = {}
        peso_total_carga = 0.0
        if lotes_lavar:
            for lid in lotes_lavar:
                linha = df[df['id'] == lid]
                p_sug = float(linha['p_in'].values[0])
                p_real = st.number_input(f"Peso de {linha['cli'].values[0]} na máquina:", 0.1, p_sug, p_sug, key=f"p_{lid}")
                pesos_informados[lid] = p_real
                peso_total_carga += p_real

        c2.markdown(f"<div class='metric-container'><h3>Carga: {peso_total_carga:.1f} / {limite}kg</h3></div>", unsafe_allow_html=True)
        
        if st.button("🚀 INICIAR LAVAGEM"):
            if lotes_lavar and operador_logado:
                if peso_total_carga <= limite:
                    for lid, p_val in pesos_informados.items():
                        idx = df[df['id'] == lid].index
                        df.loc[idx, 'status'] = "Lavagem"
                        df.loc[idx, 'maq'] = maq_sel
                        df.loc[idx, 'resp'] = operador_logado
                        df.loc[idx, 'p_lavagem'] = p_val
                        df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                        df.loc[idx, 'turno'] = turno_ativo
                    conn.update(data=df)
                    st.cache_data.clear()
                    st.rerun()
                else: st.error("Peso acima do limite!")
            else: st.error("Selecione os lotes e verifique seu nome na barra lateral!")


# --- ABA 3: PRODUÇÃO ---
            # --- CONTINUAÇÃO DA ABA 3 (PRODUÇÃO) ---
            elif row['status'] == "Secagem":
                col_b1, col_b2 = c3.columns(2)
                if col_b1.button("🧣 Ir p/ Passadeira", key=f"pas_{row['id']}"):
                    df.at[i, 'status'] = "Passadeira"
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    df.at[i, 'resp'] = operador_logado
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
                
                if col_b2.button("🧺 Ir p/ Dobragem", key=f"dob_{row['id']}"):
                    df.at[i, 'status'] = "Dobragem"
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    df.at[i, 'resp'] = operador_logado
                    conn.update(data=df); st.cache_data.clear(); st.rerun()

            elif row['status'] in ["Passadeira", "Dobragem"]:
                if c3.button(f"🏁 Finalizar e enviar para GAIOLA", key=f"fim_{row['id']}"):
                    df.at[i, 'status'] = "Gaiola"
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    df.at[i, 'resp'] = operador_logado
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: ADMIN / RELATÓRIOS ---
with tab4:
    st.subheader("📊 Painel de Controle e Histórico")
    
    # Métricas Rápidas
    m1, m2, m3 = st.columns(3)
    total_kg = df['p_in'].sum()
    em_processo = df[~df['status'].isin(["Gaiola", "Entregue"])].shape[0]
    finalizados = df[df['status'] == "Gaiola"].shape[0]
    
    m1.metric("Total Recebido (kg)", f"{total_kg:.1f} kg")
    m2.metric("Lotes em Processo", em_processo)
    m3.metric("Prontos na Gaiola", finalizados)

    st.divider()
    
    # Filtro de Busca
    busca = st.text_input("🔍 Buscar Cliente ou ID:")
    df_busca = df[df['cli'].str.contains(busca.upper()) | df['id'].str.contains(busca)] if busca else df
    
    st.dataframe(df_busca, use_container_width=True)

    # Botão de Reset (Cuidado!)
    if st.sidebar.button("🗑️ Limpar Planilha (Backup Recom.)"):
        if st.sidebar.checkbox("Confirma exclusão de TUDO?"):
            cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
            df_vazio = pd.DataFrame(columns=cols)
            conn.update(data=df_vazio); st.cache_data.clear(); st.rerun()
