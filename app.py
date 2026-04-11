import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Lavo e Levo V31", layout="wide")

# --- CONEXÃO TIDB ---
# --- CONEXÃO TIDB ---
def get_db_connection():
    try:
        credenciais = st.secrets["tidb"]
        db_alvo = credenciais["database"] # Pegando o nome do banco (ex: test)
        
        return pymysql.connect(
            host=credenciais["host"],
            port=int(credenciais["port"]),
            user=credenciais["user"],
            password=credenciais["password"],
            database=db_alvo, # Força a conexão no banco correto
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        st.error(f"Erro: {e}")
        st.stop()

# --- LOGIN (QUERY LIMPA) ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return

    st.markdown("<h2 style='text-align: center;'>🔐 Login Lavo e Levo</h2>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        u = st.text_input("Operador").upper().strip()
        p = st.text_input("Senha", type="password")
        if st.form_submit_button("ENTRAR"):
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Usamos a query sem prefixo para o banco não se confundir
                cursor.execute("SELECT usuario FROM usuarios WHERE usuario = %s AND senha = %s", (u, p))
                user = cursor.fetchone()
            conn.close()
            
            if user:
                st.session_state["autenticado"] = True
                st.session_state["operador"] = u
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
    st.stop()


# --- DASHBOARD E OPERAÇÃO ---
st.sidebar.title(f"Operador: {st.session_state['operador']}")
if st.sidebar.button("🚪 Sair"):
    st.session_state["autenticado"] = False
    st.rerun()

# Carregar dados para o Dashboard
try:
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM producao ORDER BY data_registro DESC", conn)
    conn.close()
except:
    df = pd.DataFrame()

st.title("Gestão Industrial")

tab1, tab2, tab3 = st.tabs(["📥 Entrada", "🧼 Lavagem / Produção", "📜 Histórico"])

with tab1:
    with st.form("entrada"):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente")
        peso = c2.number_input("Peso (kg)", 0.1)
        if st.form_submit_button("REGISTRAR"):
            id_lote = datetime.now().strftime("%d%H%M%S")
            sql = "INSERT INTO producao (id, cli, p_in, status, h_entrada, resp, etapa_inicio) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            conn = get_db_connection()
            with conn.cursor() as cur:
                cur.execute(sql, (id_lote, cli.upper(), peso, "Aguardando Lavagem", datetime.now().strftime("%H:%M"), st.session_state['operador'], datetime.now().isoformat()))
            conn.close()
            st.success("Lote registrado!")
            time.sleep(1)
            st.rerun()

with tab3:
    st.dataframe(df, use_container_width=True)
