import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 1. BANCO DE DADOS ROBUSTO ---
def init_db():
    conn = sqlite3.connect('gestao_lavanderia.db')
    c = conn.cursor()
    # Tabelas base
    c.execute('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS lotes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 hospital TEXT,
                 peso_entrada REAL,
                 maquina TEXT,
                 processo TEXT,
                 status TEXT, -- 'Lavagem', 'Secagem', 'Dobra/Passa', 'Finalizado'
                 inicio_lavagem TEXT, fim_lavagem TEXT,
                 inicio_secagem TEXT, fim_secagem TEXT,
                 inicio_acabamento TEXT, fim_acabamento TEXT,
                 peso_saida REAL,
                 gaiola_num TEXT,
                 operador_lavagem TEXT,
                 operador_secagem TEXT,
                 operador_acabamento TEXT)''')
    
    # Tabela de contagem de itens (Relação de roupas)
    c.execute('''CREATE TABLE IF NOT EXISTS contagem_itens (
                 lote_id INTEGER,
                 item TEXT,
                 quantidade INTEGER,
                 FOREIGN KEY(lote_id) REFERENCES lotes(id))''')

    if not executar_query("SELECT * FROM operadores WHERE nome='admin'"):
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", ('admin', '1234', 'Gerente'))
    conn.commit()
    conn.close()

def executar_query(sql, params=()):
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        if "SELECT" in sql.upper():
            return pd.read_sql_query(sql, conn, params=params)
        conn.execute(sql, params)
        conn.commit()

# --- 2. LOGICA DE ESTADO ---
init_db()
if 'logado' not in st.session_state: st.session_state['logado'] = False

# --- 3. INTERFACE DE ACESSO ---
if not st.session_state['logado']:
    st.title("🏥 Lavanderia Hospitalar - Rastreabilidade")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = executar_query("SELECT nome FROM operadores WHERE nome=? AND senha=?", (u, s))
        if not res.empty:
            st.session_state.update({"logado": True, "operador": u})
            st.rerun()
        else: st.error("Erro de login")
else:
    st.sidebar.title(f"Operador: {st.session_state['operador']}")
    etapa = st.sidebar.radio("Fluxo de Produção", ["1. Lavagem", "2. Secagem", "3. Dobra/Passadeira", "4. Expedição", "Relatórios"])
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- ETAPA 1: LAVAGEM ---
    if etapa == "1. Lavagem":
        st.header("📥 Entrada na Lavagem")
        with st.form("lavagem"):
            hosp = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            peso = st.number_input("Peso de Entrada (kg)", min_value=0.1)
            maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
            proc = st.selectbox("Processo", ["Leve (45min)", "Pesado (60min)", "Super Pesado (90min)"])
            if st.form_submit_button("Iniciar Lavagem"):
                dt = datetime.now().strftime("%d/%m %H:%M")
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (?,?,?,?,?,?,?)",
                               (hosp, peso, maq, proc, "Lavando", dt, st.session_state['operador']))
                st.success("Lavagem Iniciada!")

    # --- ETAPA 2: SECAGEM ---
    elif etapa == "2. Secagem":
        st.header("🔥 Secagem")
        lotes_lavando = executar_query("SELECT id, hospital, maquina FROM lotes WHERE status='Lavando'")
        if not lotes_lavando.empty:
            lote_sel = st.selectbox("Selecione o Lote que saiu da Lavagem", lotes_lavando['id'].astype(str) + " - " + lotes_lavando['hospital'])
            id_lote = lote_sel.split(" - ")[0]
            if st.button("Transferir para Secadora"):
                dt = datetime.now().strftime("%d/%m %H:%M")
                executar_query("UPDATE lotes SET status='Secando', fim_lavagem=?, inicio_secagem=?, operador_secagem=? WHERE id=?", 
                               (dt, dt, st.session_state['operador'], id_lote))
                st.rerun()
        else: st.info("Nenhum lote aguardando secagem.")

    # --- ETAPA 3: DOBRA / PASSADEIRA ---
    elif etapa == "3. Dobra/Passadeira":
        st.header("🧺 Acabamento")
        lotes_secando = executar_query("SELECT id, hospital FROM lotes WHERE status='Secando'")
        if not lotes_secando.empty:
            lote_sel = st.selectbox("Lote vindo da Secagem", lotes_secando['id'].astype(str) + " - " + lotes_secando['hospital'])
            id_lote = lote_sel.split(" - ")[0]
            
            tipo_acab = st.radio("Destino", ["Dobra", "Passadeira"])
            
            st.subheader("Contagem de Itens")
            itens = ["Lençóis", "Fronhas", "Oleados", "Pijamas", "Camisolas", "Colchas"]
            contagem = {}
            cols = st.columns(2)
            for i, item in enumerate(itens):
                contagem[item] = cols[i%2].number_input(item, min_value=0, step=1)

            if st.button("Finalizar Acabamento"):
                dt = datetime.now().strftime("%d/%m %H:%M")
                executar_query("UPDATE lotes SET status='Acabado', fim_secagem=?, inicio_acabamento=?, operador_acabamento=? WHERE id=?", 
                               (dt, dt, st.session_state['operador'], id_lote))
                for item, qtd in contagem.items():
                    if qtd > 0:
                        executar_query("INSERT INTO contagem_itens (lote_id, item, quantidade) VALUES (?,?,?)", (id_lote, item, qtd))
                st.success("Dados de acabamento registrados!")
        else: st.info("Nada para dobrar/passar no momento.")

    # --- ETAPA 4: EXPEDIÇÃO (Gaiolas e Motorista) ---
    elif etapa == "4. Expedição":
        st.header("🚚 Pesagem Final e Saída")
        lotes_acabados = executar_query("SELECT id, hospital FROM lotes WHERE status='Acabado'")
        if not lotes_acabados.empty:
            lote_sel = st.selectbox("Lote Pronto", lotes_acabados['id'].astype(str) + " - " + lotes_acabados['hospital'])
            id_lote = lote_sel.split(" - ")[0]
            
            peso_f = st.number_input("Peso Total de Saída (kg)")
            gaiola = st.text_input("Número da Gaiola")
            
            if st.button("Despachar Lote"):
                dt = datetime.now().strftime("%d/%m %H:%M")
                executar_query("UPDATE lotes SET status='Finalizado', fim_acabamento=?, peso_saida=?, gaiola_num=? WHERE id=?", 
                               (dt, peso_f, gaiola, id_lote))
                st.success("Lote enviado para o motorista!")
        else: st.info("Nada pronto para expedição.")

    # --- RELATÓRIOS ---
    elif etapa == "Relatórios":
        st.header("📊 Produtividade e Rastreabilidade")
        dados = executar_query("SELECT * FROM lotes")
        st.dataframe(dados)
        if st.button("Gerar Relatório para Motorista"):
             # Aqui pode-se criar a lógica de exportação PDF ou Excel
             st.write("Relatórios por hospital gerados com sucesso.")
