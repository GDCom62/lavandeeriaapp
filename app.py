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
# --- 3. CONEXÃO REVISADA E BLINDADA ---
@st.cache_resource(ttl=600)  # Faz o app "lembrar" da conexão por 10 min
def conectar_planilha():
    try:
        # Tenta conectar usando os Secrets
        return st.connection("gsheets", type=GSheetsConnection)
    except Exception as e:
        st.error(f"Erro na Instalação da Conexão: {e}")
        return None

conn = conectar_planilha()

def buscar_dados():
    if conn is not None:
        try:
            # Força a leitura ignorando o cache se der erro
            return conn.read(spreadsheet=URL_PLANILHA, ttl="0")
        except Exception as e:
            st.warning(f"Erro ao ler dados: {e}. Tentando reconectar...")
            st.cache_resource.clear() # Limpa a conexão travada
            return None
    return None

df = buscar_dados()

# Se o DF vier vazio ou der erro, cria a estrutura básica para o app não travar
if df is None or not isinstance(df, pd.DataFrame):
    cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
    df = pd.DataFrame(columns=cols)
else:
    # Garante que colunas numéricas não tenham texto/nulos que causam o TypeError
    df["p_in"] = pd.to_numeric(df["p_in"], errors='coerce').fillna(0.0)
    df["p_lavagem"] = pd.to_numeric(df["p_lavagem"], errors='coerce').fillna(0.0)

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
     # --- ABA 3: PRODUÇÃO (Adicionando o Check-out da Gaiola) ---
with tab3:
    # ... (mantenha o código anterior de Lavagem/Secagem/Passadeira) ...
    
    st.divider()
    st.subheader("📦 Prontos na Gaiola (Aguardando Saída)")
    na_gaiola = df[df['status'] == "Gaiola"]
    
    if not na_gaiola.empty:
        for i, row in na_gaiola.iterrows():
            with st.expander(f"🚚 SAÍDA: {row['cli']} - {row['p_lavagem']}kg"):
                c1, c2 = st.columns([3, 1])
                c1.write(f"ID: {row['id']} | Entrou na Gaiola às: {row['etapa_inicio'][11:16]}")
                if c2.button("ENTREGAR", key=f"entregar_{row['id']}"):
                    df.at[i, 'status'] = "Entregue"
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
    else:
        st.info("Nenhum lote aguardando na Gaiola no momento.")

# --- ABA 4: ADMIN / RELATÓRIOS (Cálculo de Tempos) ---
with tab4:
    st.subheader("📊 Performance e Indicadores de Tempo")

    if not df.empty:
        # Converter h_entrada (HH:MM) para datetime do dia atual para cálculo
        hoje = datetime.now().date()
        
        def calcular_minutos(row):
            try:
                # Criamos um datetime completo usando a hora de entrada
                entrada_dt = datetime.combine(hoje, datetime.strptime(row['h_entrada'], "%H:%M").time())
                # Se já foi entregue, usa o etapa_inicio (que é o fim do processo), se não, usa AGORA
                fim_dt = datetime.fromisoformat(row['etapa_inicio']) if row['status'] == "Entregue" else datetime.now()
                
                diff = (fim_dt - entrada_dt).total_seconds() / 60
                return max(0, diff) # Evita números negativos se o servidor tiver atraso
            except:
                return 0

        # Criar coluna temporária de minutos totais
        df_tempos = df.copy()
        df_tempos['minutos_totais'] = df_tempos.apply(calcular_minutos, axis=1)
        
        # Média Geral
        tempo_medio_geral = df_tempos['minutos_totais'].mean()
        
        # 1. MÉTRICAS DE TEMPO
        m1, m2, m3 = st.columns(3)
        m1.metric("Tempo Médio Total", f"{tempo_medio_geral:.0f} min")
        
        # Tempo médio por cliente (Top 5 mais demorados)
        tempo_por_cli = df_tempos.groupby('cli')['minutos_totais'].mean().sort_values(ascending=False).head(5)
        
        # 2. GRÁFICOS DE TEMPO
        col_t1, col_t2 = st.columns(2)
        
        with col_t1:
            st.markdown("**🕒 Tempo Médio por Cliente (min)**")
            st.bar_chart(tempo_por_cli, color="#ffc107")
            
        with col_t2:
            st.markdown("**📈 Eficiência por Turno (Tempo Médio)**")
            tempo_turno = df_tempos.groupby('turno')['minutos_totais'].mean()
            st.line_chart(tempo_turno, color="#17a2b8")

        st.divider()

    # ... (Aqui continua o código anterior dos gráficos de Kg e Status) ...
