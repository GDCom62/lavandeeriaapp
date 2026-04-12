import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURAÇÕES E ESTADO ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")

for key, val in {'logado': False, 'operador': "Visitante", 'funcao': "Nenhum", 'etapa_atual': "Início"}.items():
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
    c.execute('CREATE TABLE IF NOT EXISTS alertas_panico (id INTEGER PRIMARY KEY AUTOINCREMENT, operador TEXT, etapa TEXT, data TEXT, resolvido INTEGER)')
    
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
    st.title("🏥 Gestão Lavanderia Hospitalar")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=? AND senha=?", (u, s))
            if not res.empty:
                st.session_state.update({"logado": True, "operador": res.iloc[0]['nome'], "funcao": res.iloc[0]['funcao']})
                st.rerun()
            else: st.error("Acesso negado.")
else:
    # --- 4. BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    
    if st.sidebar.button("🚨 PÂNICO", use_container_width=True, type="primary"):
        executar_query("INSERT INTO alertas_panico (operador, etapa, data, resolvido) VALUES (?,?,?,0)", 
                       (st.session_state['operador'], st.session_state['etapa_atual'], datetime.now().strftime("%H:%M:%S")))
        st.sidebar.warning("Alerta enviado!")

    menu_op = ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Motorista", "⚙️ Gestão", "📊 Relatórios"]
    if st.session_state['funcao'] == 'Motorista': menu_op = ["🚚 Motorista"]
    
    menu = st.sidebar.radio("Menu", menu_op)
    st.session_state['etapa_atual'] = menu

    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False, "operador": "Visitante"})
        st.rerun()

    # --- 5. PAINEL GERAL (MONITORAMENTO E ABORTO) ---
    if menu == "Painel Geral":
        st.title("📈 Monitoramento e Gestão de Crise")
        
        # Alertas de Pânico e Atraso
        panicos = consultar_db("SELECT * FROM alertas_panico WHERE resolvido=0")
        if not panicos.empty:
            for _, p in panicos.iterrows():
                st.error(f"🆘 **PÂNICO:** {p['operador']} em {p['etapa']} ({p['data']})")
                if st.button(f"Resolver #{p['id']}"):
                    executar_query("UPDATE alertas_panico SET resolvido=1 WHERE id=?", (p['id'],))
                    st.rerun()
            st.components.v1.html('<audio autoplay><source src="https://soundjay.com"></audio>', height=0)

        st.divider()
        st.subheader("🛠️ Abortar ou Reiniciar Lotes")
        lotes_ativos = consultar_db("SELECT id, hospital, status FROM lotes WHERE status != 'Finalizado'")
        if not lotes_ativos.empty:
            sel_r = st.selectbox("Escolha um lote para ação emergencial", lotes_ativos['id'].astype(str) + " - " + lotes_ativos['hospital'])
            id_r = int(sel_r.split(" - "))
            c1, c2 = st.columns(2)
            if c1.button("🔄 REINICIAR TUDO (Voltar à Lavagem)"):
                executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL, fim_secagem=NULL, inicio_acabamento=NULL, fim_acabamento=NULL WHERE id=?", (id_r,))
                st.success("Lote resetado!")
                st.rerun()
            if c2.button("❌ EXCLUIR LOTE PERMANENTEMENTE"):
                executar_query("DELETE FROM lotes WHERE id=?", (id_r,))
                st.rerun()

    # --- 6. FLUXO OPERACIONAL COM ESTORNO ---
    elif menu == "1. Lavagem":
        with st.form("f1"):
            h = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            p = st.number_input("Peso (kg)", min_value=1.0)
            m = st.selectbox("Máquina", ["M1", "M2", "M3", "M4", "M5"])
            if st.form_submit_button("Iniciar"):
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, status, inicio_lavagem, operador_lavagem) VALUES (?,?,?,?,?,?)", 
                               (h, p, m, "Lavando", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state['operador']))
                st.rerun()

    elif menu == "2. Secagem":
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status IN ('Lavando', 'Secando')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status_atual = df[df['id'] == id_l]['status'].values[0]
            
            if status_atual == 'Lavando':
                if st.button("✅ Iniciar Secagem"):
                    executar_query("UPDATE lotes SET status='Secando', fim_lavagem=?, inicio_secagem=?, operador_secagem=? WHERE id=?", 
                                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state['operador'], id_l))
                    st.rerun()
            else:
                st.info("Lote em Secagem...")
                if st.button("⏪ ESTORNAR (Voltar para Lavagem)"):
                    executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL WHERE id=?", (id_l,))
                    st.rerun()

    elif menu == "3. Acabamento":
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status_atual = df[df['id'] == id_l]['status'].values[0]

            if status_atual == 'Secando':
                it = ["Lençol", "Fronha", "Pijama", "Campo", "Colcha"]
                qtds = {item: st.number_input(item, min_value=0) for item in it}
                if st.button("✅ Finalizar e Contar"):
                    executar_query("UPDATE lotes SET status='Pronto', fim_secagem=?, inicio_acabamento=?, operador_acabamento=? WHERE id=?", 
                                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state['operador'], id_l))
                    for k, v in qtds.items(): 
                        if v > 0: executar_query("INSERT INTO contagem_itens VALUES (?,?,?)", (id_l, k, v))
                    st.rerun()
            else:
                if st.button("⏪ ESTORNAR (Voltar para Secagem)"):
                    executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL, inicio_acabamento=NULL WHERE id=?", (id_l,))
                    executar_query("DELETE FROM contagem_itens WHERE lote_id=?", (id_l,))
                    st.rerun()

    elif menu == "4. Expedição":
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status IN ('Pronto', 'Disponível')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status_atual = df[df['id'] == id_l]['status'].values[0]

            if status_atual == 'Pronto':
                ps, gai = st.number_input("Peso Saída"), st.text_input("Gaiola")
                if st.button("✅ Disponibilizar p/ Motorista"):
                    executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=?, peso_saida=?, gaiola_num=? WHERE id=?", 
                                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ps, gai, id_l))
                    st.rerun()
            else:
                if st.button("⏪ ESTORNAR (Voltar para Acabamento)"):
                    executar_query("UPDATE lotes SET status='Pronto', fim_acabamento=NULL, peso_saida=NULL, gaiola_num=NULL WHERE id=?", (id_l,))
                    st.rerun()

    elif menu == "🚚 Motorista":
        df = consultar_db("SELECT * FROM lotes WHERE status='Disponível'")
        if not df.empty:
            for _, r in df.iterrows():
                if st.button(f"Confirmar Retirada Gaiola {r['gaiola_num']} - {r['hospital']}"):
                    executar_query("UPDATE lotes SET status='Finalizado', saida_motorista=?, motorista_nome=? WHERE id=?", 
                                   (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state['operador'], r['id']))
                    st.rerun()
        else: st.info("Sem gaiolas prontas.")

    elif menu == "⚙️ Gestão":
        with st.form("equipe"):
            n, s, f = st.text_input("Nome"), st.text_input("Senha"), st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
            if st.form_submit_button("Cadastrar"):
                executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", (n, s, f))
                st.success("Salvo!")

    elif menu == "📊 Relatórios":
        df = consultar_db("SELECT * FROM lotes")
        st.dataframe(df)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
        st.download_button("📥 Baixar Excel", buf.getvalue(), "relatorio.xlsx")
