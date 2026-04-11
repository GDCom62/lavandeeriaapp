import streamlit as st
import sqlite3

# --- 1. CONFIGURAÇÃO E BANCO DE DADOS ---
# Conecta ao SQLite (cria o arquivo se não existir)
def init_db():
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS operadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            senha TEXT NOT NULL
        )
    ''')
    # Adiciona um operador padrão se a tabela estiver vazia
    c.execute('SELECT COUNT(*) FROM operadores')
    if c.fetchone()[0] == 0:
        c.execute('INSERT INTO operadores (nome, senha) VALUES (?, ?)', ('admin', '1234'))
    conn.commit()
    conn.close()

# Função para validar o login
def validar_login(usuario, senha):
    conn = sqlite3.connect('usuarios.db')
    c = conn.cursor()
    c.execute('SELECT * FROM operadores WHERE nome = ? AND senha = ?', (usuario, senha))
    resultado = c.fetchone()
    conn.close()
    return resultado

# --- 2. INICIALIZAÇÃO DO ESTADO (Prevenção de KeyError) ---
init_db() # Garante que o banco existe antes de tudo

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'operador' not in st.session_state:
    st.session_state['operador'] = "Não identificado"

# --- 3. LÓGICA DE NAVEGAÇÃO ---
if not st.session_state['logado']:
    # TELA DE LOGIN
    st.title("Lavanderia App - Acesso")
    with st.form("login_form"):
        usuario_input = st.text_input("Usuário")
        senha_input = st.text_input("Senha", type="password")
        botao_entrar = st.form_submit_button("Entrar")

        if botao_entrar:
            if validar_login(usuario_input, senha_input):
                st.session_state['logado'] = True
                st.session_state['operador'] = usuario_input
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

else:
    # --- BARRA LATERAL (Uso seguro da variável) ---
    st.sidebar.title(f"Operador: {st.session_state['operador']}")
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.session_state['operador'] = "Não identificado"
        st.rerun()

    # --- TELA PRINCIPAL ---
    st.title("Sistema de Lavanderia")
    st.subheader(f"Bem-vindo(a), {st.session_state['operador']}")
    
    # Exemplo de conteúdo do App
    cols = st.columns(3)
    cols[0].metric("Pedidos Hoje", "12")
    cols[1].metric("Em Processo", "5")
    cols[2].metric("Prontos", "7")
    
    st.divider()
    st.write("Seu sistema de gerenciamento está pronto para uso.")
