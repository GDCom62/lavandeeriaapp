import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('lavanderia.db')
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
    conn = sqlite3.connect('lavanderia.db')
    res = pd.read_sql_query(sql, conn, params=params) if "SELECT" in sql.upper() else None
    if res is None:
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()
    conn.close()
    return res

# --- 2. INICIALIZAÇÃO ---
init_db()
if 'logado' not in st.session_state: st.session_state['logado'] = False
if 'operador' not in st.session_state: st.session_state['operador'] = "Não identificado"

# --- 3. LÓGICA DE ACESSO ---
if not st.session_state['logado']:
    st.title("🧺 Lavanderia App - Login")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            conn = sqlite3.connect('lavanderia.db')
            c = conn.cursor()
            c.execute("SELECT * FROM operadores WHERE nome=? AND senha=?", (u, s))
            if c.fetchone():
                st.session_state.update({"logado": True, "operador": u})
                st.rerun()
            else: st.error("Acesso negado.")
            conn.close()
else:
    # --- MENU LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    menu = st.sidebar.radio("Navegação", ["Painel Principal", "Novo Pedido", "Relatório/Faturamento", "Configurações"])
    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False, "operador": "Não identificado"})
        st.rerun()

    # --- TELAS ---
    if menu == "Painel Principal":
        st.title("📋 Pedidos em Aberto")
        df = executar_query("SELECT id, cliente, servico, valor, status, data_entrada FROM pedidos WHERE status != 'Entregue'")
        
        if not df.empty:
            for i, row in df.iterrows():
                with st.expander(f"Pedido #{row['id']} - {row['cliente']}"):
                    st.write(f"**Serviço:** {row['servico']} | **Valor:** R$ {row['valor']:.2f}")
                    if st.button(f"Confirmar Entrega #{row['id']}", key=f"btn_{row['id']}"):
                        data_saida = datetime.now().strftime("%d/%m/%Y %H:%M")
                        executar_query("UPDATE pedidos SET status='Entregue', data_saida=? WHERE id=?", (data_saida, row['id']))
                        st.success("Pedido entregue!")
                        st.rerun()
        else:
            st.info("Nenhum pedido pendente.")

    elif menu == "Novo Pedido":
        st.title("📥 Entrada de Roupa")
        with st.form("form_pedido"):
            cliente = st.text_input("Nome do Cliente")
            servico = st.selectbox("Tipo", ["Lavagem Simples", "Lavagem + Secagem", "Passadoria", "Edredom/Tapete"])
            valor = st.number_input("Valor (R$)", min_value=0.0, step=0.50)
            if st.form_submit_button("Registrar"):
                dt = datetime.now().strftime("%d/%m/%Y %H:%M")
                executar_query("INSERT INTO pedidos (cliente, servico, valor, status, data_entrada, operador) VALUES (?,?,?,?,?,?)",
                               (cliente, servico, valor, "Em Processo", dt, st.session_state['operador']))
                st.success("Pedido cadastrado!")

    elif menu == "Relatório/Faturamento":
        st.title("💰 Financeiro e Histórico")
        df_total = executar_query("SELECT * FROM pedidos")
        if not df_total.empty:
            total_ganho = df_total[df_total['status'] == 'Entregue']['valor'].sum()
            st.metric("Total Faturado (Entregues)", f"R$ {total_ganho:.2f}")
            st.write("### Todos os Registros")
            st.dataframe(df_total)
        else:
            st.warning("Sem dados para exibir.")

    elif menu == "Configurações":
        st.subheader("Cadastrar Novo Operador")
        with st.form("cad"):
            n, s = st.text_input("Nome"), st.text_input("Senha", type="password")
            if st.form_submit_button("Salvar"):
                try:
                    executar_query("INSERT INTO operadores (nome, senha) VALUES (?,?)", (n, s))
                    st.success("Cadastrado!")
                except: st.error("Usuário já existe.")
