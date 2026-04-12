import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURAÇÕES INICIAIS E ESTADO ---
st.set_page_config(page_title="Lavanderia Hospitalar", layout="wide")

if 'logado' not in st.session_state:
    st.session_state['logado'] = False
if 'operador' not in st.session_state:
    st.session_state['operador'] = "Visitante"
if 'funcao' not in st.session_state:
    st.session_state['funcao'] = "Nenhum"

# --- 2. FUNÇÕES DE BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('gestao_lavanderia.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS lotes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 hospital TEXT, peso_entrada REAL, maquina TEXT, processo TEXT, status TEXT,
                 inicio_lavagem TEXT, fim_lavagem TEXT, inicio_secagem TEXT, fim_secagem TEXT,
                 inicio_acabamento TEXT, fim_acabamento TEXT, saida_motorista TEXT, 
                 motorista_nome TEXT, peso_saida REAL, gaiola_num TEXT,
                 operador_lavagem TEXT, operador_secagem TEXT, operador_acabamento TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS contagem_itens (lote_id INTEGER, item TEXT, quantidade INTEGER)')
    
    c.execute("SELECT * FROM operadores WHERE nome='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", ('admin', '1234', 'Administrador'))
    conn.commit()
    conn.close()

def executar_query(sql, params=()):
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()

def consultar_db(sql, params=()):
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        return pd.read_sql_query(sql, conn, params=params)

init_db()

# --- 3. LÓGICA DE LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Gestão de Lavanderia Hospitalar")
    with st.container(border=True):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            conn = sqlite3.connect('gestao_lavanderia.db')
            c = conn.cursor()
            c.execute("SELECT nome, funcao FROM operadores WHERE nome=? AND senha=?", (u, s))
            user_data = c.fetchone()
            conn.close()
            if user_data:
                st.session_state.update({"logado": True, "operador": user_data[0], "funcao": user_data[1]})
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
else:
    # --- 4. BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    st.sidebar.caption(f"Função: {st.session_state['funcao']}")
    
    menu_opcoes = ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Retirada Motorista", "⚙️ Gestão", "📊 Relatórios"]
    if st.session_state['funcao'] == 'Motorista': menu_opcoes = ["🚚 Retirada Motorista"]
    elif st.session_state['funcao'] == 'Operador': menu_opcoes = ["1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição"]
    
    menu = st.sidebar.radio("Navegação", menu_opcoes)
    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False, "operador": "Visitante", "funcao": "Nenhum"})
        st.rerun()

    # --- 5. TELAS DO SISTEMA ---

    if menu == "Painel Geral":
        st.title("📈 Monitoramento em Tempo Real")
        df_l = consultar_db("SELECT id, hospital, status, inicio_lavagem, maquina FROM lotes WHERE status NOT IN ('Finalizado', 'Em Transito')")
        
        if not df_l.empty:
            houve_alerta = False
            agora = datetime.now()
            for _, row in df_l.iterrows():
                try:
                    inicio = pd.to_datetime(row['inicio_lavagem'])
                    tempo_parado = (agora - inicio).total_seconds() / 60
                    if tempo_parado > 120: # Alerta 2 horas
                        st.error(f"🚨 **ALERTA:** Lote #{row['id']} ({row['hospital']}) parado há {int(tempo_parado)} min na etapa {row['status']}!")
                        houve_alerta = True
                except: continue
            
            if houve_alerta:
                st.components.v1.html('<audio autoplay><source src="https://soundjay.com" type="audio/mpeg"></audio>', height=0)
            
            st.write("### Lista de Processamento Ativo")
            st.dataframe(df_l, use_container_width=True)
        else: st.info("Nenhum lote em processamento.")

    elif menu == "1. Lavagem":
        st.header("📥 Entrada de Lote")
        with st.form("lav"):
            h = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            p = st.number_input("Peso Entrada (kg)", min_value=1.0)
            m = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
            pr = st.selectbox("Processo", ["Leve", "Pesado", "Super Pesado"])
            if st.form_submit_button("Iniciar"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (?,?,?,?,?,?,?)",
                               (h, p, m, pr, "Lavando", dt, st.session_state['operador']))
                st.success("Lote registrado!")
                st.rerun()

    elif menu == "2. Secagem":
        st.header("🔥 Transferência para Secagem")
        df = consultar_db("SELECT id, hospital, maquina FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Selecione o Lote", df['id'].astype(str) + " - " + df['hospital'])
            if st.button("Confirmar Entrada na Secagem"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Secando', fim_lavagem=?, inicio_secagem=?, operador_secagem=? WHERE id=?", 
                               (dt, dt, st.session_state['operador'], int(sel.split(" - ")[0])))
                st.rerun()
        else: st.info("Nada na lavagem.")

    elif menu == "3. Acabamento":
        st.header("🧺 Dobra e Passadeira")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Secando'")
        if not df.empty:
            sel = st.selectbox("Lote vindo da Secagem", df['id'].astype(str) + " - " + df['hospital'])
            id_lote = int(sel.split(" - ")[0])
            st.write("---")
            itens = ["Lençóis", "Fronhas", "Oleados", "Pijamas", "Camisolas", "Campos", "Colchas"]
            c1, c2 = st.columns(2)
            contagem = {it: (c1.number_input(it, min_value=0) if i%2==0 else c2.number_input(it, min_value=0)) for i, it in enumerate(itens)}
            
            if st.button("Finalizar e Contar Itens"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Pronto', fim_secagem=?, inicio_acabamento=?, operador_acabamento=? WHERE id=?", 
                               (dt, dt, st.session_state['operador'], id_lote))
                for it, q in contagem.items():
                    if q > 0: executar_query("INSERT INTO contagem_itens VALUES (?,?,?)", (id_lote, it, q))
                st.rerun()

    elif menu == "4. Expedição":
        st.header("📦 Pesagem e Gaiola")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Pronto'")
        if not df.empty:
            sel = st.selectbox("Lote pronto", df['id'].astype(str) + " - " + df['hospital'])
            p_s = st.number_input("Peso Saída (kg)", min_value=0.1)
            gai = st.text_input("Gaiola N°")
            if st.button("Disponibilizar para Doca"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=?, peso_saida=?, gaiola_num=? WHERE id=?", 
                               (dt, p_s, gai, int(sel.split(" - ")[0])))
                st.rerun()

    elif menu == "🚚 Retirada Motorista":
        st.header("🚚 Check-out de Carga")
        df = consultar_db("SELECT id, hospital, gaiola_num, peso_saida FROM lotes WHERE status='Disponível'")
        if not df.empty:
            for _, row in df.iterrows():
                with st.container(border=True):
                    st.write(f"**Gaiola:** {row['gaiola_num']} | **Hospital:** {row['hospital']} | {row['peso_saida']}kg")
                    if st.button(f"Confirmar Retirada - Lote {row['id']}", key=f"mot_{row['id']}"):
                        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        executar_query("UPDATE lotes SET status='Finalizado', saida_motorista=?, motorista_nome=? WHERE id=?", 
                                       (dt, st.session_state['operador'], row['id']))
                        st.success("Retirada confirmada!")
                        st.rerun()

    elif menu == "⚙️ Gestão":
        st.header("⚙️ Cadastro de Equipe")
        with st.form("cad_equipe"):
            n, s, f = st.text_input("Nome"), st.text_input("Senha", type="password"), st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
            if st.form_submit_button("Cadastrar"):
                try:
                    executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", (n, s, f))
                    st.success("Cadastrado!")
                except: st.error("Usuário já existe.")

    elif menu == "📊 Relatórios":
        st.header("📊 Exportação e Produtividade")
        df_final = consultar_db("SELECT * FROM lotes")
        if not df_final.empty:
            st.dataframe(df_final)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                df_final.to_excel(wr, index=False)
            st.download_button("📥 Baixar Excel", data=buf.getvalue(), file_name="relatorio_lavanderia.xlsx")
