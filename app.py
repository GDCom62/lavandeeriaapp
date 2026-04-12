import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURAÇÕES E ESTADO ---
st.set_page_config(page_title="Lavanderia Hospitalar", layout="wide")

for key, val in {'logado': False, 'operador': "Visitante", 'funcao': "Nenhum"}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 2. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('gestao_lavanderia.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS lotes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, hospital TEXT, peso_entrada REAL, maquina TEXT, 
                 processo TEXT, status TEXT, inicio_lavagem TEXT, fim_lavagem TEXT, inicio_secagem TEXT, 
                 fim_secagem TEXT, inicio_acabamento TEXT, fim_acabamento TEXT, saida_motorista TEXT, 
                 motorista_nome TEXT, peso_saida REAL, gaiola_num TEXT, operador_lavagem TEXT, 
                 operador_secagem TEXT, operador_acabamento TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS contagem_itens (lote_id INTEGER, item TEXT, quantidade INTEGER)')
    # TABELA DE PÂNICO
    c.execute('CREATE TABLE IF NOT EXISTS alertas_panico (id INTEGER PRIMARY KEY AUTOINCREMENT, operador TEXT, data TEXT, resolvido INTEGER)')
    
    if not c.execute("SELECT * FROM operadores WHERE nome='admin'").fetchone():
        c.execute("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", ('admin', '1234', 'Administrador'))
    conn.commit()
    conn.close()

def executar_query(sql, params=()):
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        conn.cursor().execute(sql, params)
        conn.commit()

def consultar_db(sql, params=()):
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        return pd.read_sql_query(sql, conn, params=params)

init_db()

# --- 3. LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Lavanderia Hospitalar")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=? AND senha=?", (u, s))
            if not res.empty:
                st.session_state.update({"logado": True, "operador": res.iloc[0]['nome'], "funcao": res.iloc[0]['funcao']})
                st.rerun()
            else: st.error("Acesso negado.")
else:
    # --- 4. BARRA LATERAL E BOTÃO DE PÂNICO ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    
    st.sidebar.divider()
    if st.sidebar.button("🚨 BOTÃO DE PÂNICO", use_container_width=True, type="primary"):
        dt = datetime.now().strftime("%H:%M:%S")
        executar_query("INSERT INTO alertas_panico (operador, data, resolvido) VALUES (?,?,0)", (st.session_state['operador'], dt))
        st.sidebar.warning("Alerta de Pânico enviado!")

    menu_op = ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Motorista", "⚙️ Gestão", "📊 Relatórios"]
    if st.session_state['funcao'] == 'Motorista': menu_op = ["🚚 Motorista"]
    
    menu = st.sidebar.radio("Menu", menu_op)
    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False, "operador": "Visitante"})
        st.rerun()

    # --- 5. PAINEL GERAL (ALERTAS E PÂNICO) ---
    if menu == "Painel Geral":
        st.title("📈 Monitoramento")
        
        # Verificar Pânico
        panicos = consultar_db("SELECT * FROM alertas_panico WHERE resolvido=0")
        houve_som = False
        if not panicos.empty:
            houve_som = True
            for _, p in panicos.iterrows():
                st.error(f"🆘 **PÂNICO ATIVADO:** Operador {p['operador']} às {p['data']}! Verifique a produção imediatamente.")
                if st.button(f"Marcar como Resolvido ({p['id']})"):
                    executar_query("UPDATE alertas_panico SET resolvido=1 WHERE id=?", (p['id'],))
                    st.rerun()

        # Verificar Atrasos (>2h)
        df_l = consultar_db("SELECT id, hospital, status, inicio_lavagem FROM lotes WHERE status NOT IN ('Finalizado', 'Em Transito')")
        if not df_l.empty:
            agora = datetime.now()
            for _, row in df_l.iterrows():
                try:
                    atraso = (agora - pd.to_datetime(row['inicio_lavagem'])).total_seconds() / 60
                    if atraso > 120:
                        st.warning(f"⏳ **ATRASO:** Lote #{row['id']} ({row['hospital']}) há {int(atraso)} min!")
                        houve_som = True
                except: continue
            st.dataframe(df_l, use_container_width=True)
        
        if houve_som:
            st.components.v1.html('<audio autoplay><source src="https://soundjay.com"></audio>', height=0)

    # --- 6. FLUXO OPERACIONAL (RESUMIDO) ---
    elif menu == "1. Lavagem":
        with st.form("f1"):
            h = st.selectbox("Hospital", ["Hospital A", "Hospital B"])
            p = st.number_input("Peso", min_value=1.0)
            m = st.selectbox("Máquina", ["M1", "M2", "M3", "M4", "M5"])
            if st.form_submit_button("Iniciar"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, status, inicio_lavagem, operador_lavagem) VALUES (?,?,?,?,?,?)", (h, p, m, "Lavando", dt, st.session_state['operador']))
                st.rerun()

    elif menu == "2. Secagem":
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            if st.button("Confirmar Secagem"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Secando', fim_lavagem=?, inicio_secagem=?, operador_secagem=? WHERE id=?", (dt, dt, st.session_state['operador'], int(sel.split(" - ")[0])))
                st.rerun()

    elif menu == "3. Acabamento":
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Secando'")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            it = ["Lençol", "Fronha", "Pijama"]
            qtds = {i: st.number_input(i, min_value=0) for i in it}
            if st.button("Finalizar"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Pronto', fim_secagem=?, inicio_acabamento=?, operador_acabamento=? WHERE id=?", (dt, dt, st.session_state['operador'], int(sel.split(" - ")[0])))
                for k, v in qtds.items(): 
                    if v > 0: executar_query("INSERT INTO contagem_itens VALUES (?,?,?)", (int(sel.split(" - ")[0]), k, v))
                st.rerun()

    elif menu == "4. Expedição":
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Pronto'")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            ps, gai = st.number_input("Peso Saída"), st.text_input("Gaiola")
            if st.button("Liberar"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=?, peso_saida=?, gaiola_num=? WHERE id=?", (dt, ps, gai, int(sel.split(" - ")[0])))
                st.rerun()

    elif menu == "🚚 Motorista":
        df = consultar_db("SELECT * FROM lotes WHERE status='Disponível'")
        for _, r in df.iterrows():
            if st.button(f"Retirar Gaiola {r['gaiola_num']} - {r['hospital']}"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Finalizado', saida_motorista=?, motorista_nome=? WHERE id=?", (dt, st.session_state['operador'], r['id']))
                st.rerun()

    elif menu == "⚙️ Gestão":
        with st.form("equipe"):
            n, s, f = st.text_input("Nome"), st.text_input("Senha"), st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
            if st.form_submit_button("Cadastrar"):
                executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", (n, s, f))
                st.success("Cadastrado!")

    elif menu == "📊 Relatórios":
        df = consultar_db("SELECT * FROM lotes")
        st.dataframe(df)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
        st.download_button("Baixar Excel", buf.getvalue(), "relatorio.xlsx")
