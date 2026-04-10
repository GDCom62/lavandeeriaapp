# --- SISTEMA DE AUTENTICAÇÃO VIA GSHEETS ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("<h2 style='text-align: center;'>🔐 Acesso Restrito - Lavo e Levo</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            usuario_input = st.text_input("Usuário (Operador)").upper()
            senha_input = st.text_input("Senha", type="password")
            
            if st.button("ENTRAR"):
                try:
                    # Busca a aba 'usuarios' da mesma planilha
                    df_usuarios = conn.read(worksheet="usuarios")
                    
                    # Verifica se o usuário e senha batem com alguma linha da planilha
                    user_match = df_usuarios[
                        (df_usuarios['usuario'].str.upper() == usuario_input) & 
                        (df_usuarios['senha'].astype(str) == senha_input)
                    ]

                    if not user_match.empty:
                        st.session_state["autenticado"] = True
                        st.session_state["operador"] = usuario_input
                        st.success(f"Bem-vindo, {usuario_input}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except Exception as e:
                    st.error("Erro ao carregar lista de usuários. Verifique se a aba 'usuarios' existe na planilha.")
        st.stop()

verificar_login()
