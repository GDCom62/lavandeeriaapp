import streamlit as st
import pandas as pd
import mysql.connector
from datetime import datetime
import io
import time

# --- 1. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="Lavo e Levo V31 - TiDB", layout="wide")

# --- 2. CONEXÃO COM O BANCO TIDB ---
# Os dados devem estar no .streamlit/secrets.toml ou nas configurações do Streamlit Cloud
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=st.secrets["tidb"]["host"],
            port=st.secrets["tidb"]["port"],
            user=st.secrets["tidb"]["user"],
            password=st.secrets["tidb"]["password"],
            database=st.secrets["tidb"]["database"],
            autocommit=True
        )
    except Exception as e:
        st.error(f"Erro de conexão com TiDB: {e}")
        st.stop()

# --- 3. FUNÇÕES DE BANCO DE DADOS ---
def carregar_dados():
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM producao ORDER BY data_registro DESC", conn)
    conn.close()
    return df

def executar_sql(query, params):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro na execução SQL: {e}")
        return False

# --- 4. SISTEMA DE AUTENTICAÇÃO ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("<h2 style='text-align: center;'>🔐 Login Industrial - TiDB</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            u = st.text_input("Operador").upper()
            p = st.text_input("Senha", type="password")
            if st.button("ENTRAR"):
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM usuarios WHERE usuario = %s AND senha = %s", (u, p))
                user = cursor.fetchone()
                conn.close()
                
                if user:
                    st.session_state["autenticado"] = True
                    st.session_state["operador"] = u
                    st.success("Acesso liberado!")
                    time.sleep(0.5) # Evita erro de removeChild
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.stop()

verificar_login()

# --- 5. CARREGAMENTO INICIAL ---
df = carregar_dados()

# --- 6. SIDEBAR ---
st.sidebar.title("🧺 Lavo e Levo")
st.sidebar.write(f"Logado como: **{st.session_state['operador']}**")
turno_ativo = st.sidebar.selectbox("Turno:", ["Manhã", "Tarde", "Noite"])

if st.sidebar.button("🔄 Sincronizar Banco"):
    st.rerun()

if st.sidebar.button("🚪 Sair"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 7. DASHBOARD SUPERIOR ---
META_DIA = 5000.0
produzido = df[df['status'].isin(["Gaiola", "Entregue"])]['p_lavagem'].astype(float).sum()
st.title("Gestão de Produção Industrial")
st.metric("Produção Hoje (kg)", f"{produzido:.1f}", f"{produzido - META_DIA:.1f} para meta")
st.progress(min(produzido / META_DIA, 1.0))

# --- 8. ABAS DE OPERAÇÃO ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Entrada", "🧼 Lavagem", "⚙️ Produção", "📊 Saída", "📜 Histórico"])

with tab1:
    with st.form("form_entrada", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente/Hospital")
        peso = c2.number_input("Peso Sujo (kg)", 0.1, 2000.0)
        if st.form_submit_button("REGISTRAR LOTE"):
            id_lote = datetime.now().strftime("%d%H%M%S")
            query = """INSERT INTO producao (id, cli, p_in, status, h_entrada, resp, turno, etapa_inicio) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
            if executar_sql(query, (id_lote, cli.upper(), peso, "Aguardando Lavagem", 
                                    datetime.now().strftime("%H:%M"), st.session_state['operador'], 
                                    turno_ativo, datetime.now().isoformat())):
                st.success(f"Lote {id_lote} registrado!")
                time.sleep(0.5)
                st.rerun()

with tab2:
    esp = df[df['status'] == "Aguardando Lavagem"]
    if not esp.empty:
        mq = st.selectbox("Máquina:", ["LAVADORA 01", "LAVADORA 02", "LAVADORA 03"])
        lts = st.multiselect("Lotes para Lavagem:", esp['id'].tolist(), 
                             format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)")
        if st.button("🚀 INICIAR PROCESSO") and lts:
            for lid in lts:
                query = "UPDATE producao SET status=%s, maq=%s, etapa_inicio=%s WHERE id=%s"
                executar_sql(query, ("Lavagem", mq, datetime.now().isoformat(), lid))
            st.success("Lavagem iniciada!")
            time.sleep(0.5)
            st.rerun()
    else: st.info("Nenhum lote aguardando.")

with tab3:
    atv = df[df['status'].isin(["Lavagem", "Secagem", "Passadeira"])]
    if atv.empty: st.info("Sem produção ativa.")
    for i, row in atv.iterrows():
        minutos = int((datetime.now() - datetime.fromisoformat(str(row['etapa_inicio']))).total_seconds() // 60)
        with st.container():
            st.markdown(f"**Lote {row['id']} - {row['cli']}** ({row['status']}) - {minutos} min")
            c1, c2 = st.columns([1, 2])
            if row['status'] == "Lavagem":
                if c1.button(f"🌀 Secagem", key=f"sec_{row['id']}"):
                    executar_sql("UPDATE producao SET status='Secagem', etapa_inicio=%s WHERE id=%s", (datetime.now().isoformat(), row['id']))
                    st.rerun()
            elif row['status'] == "Secagem":
                if c1.button(f"🧣 Passadeira", key=f"pas_{row['id']}"):
                    executar_sql("UPDATE producao SET status='Passadeira', etapa_inicio=%s WHERE id=%s", (datetime.now().isoformat(), row['id']))
                    st.rerun()
            elif row['status'] == "Passadeira":
                p_f = c2.number_input("Peso Final", value=float(row['p_in']), key=f"p_fin_{row['id']}")
                if c1.button(f"🏁 Concluir", key=f"con_{row['id']}"):
                    executar_sql("UPDATE producao SET status='Gaiola', p_lavagem=%s, etapa_inicio=%s WHERE id=%s", (p_f, datetime.now().isoformat(), row['id']))
                    st.rerun()
            st.divider()

with tab5:
    st.subheader("Histórico TiDB")
    st.dataframe(df, use_container_width=True)

st.markdown("---")
st.caption(f"Lavo e Levo V31 | TiDB Cloud Connected | {datetime.now().strftime('%d/%m/%Y')}")
