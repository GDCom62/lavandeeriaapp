import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- 1. INICIALIZAÇÃO DO SESSION STATE (Evita KeyError) ---
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
    # Criar tabelas
    c.execute('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS lotes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 hospital TEXT, peso_entrada REAL, maquina TEXT, processo TEXT, status TEXT,
                 inicio_lavagem TEXT, fim_lavagem TEXT,
                 inicio_secagem TEXT, fim_secagem TEXT,
                 inicio_acabamento TEXT, fim_acabamento TEXT,
                 saida_motorista TEXT, motorista_nome TEXT,
                 peso_saida REAL, gaiola_num TEXT,
                 operador_lavagem TEXT, operador_secagem TEXT, operador_acabamento TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS contagem_itens (lote_id INTEGER, item TEXT, quantidade INTEGER)')
    
    # Verificar e criar usuário admin de forma segura (sem ValueError)
    c.execute("SELECT * FROM operadores WHERE nome='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", ('admin', '1234', 'Administrador'))
    
    conn.commit()
    conn.close()

def executar_query(sql, params=()):
    """Executa comandos de INSERT, UPDATE e DELETE"""
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        c = conn.cursor()
        c.execute(sql, params)
        conn.commit()

def consultar_db(sql, params=()):
    """Executa consultas SELECT e retorna um DataFrame"""
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        return pd.read_sql_query(sql, conn, params=params)

# --- 3. EXECUÇÃO INICIAL ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")
init_db()

# --- 4. LÓGICA DE LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Gestão de Lavanderia Hospitalar")
    st.subheader("Controle de Rastreabilidade e Produtividade")
    
    with st.form("login_form"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            # Consulta segura sem causar conflito com booleano do Pandas
            conn = sqlite3.connect('gestao_lavanderia.db')
            c = conn.cursor()
            c.execute("SELECT nome, funcao FROM operadores WHERE nome=? AND senha=?", (u, s))
            user_data = c.fetchone()
            conn.close()
            
            if user_data:
                st.session_state.update({
                    "logado": True, 
                    "operador": user_data[0], 
                    "funcao": user_data[1]
                })
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")

# --- 5. APP LOGADO ---
else:
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    st.sidebar.info(f"Perfil: {st.session_state['funcao']}")
    
    # Menu dinâmico por perfil
    if st.session_state['funcao'] == 'Administrador':
        menu = st.sidebar.radio("Navegação", ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Retirada Motorista", "⚙️ Gestão de Equipe", "📊 Exportar Excel"])
    elif st.session_state['funcao'] == 'Motorista':
        menu = st.sidebar.radio("Navegação", ["🚚 Retirada Motorista"])
    else:
        menu = st.sidebar.radio("Navegação", ["1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição"])

    if st.sidebar.button("Sair do Sistema"):
        st.session_state.update({"logado": False, "operador": "Visitante", "funcao": "Nenhum"})
        st.rerun()

    # --- TELAS ---
    if menu == "Painel Geral":
        st.title("📈 Monitoramento de Lotes Ativos")
        df_l = consultar_db("SELECT id, hospital, status, maquina, operador_lavagem FROM lotes WHERE status != 'Finalizado'")
        st.dataframe(df_l, use_container_width=True)

    elif menu == "1. Lavagem":
        st.header("📥 Entrada de Lote na Lavagem")
        with st.form("f_lavagem"):
            hosp = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            peso = st.number_input("Peso de Entrada (kg)", min_value=1.0)
            maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
            proc = st.selectbox("Tipo de Lavagem", ["Leve", "Pesado", "Super Pesado"])
            if st.form_submit_button("Iniciar Lavagem"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (?,?,?,?,?,?,?)",
                               (hosp, peso, maq, proc, "Lavando", dt, st.session_state['operador']))
                st.success("Processo iniciado!")
                st.rerun()

    elif menu == "2. Secagem":
        st.header("🔥 Transferir para Secadoras")
        df = consultar_db("SELECT id, hospital, maquina FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Lote que concluiu lavagem", df['id'].astype(str) + " - " + df['hospital'])
            if st.button("Confirmar Entrada na Secagem"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Secando', fim_lavagem=?, inicio_secagem=?, operador_secagem=? WHERE id=?", 
                               (dt, dt, st.session_state['operador'], int(sel.split(" - ")[0])))
                st.success("Lote enviado para secagem!")
                st.rerun()
        else: st.info("Nenhum lote aguardando secagem.")

    elif menu == "3. Acabamento":
        st.header("🧺 Dobra e Passadeira")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Secando'")
        if not df.empty:
            sel = st.selectbox("Lote para acabamento", df['id'].astype(str) + " - " + df['hospital'])
            id_lote = int(sel.split(" - ")[0])
            itens_lista = ["Lençóis", "Fronhas", "Oleados", "Pijamas", "Camisolas", "Campos", "Colchas"]
            contagem = {}
            c1, c2 = st.columns(2)
            for i, item in enumerate(itens_lista):
                contagem[item] = c1.number_input(item, min_value=0) if i%2==0 else c2.number_input(item, min_value=0)
            
            if st.button("Finalizar Acabamento"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Pronto', fim_secagem=?, inicio_acabamento=?, operador_acabamento=? WHERE id=?", 
                               (dt, dt, st.session_state['operador'], id_lote))
                for it, qtd in contagem.items():
                    if qtd > 0: executar_query("INSERT INTO contagem_itens VALUES (?,?,?)", (id_lote, it, qtd))
                st.success("Contagem registrada!")
                st.rerun()
        else: st.info("Nada na secagem.")

    elif menu == "4. Expedição":
        st.header("📦 Pesagem e Gaiola")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Pronto'")
        if not df.empty:
            sel = st.selectbox("Lote pronto", df['id'].astype(str) + " - " + df['hospital'])
            id_lote = int(sel.split(" - ")[0])
            p_saida = st.number_input("Peso Final (kg)", min_value=0.1)
            gaiola = st.text_input("Número da Gaiola")
            if st.button("Disponibilizar para Motorista"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=?, peso_saida=?, gaiola_num=? WHERE id=?", 
                               (dt, p_saida, gaiola, id_lote))
                st.success("Lote enviado para doca!")
                st.rerun()

    elif menu == "🚚 Retirada Motorista":
        st.header("🚚 Retirada de Gaiolas")
        df = consultar_db("SELECT id, hospital, gaiola_num, peso_saida FROM lotes WHERE status='Disponível'")
        if not df.empty:
            for _, row in df.iterrows():
                with st.container(border=True):
                    st.write(f"**Gaiola:** {row['gaiola_num']} | **Hospital:** {row['hospital']} | {row['peso_saida']}kg")
                    if st.button(f"Confirmar Retirada - Lote {row['id']}", key=f"btn_{row['id']}"):
                        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        executar_query("UPDATE lotes SET status='Finalizado', saida_motorista=?, motorista_nome=? WHERE id=?", 
                                       (dt, st.session_state['operador'], row['id']))
                        st.success("Retirada confirmada!")
                        st.rerun()
        else: st.info("Nenhuma gaiola aguardando motorista.")

    elif menu == "⚙️ Gestão de Equipe":
        st.header("⚙️ Cadastro de Colaboradores")
        with st.form("cad_equipe"):
            n = st.text_input("Nome")
            s = st.text_input("Senha", type="password")
            f = st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
            if st.form_submit_button("Cadastrar"):
                try:
                    executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", (n, s, f))
                    st.success("Cadastrado com sucesso!")
                except: st.error("Erro: Usuário já existe.")
        
        st.dataframe(consultar_db("SELECT nome, funcao FROM operadores"))

    elif menu == "📊 Exportar Excel":
        st.header("📊 Exportação de Produtividade")
        df_final = consultar_db("SELECT * FROM lotes")
        if not df_final.empty:
            st.dataframe(df_final)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False)
            st.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="lavanderia_hosp.xlsx")
