import streamlit as st
import pandas as pd
import pymysql
from datetime import datetime
import time

# --- 1. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(page_title="Lavo e Levo V31 - TiDB", layout="wide")

# --- 2. CONEXÃO COM O BANCO TIDB (USANDO PYMYSQL) ---
def get_db_connection():
    try:
        return pymysql.connect(
            host=st.secrets["tidb"]["host"],
            port=st.secrets["tidb"]["port"],
            user=st.secrets["tidb"]["user"],
            password=st.secrets["tidb"]["password"],
            database=st.secrets["tidb"]["database"],
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor
        )
    except Exception as e:
        st.error(f"Erro de conexão com TiDB: {e}")
        st.stop()

# --- 3. FUNÇÕES DE BANCO DE DADOS ---
def carregar_dados():
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM producao ORDER BY data_registro DESC")
            result = cursor.fetchall()
            return pd.DataFrame(result) if result else pd.DataFrame()
    finally:
        conn.close()

def executar_sql(query, params):
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
        conn.close()
        return True
    except Exception as e:
        st.error(f"Erro na execução SQL: {e}")
        return False

# --- 4. SISTEMA DE AUTENTICAÇÃO ---
# --- SISTEMA DE AUTENTICAÇÃO ESTÁVEL ---
def verificar_login():
    # Inicializa o estado de autenticação se não existir
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    # Se já estiver logado, não mostra a tela de login
    if st.session_state["autenticado"]:
        return

    # Centraliza o formulário de login
    st.markdown("<h2 style='text-align: center;'>🔐 Login Lavo e Levo</h2>", unsafe_allow_html=True)
    
    # Usa um container e colunas para organizar a tela
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("form_login"):
            u = st.text_input("Usuário").upper().strip()
            p = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("ENTRAR NO SISTEMA")
            
            if entrar:
                if not u or not p:
                    st.warning("Preencha todos os campos.")
                else:
                    try:
                        conn = get_db_connection()
                        with conn.cursor() as cursor:
                            # Busca o usuário no TiDB
                            sql = "SELECT usuario FROM usuarios WHERE usuario = %s AND senha = %s"
                            cursor.execute(sql, (u, p))
                            user = cursor.fetchone()
                        conn.close()
                        
                        if user:
                            # Sucesso! Salva no estado da sessão
                            st.session_state["autenticado"] = True
                            st.session_state["operador"] = u
                            st.success(f"Acesso liberado! Aguarde...")
                            time.sleep(1) # Tempo para o usuário ver a mensagem
                            st.rerun()
                        else:
                            st.error("Usuário ou senha incorretos.")
                    except Exception as e:
                        st.error(f"Erro ao conectar ao banco: {e}")
    
    # Trava a execução do restante do script enquanto não logar
    st.stop()

# Chama a função logo no início do código
verificar_login()


# --- 6. SIDEBAR ---
st.sidebar.title("🧺 Lavo e Levo")
st.sidebar.write(f"Logado como: **{st.session_state['operador']}**")
turno_ativo = st.sidebar.selectbox("Turno:", ["Manhã", "Tarde", "Noite"])

if st.sidebar.button("🔄 Sincronizar Banco"):
    st.cache_data.clear()
    st.rerun()

if st.sidebar.button("🚪 Sair"):
    st.session_state["autenticado"] = False
    st.rerun()

# --- 7. DASHBOARD SUPERIOR ---
META_DIA = 5000.0
if not df.empty and 'p_lavagem' in df.columns:
    produzido = pd.to_numeric(df[df['status'].isin(["Gaiola", "Entregue"])]['p_lavagem']).sum()
else:
    produzido = 0.0

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
    if not df.empty:
        esp = df[df['status'] == "Aguardando Lavagem"]
        if not esp.empty:
            mq = st.selectbox("Máquina:", ["LAVADORA 01", "LAVADORA 02", "LAVADORA 03"])
            lts = st.multiselect("Lotes para Lavagem:", esp['id'].tolist())
            if st.button("🚀 INICIAR PROCESSO") and lts:
                for lid in lts:
                    executar_sql("UPDATE producao SET status=%s, maq=%s, etapa_inicio=%s WHERE id=%s", 
                                 ("Lavagem", mq, datetime.now().isoformat(), lid))
                st.success("Lavagem iniciada!")
                time.sleep(0.5)
                st.rerun()
        else: st.info("Nenhum lote aguardando.")

with tab3:
    if not df.empty:
        atv = df[df['status'].isin(["Lavagem", "Secagem", "Passadeira"])]
        if atv.empty: st.info("Sem produção ativa.")
        for i, row in atv.iterrows():
            minutos = int((datetime.now() - datetime.fromisoformat(str(row['etapa_inicio']))).total_seconds() // 60)
            with st.expander(f"Lote {row['id']} - {row['cli']} ({row['status']}) - {minutos} min", expanded=True):
                c1, c2 = st.columns(2)
                if row['status'] == "Lavagem":
                    if c1.button(f"🌀 Enviar para Secagem", key=f"sec_{row['id']}"):
                        executar_sql("UPDATE producao SET status='Secagem', etapa_inicio=%s WHERE id=%s", (datetime.now().isoformat(), row['id']))
                        st.rerun()
                elif row['status'] == "Secagem":
                    if c1.button(f"🧣 Enviar para Passadeira", key=f"pas_{row['id']}"):
                        executar_sql("UPDATE producao SET status='Passadeira', etapa_inicio=%s WHERE id=%s", (datetime.now().isoformat(), row['id']))
                        st.rerun()
                elif row['status'] == "Passadeira":
                    p_f = c2.number_input("Peso Final (kg)", value=float(row['p_in']), key=f"p_fin_{row['id']}")
                    if c1.button(f"🏁 Concluir Lote", key=f"con_{row['id']}"):
                        executar_sql("UPDATE producao SET status='Gaiola', p_lavagem=%s, etapa_inicio=%s WHERE id=%s", (p_f, datetime.now().isoformat(), row['id']))
                        st.rerun()

with tab5:
    st.subheader("Histórico TiDB")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Banco de dados vazio.")

st.markdown("---")
st.caption(f"Lavo e Levo V31 | TiDB Cloud (PyMySQL) | {datetime.now().strftime('%d/%m/%Y')}")
