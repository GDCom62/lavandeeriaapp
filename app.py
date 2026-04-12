import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- 1. CONFIGURAÇÕES E ESTADO (Sempre no topo) ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")

# Inicialização segura do estado
for key, val in {'logado': False, 'operador': "Visitante", 'funcao': "Nenhum", 'etapa_atual': "Início"}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# --- 2. BANCO DE DADOS (Otimizado com check_same_thread=False) ---
def get_connection():
    return sqlite3.connect('gestao_lavanderia.db', check_same_thread=False)

def init_db():
    with get_connection() as conn:
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
        
        # Admin padrão
        c.execute("SELECT * FROM operadores WHERE nome='admin'")
        if not c.fetchone():
            c.execute("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", ('admin', '1234', 'Administrador'))
        conn.commit()

def executar_query(sql, params=()):
    try:
        with get_connection() as conn:
            conn.execute(sql, params)
            conn.commit()
    except Exception as e:
        st.error(f"Erro no banco: {e}")

def consultar_db(sql, params=()):
    try:
        with get_connection() as conn:
            return pd.read_sql_query(sql, conn, params=params)
    except Exception as e:
        st.error(f"Erro na consulta: {e}")
        return pd.DataFrame()

# Executa criação das tabelas
init_db()

# --- 3. LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Gestão Lavanderia Hospitalar")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=? AND senha=?", (u, s))
        if not res.empty:
            st.session_state['logado'] = True
            st.session_state['operador'] = res.iloc[0]['nome']
            st.session_state['funcao'] = res.iloc[0]['funcao']
            st.rerun()
        else:
            st.error("Acesso negado.")
else:
    # --- 4. BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    
    if st.sidebar.button("🚨 PÂNICO", type="primary", use_container_width=True):
        executar_query("INSERT INTO alertas_panico (operador, etapa, data, resolvido) VALUES (?,?,?,0)", 
                       (st.session_state['operador'], st.session_state['etapa_atual'], datetime.now().strftime("%H:%M:%S")))
        st.sidebar.warning("Alerta Enviado!")

    menu_op = ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Motorista", "⚙️ Gestão", "📊 Relatórios"]
    if st.session_state['funcao'] == 'Motorista': menu_op = ["🚚 Motorista"]
    
    menu = st.sidebar.radio("Menu", menu_op)
    st.session_state['etapa_atual'] = menu

    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- 5. PAINEL GERAL (ALERTAS E RESET) ---
    if menu == "Painel Geral":
        st.title("📈 Monitoramento")
        
        # Alertas de Pânico
        panicos = consultar_db("SELECT * FROM alertas_panico WHERE resolvido=0")
        if not panicos.empty:
            for _, p in panicos.iterrows():
                st.error(f"🆘 PÂNICO: {p['operador']} em {p['etapa']} ({p['data']})")
                if st.button(f"Resolver Chamado {p['id']}"):
                    executar_query("UPDATE alertas_panico SET resolvido=1 WHERE id=?", (p['id'],))
                    st.rerun()

        st.divider()
        st.subheader("🛠️ Gestão de Lotes")
        lotes_ativos = consultar_db("SELECT id, hospital, status FROM lotes WHERE status != 'Finalizado'")
        if not lotes_ativos.empty:
            sel_r = st.selectbox("Ação rápida para lote:", lotes_ativos['id'].astype(str) + " - " + lotes_ativos['hospital'])
            id_r = int(sel_r.split(" - ")[0])
            c1, c2 = st.columns(2)
            if c1.button("🔄 Reiniciar (Voltar Início)"):
                executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL, fim_secagem=NULL, inicio_acabamento=NULL, fim_acabamento=NULL WHERE id=?", (id_r,))
                st.rerun()
            if c2.button("❌ Excluir Lote"):
                executar_query("DELETE FROM lotes WHERE id=?", (id_r,))
                st.rerun()
        
        st.write("### Fluxo Atual")
        st.dataframe(lotes_ativos, use_container_width=True)

    # --- 6. FLUXO OPERACIONAL (EXEMPLO DE LOGICA SEGURA) ---
    elif menu == "1. Lavagem":
        with st.form("f_lavagem", clear_on_submit=True):
            h = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            p = st.number_input("Peso (kg)", min_value=1.0)
            m = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
            if st.form_submit_button("Iniciar Lavagem"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, status, inicio_lavagem, operador_lavagem) VALUES (?,?,?,?,?,?)", 
                               (h, p, m, "Lavando", dt, st.session_state['operador']))
                st.success("Lote Iniciado!")

    elif menu == "2. Secagem":
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Lavando', 'Secando')")
        if not df.empty:
            sel = st.selectbox("Selecione Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - ")[0])
            row = df[df['id'] == id_l].iloc[0]
            
            if row['status'] == 'Lavando':
                if st.button("✅ Confirmar Entrada na Secadora"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Secando', fim_lavagem=?, inicio_secagem=?, operador_secagem=? WHERE id=?", 
                                   (dt, dt, st.session_state['operador'], id_l))
                    st.rerun()
            else:
                st.warning("Lote em Secagem")
                if st.button("⏪ Estornar p/ Lavagem"):
                    executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL WHERE id=?", (id_l,))
                    st.rerun()

    elif menu == "3. Acabamento":
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Selecione Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - ")[0])
            row = df[df['id'] == id_l].iloc[0]

            if row['status'] == 'Secando':
                it = ["Lençol", "Fronha", "Pijama"]
                qtds = {item: st.number_input(item, min_value=0) for item in it}
                if st.button("✅ Finalizar Contagem"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Pronto', fim_secagem=?, inicio_acabamento=?, operador_acabamento=? WHERE id=?", 
                                   (dt, dt, st.session_state['operador'], id_l))
                    for k, v in qtds.items(): 
                        if v > 0: executar_query("INSERT INTO contagem_itens VALUES (?,?,?)", (id_l, k, v))
                    st.rerun()
            else:
                if st.button("⏪ Estornar p/ Secagem"):
                    executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL, inicio_acabamento=NULL WHERE id=?", (id_l,))
                    executar_query("DELETE FROM contagem_itens WHERE lote_id=?", (id_l,))
                    st.rerun()

    elif menu == "📊 Relatórios":
        df = consultar_db("SELECT * FROM lotes")
        st.dataframe(df)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
            df.to_excel(wr, index=False)
        st.download_button("📥 Baixar Relatório Excel", buf.getvalue(), "relatorio_lavanderia.xlsx")
