import streamlit as st
import sqlite3
from datetime import datetime

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('lavanderia.db')
    c = conn.cursor()
    # Tabela de Operadores
    c.execute('''CREATE TABLE IF NOT EXISTS operadores 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT UNIQUE, senha TEXT)''')
    # Tabela de Pedidos
    c.execute('''CREATE TABLE IF NOT EXISTS pedidos (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 cliente TEXT,
                 servico TEXT,
                 valor REAL,
                 status TEXT,
                 data_entrada TEXT,
                 operador TEXT)''')
    
    c.execute('SELECT COUNT(*) FROM operadores')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO operadores (nome, senha) VALUES (?, ?)', ('admin', '1234'))
    conn.commit()
    conn.close()

# Funções de Apoio
def executar_query(sql, params=()):
    conn = sqlite3.connect('lavanderia.db')
    c = conn.cursor()
    c.execute(sql, params)
    res = c.fetchall()
    conn.commit()
    conn.close()
    return res

# --- 2. INICIALIZAÇÃO ---
init_db()
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'operador' not in st.session_state: st.session_state['operador'] = "Não identificado"

# --- 3. LOGICA DE ACESSO ---
if not st.session_state['logado']:
    st.title("🧺 Lavanderia App - Login")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = executar_query("SELECT * FROM operadores WHERE nome=? AND senha=?", (u, s))
            if res:
                st.session_state.update({"logado": True, "operador": u})
                st.rerun()
            else: st.error("Acesso negado.")
else:
    # --- MENU LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    menu = st.sidebar.radio("Navegação", ["Painel Principal", "Novo Pedido", "Cadastrar Operador"])
    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False, "operador": "Não identificado"})
        st.rerun()

    # --- TELAS ---
    if menu == "Painel Principal":
        st.title("📋 Pedidos Ativos")
        dados = executar_query("SELECT id, cliente, servico, valor, status, data_entrada FROM pedidos WHERE status != 'Entregue'")
        if dados:
            st.table(dados)
        else:
            st.info("Nenhum pedido pendente.")

    elif menu == "Novo Pedido":
        st.title("📥 Entrada de Roupa")
        with st.form("form_pedido"):
            cliente = st.text_input("Nome do Cliente")
            servico = st.selectbox("Tipo de Serviço", ["Lavagem Simples", "Lavagem + Secagem", "Passadoria", "Edredom/Tapete"])
            valor = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Registrar Pedido"):
                data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                executar_query("INSERT INTO pedidos (cliente, servico, valor, status, data_entrada, operador) VALUES (?,?,?,?,?,?)",
                               (cliente, servico, valor, "Em Processo", data_hoje, st.session_state['operador']))
                st.success("Pedido registrado!")

    elif menu == "Cadastrar Operador":
        st.title("👥 Gestão de Equipe")
        with st.form("cad_op"):
            n, s = st.text_input("Nome"), st.text_input("Senha", type="password")
            if st.form_submit_button("Salvar"):
                try:
                    executar_query("INSERT INTO operadores (nome, senha) VALUES (?,?)", (n, s))
                    st.success("Operador cadastrado!")
                except: st.error("Erro: Usuário já existe.")
