import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. BANCO DE DADOS (Conexão Segura) ---
def init_db():
    conn = sqlite3.connect('lavanderia.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, senha TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 cliente TEXT, servico TEXT, valor REAL, status TEXT, 
                 data_entrada TEXT, data_saida TEXT, operador TEXT)''')
    c.execute('SELECT COUNT(*) FROM operadores')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO operadores (nome, senha) VALUES (?, ?)', ('admin', '1234'))
    conn.commit()
    conn.close()

def executar_query(sql, params=()):
    conn = sqlite3.connect('lavanderia.db', check_same_thread=False)
    try:
        if "SELECT" in sql.upper():
            return pd.read_sql_query(sql, conn, params=params)
        else:
            c = conn.cursor()
            c.execute(sql, params)
            conn.commit()
    finally:
        conn.close()

# --- 2. INICIALIZAÇÃO DE ESTADO ---
init_db()
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'operador' not in st.session_state:
    st.session_state['operador'] = "Visitante"

# --- 3. LÓGICA DE INTERFACE ---
placeholder = st.empty()

if not st.session_state['logado']:
    with placeholder.container():
        st.title("🧺 Lavanderia App")
        st.subheader("Login de Acesso")
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            # Verificação direta sem abrir múltiplas conexões
            conn = sqlite3.connect('lavanderia.db')
            c = conn.cursor()
            c.execute("SELECT nome FROM operadores WHERE nome=? AND senha=?", (u, s))
            user = c.fetchone()
            conn.close()
            
            if user:
                st.session_state['logado'] = True
                st.session_state['operador'] = user[0]
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

else:
    # SE LOGADO, LIMPA O LOGIN E MOSTRA O APP
    placeholder.empty()
    
    # MENU LATERAL
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    menu = st.sidebar.radio("Navegação", ["Painel Principal", "Novo Pedido", "Relatórios", "Configurações"])
    
    if st.sidebar.button("Encerrar Sessão"):
        st.session_state['logado'] = False
        st.session_state['operador'] = "Visitante"
        st.rerun()

    # --- TELAS ---
    if menu == "Painel Principal":
        st.title("📋 Pedidos Ativos")
        busca = st.text_input("🔍 Filtrar por nome de cliente...")
        
        sql = "SELECT * FROM pedidos WHERE status != 'Entregue'"
        params = []
        if busca:
            sql += " AND cliente LIKE ?"
            params.append(f"%{busca}%")
            
        df = executar_query(sql, params)
        
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                with st.expander(f"ID #{row['id']} - {row['cliente']}"):
                    st.write(f"**Serviço:** {row['servico']} | **Valor:** R$ {row['valor']:.2f}")
                    if st.button(f"Baixar Pedido {row['id']}", key=f"b_{row['id']}"):
                        dt_s = datetime.now().strftime("%d/%m/%Y %H:%M")
                        executar_query("UPDATE pedidos SET status='Entregue', data_saida=? WHERE id=?", (dt_s, row['id']))
                        st.rerun()
        else:
            st.info("Nenhum pedido pendente.")

    elif menu == "Novo Pedido":
        st.title("📥 Registrar Entrada")
        with st.form("f_pedido", clear_on_submit=True):
            cl = st.text_input("Nome do Cliente")
            sv = st.selectbox("Serviço", ["Lavagem", "Secagem", "Passadoria", "Completo"])
            vl = st.number_input("Valor", min_value=0.0)
            if st.form_submit_button("Salvar"):
                dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                executar_query("INSERT INTO pedidos (cliente, servico, valor, status, data_entrada, operador) VALUES (?,?,?,?,?,?)",
                               (cl, sv, vl, "Em Processo", dt, st.session_state['operador']))
                st.success("Pedido salvo!")

    elif menu == "Relatórios":
        st.title("💰 Financeiro")
        df_f = executar_query("SELECT * FROM pedidos")
        if df_f is not None and not df_f.empty:
            faturado = df_f[df_f['status'] == 'Entregue']['valor'].sum()
            st.metric("Total Recebido", f"R$ {faturado:.2f}")
            st.dataframe(df_f)

    elif menu == "Configurações":
        st.title("⚙️ Operadores")
        with st.form("f_op"):
            n, s = st.text_input("Novo Usuário"), st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Cadastrar"):
                try:
                    executar_query("INSERT INTO operadores (nome, senha) VALUES (?,?)", (n, s))
                    st.success("Cadastrado!")
                except: st.error("Erro: Usuário já existe.")
