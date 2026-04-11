import streamlit as st

# 1. INICIALIZAÇÃO DO SESSION STATE (Evita o KeyError)
if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'operador' not in st.session_state:
    st.session_state['operador'] = ""

# --- FUNÇÃO DE LOGIN ---
def realizar_login(nome_usuario):
    if nome_usuario.strip():
        st.session_state['logado'] = True
        st.session_state['operador'] = nome_usuario
        st.rerun() # Atualiza a página para mostrar o app logado
    else:
        st.error("Por favor, digite o nome do operador.")

# --- LÓGICA DE NAVEGAÇÃO ---
if not st.session_state['logado']:
    # Tela de Login
    st.title("Lavanderia App - Acesso")
    usuario = st.text_input("Nome do Operador")
    if st.button("Entrar"):
        realizar_login(usuario)

else:
    # --- INTERFACE DO APP LOGADO ---
    
    # BARRA LATERAL (Onde ocorria o seu erro)
    st.sidebar.title(f"Operador: {st.session_state['operador']}")
    
    if st.sidebar.button("Sair/Logout"):
        st.session_state['logado'] = False
        st.session_state['operador'] = ""
        st.rerun()

    # CONTEÚDO PRINCIPAL
    st.title("Painel Principal da Lavanderia")
    st.write(f"Bem-vindo(a), {st.session_state['operador']}!")
    
    # Exemplo de funcionalidade
    opcao = st.selectbox("Selecione uma tarefa", ["Entrada de Roupas", "Saída/Entrega", "Relatórios"])
    st.info(f"Você selecionou: {opcao}")

    # Seu código adicional (banco de dados, cálculos, etc) deve vir aqui
