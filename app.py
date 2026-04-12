import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURAÇÕES E ESTADO ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")

for key, val in {'logado': False, 'operador': "Visitante", 'funcao': "Nenhum", 'etapa_atual': "Nenhuma"}.items():
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
    # TABELA DE PÂNICO INTELIGENTE
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
    # --- 4. BARRA LATERAL COM PÂNICO INTELIGENTE ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    
    st.sidebar.divider()
    # O Botão de Pânico agora envia a etapa onde o operador está navegando
    if st.sidebar.button("🚨 BOTÃO DE PÂNICO", use_container_width=True, type="primary"):
        dt = datetime.now().strftime("%H:%M:%S")
        etapa_msg = st.session_state.get('etapa_atual', 'Navegação Geral')
        executar_query("INSERT INTO alertas_panico (operador, etapa, data, resolvido) VALUES (?,?,?,0)", 
                       (st.session_state['operador'], etapa_msg, dt))
        st.sidebar.warning("Alerta enviado à Gerência!")

    menu_op = ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Motorista", "⚙️ Gestão", "📊 Relatórios"]
    if st.session_state['funcao'] == 'Motorista': menu_op = ["🚚 Motorista"]
    
    menu = st.sidebar.radio("Menu", menu_op)
    st.session_state['etapa_atual'] = menu # Atualiza a etapa para o botão de pânico

    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False, "operador": "Visitante"})
        st.rerun()

    # --- 5. PAINEL GERAL (ALERTAS SONOROS E VISUAIS) ---
    if menu == "Painel Geral":
        st.title("📈 Monitoramento de Produção")
        
        # Exibir Pânicos Ativos
        panicos = consultar_db("SELECT * FROM alertas_panico WHERE resolvido=0")
        houve_som = False
        if not panicos.empty:
            houve_som = True
            for _, p in panicos.iterrows():
                st.error(f"🆘 **PÂNICO ATIVADO:** Operador **{p['operador']}** na etapa **{p['etapa']}** às {p['data']}!")
                if st.button(f"Resolver Chamado {p['id']}", key=f"res_{p['id']}"):
                    executar_query("UPDATE alertas_panico SET resolvido=1 WHERE id=?", (p['id'],))
                    st.rerun()

        # Monitor de Atrasos
        df_l = consultar_db("SELECT id, hospital, status, inicio_lavagem FROM lotes WHERE status NOT IN ('Finalizado', 'Em Transito')")
        if not df_l.empty:
            agora = datetime.now()
            for _, row in df_l.iterrows():
                try:
                    atraso = (agora - pd.to_datetime(row['inicio_lavagem'])).total_seconds() / 60
                    if atraso > 120:
                        st.warning(f"⏳ **ATRASO CRÍTICO:** Lote #{row['id']} ({row['hospital']}) há {int(atraso)} min!")
                        houve_som = True
                except: continue
            st.write("### Lotes em Andamento")
            st.dataframe(df_l, use_container_width=True)
        
        if houve_som:
            st.components.v1.html('<audio autoplay loop><source src="https://soundjay.com"></audio>', height=0)

    # --- 6. FLUXO OPERACIONAL ---
    elif menu == "1. Lavagem":
        st.header("Entrada de Roupas")
        with st.form("f1"):
            h = st.selectbox("Hospital", ["Hospital Central", "Hospital Norte", "Unimed"])
            p = st.number_input("Peso Bruto (kg)", min_value=1.0)
            m = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
            if st.form_submit_button("Iniciar Lavagem"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, status, inicio_lavagem, operador_lavagem) VALUES (?,?,?,?,?,?)", (h, p, m, "Lavando", dt, st.session_state['operador']))
                st.success("Lote em lavagem!")

    elif menu == "2. Secagem":
        st.header("Processo de Secagem")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Lote vindo da Lavagem", df['id'].astype(str) + " - " + df['hospital'])
            if st.button("Confirmar Entrada na Secadora"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Secando', fim_lavagem=?, inicio_secagem=?, operador_secagem=? WHERE id=?", (dt, dt, st.session_state['operador'], int(sel.split(" - "))))
                st.rerun()
        else: st.info("Nenhum lote pronto para secagem.")

    elif menu == "3. Acabamento":
        st.header("Contagem e Dobra")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Secando'")
        if not df.empty:
            sel = st.selectbox("Lote vindo da Secagem", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            it = ["Lençol", "Fronha", "Pijama", "Campo Cirúrgico", "Colcha"]
            cols = st.columns(len(it))
            qtds = {item: cols[i].number_input(item, min_value=0) for i, item in enumerate(it)}
            if st.button("Finalizar Acabamento"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Pronto', fim_secagem=?, inicio_acabamento=?, operador_acabamento=? WHERE id=?", (dt, dt, st.session_state['operador'], id_l))
                for k, v in qtds.items(): 
                    if v > 0: executar_query("INSERT INTO contagem_itens VALUES (?,?,?)", (id_l, k, v))
                st.success("Contagem salva!")

    elif menu == "4. Expedição":
        st.header("Pesagem de Saída e Gaiolas")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Pronto'")
        if not df.empty:
            sel = st.selectbox("Lote Pronto", df['id'].astype(str) + " - " + df['hospital'])
            ps = st.number_input("Peso Saída (kg)")
            gai = st.text_input("Nº da Gaiola")
            if st.button("Disponibilizar para Motorista"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=?, peso_saida=?, gaiola_num=? WHERE id=?", (dt, ps, gai, int(sel.split(" - "))))
                st.rerun()

    elif menu == "🚚 Motorista":
        st.header("Retirada de Carga")
        df = consultar_db("SELECT * FROM lotes WHERE status='Disponível'")
        if not df.empty:
            for _, r in df.iterrows():
                with st.expander(f"Gaiola {r['gaiola_num']} - {r['hospital']}"):
                    st.write(f"Peso Saída: {r['peso_saida']}kg")
                    if st.button(f"Confirmar Retirada #{r['id']}", key=f"ret_{r['id']}"):
                        dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        executar_query("UPDATE lotes SET status='Finalizado', saida_motorista=?, motorista_nome=? WHERE id=?", (dt, st.session_state['operador'], r['id']))
                        st.rerun()
        else: st.info("Aguardando gaiolas prontas.")

    elif menu == "⚙️ Gestão":
        st.header("Controle de Usuários")
        with st.form("equipe"):
            n, s, f = st.text_input("Nome"), st.text_input("Senha"), st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
            if st.form_submit_button("Cadastrar"):
                try:
                    executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", (n, s, f))
                    st.success(f"Usuário {n} cadastrado!")
                except: st.error("Erro: Nome de usuário já existe.")

    elif menu == "📊 Relatórios":
        st.header("Histórico Completo")
        df = consultar_db("SELECT * FROM lotes")
        st.dataframe(df)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
        st.download_button("📥 Baixar Relatório Excel", buf.getvalue(), "faturamento_lavanderia.xlsx")
