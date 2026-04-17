import streamlit as st
import pandas as pd
from datetime import datetime
import io
from sqlalchemy import create_engine, text

# --- 1. CONFIGURAÇÃO DE ACESSO MÚLTIPLO (SQLAlchemy) ---
engine = create_engine("sqlite:///gestao_lavanderia.db", pool_size=20, max_overflow=30)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

# --- 2. INICIALIZAÇÃO DO BANCO ---
def init_db():
    executar_query('''CREATE TABLE IF NOT EXISTS operadores 
                      (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)''')
    executar_query('''CREATE TABLE IF NOT EXISTS lotes (
                      id INTEGER PRIMARY KEY AUTOINCREMENT, hospital TEXT, peso_entrada REAL, maquina TEXT, 
                      processo TEXT, status TEXT, inicio_lavagem TEXT, fim_lavagem TEXT, inicio_secagem TEXT, 
                      fim_secagem TEXT, inicio_acabamento TEXT, fim_acabamento TEXT, saida_motorista TEXT, 
                      motorista_nome TEXT, peso_saida REAL, gaiola_num TEXT, operador_lavagem TEXT, 
                      operador_secagem TEXT, operador_acabamento TEXT)''')
    executar_query('''CREATE TABLE IF NOT EXISTS contagem_itens 
                      (lote_id INTEGER, item TEXT, quantidade INTEGER)''')
    executar_query('''CREATE TABLE IF NOT EXISTS alertas_panico 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, operador TEXT, etapa TEXT, data TEXT, resolvido INTEGER)''')
    
    if consultar_db("SELECT * FROM operadores WHERE nome='admin'").empty:
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES ('admin', '1234', 'Administrador')")

# --- 3. INTERFACE E ESTADO ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")
init_db()

for key, val in {'logado': False, 'operador': "", 'funcao': "", 'etapa_atual': "Início"}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 4. LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Lavanderia Hospitalar - Gestão Têxtil")
    with st.container(border=True):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Acessar Sistema"):
            res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=:u AND senha=:s", {"u": u, "s": s})
            if not res.empty:
                st.session_state.update({"logado": True, "operador": res.iloc[0]['nome'], "funcao": res.iloc[0]['funcao']})
                st.rerun()
            else: st.error("Acesso Negado")
else:
    # --- BARRA LATERAL ---
    st.sidebar.header(f"👤 {st.session_state['operador']}")
    if st.sidebar.button("🚨 BOTÃO DE PÂNICO", type="primary", use_container_width=True):
        dt = datetime.now().strftime("%H:%M:%S")
        executar_query("INSERT INTO alertas_panico (operador, etapa, data, resolvido) VALUES (:op, :et, :dt, 0)",
                       {"op": st.session_state['operador'], "et": st.session_state['etapa_atual'], "dt": dt})
        st.sidebar.warning("Alerta de Pânico Enviado!")

    menu_op = ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Motorista", "⚙️ Equipe", "📊 Relatórios"]
    if st.session_state['funcao'] == 'Motorista': menu_op = ["🚚 Motorista"]
    
    menu = st.sidebar.radio("Navegação", menu_op)
    st.session_state['etapa_atual'] = menu

    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False})
        st.rerun()

    # --- 5. TELAS DO SISTEMA ---

    if menu == "Painel Geral":
        st.title("📈 Monitoramento e Alertas")
        panicos = consultar_db("SELECT * FROM alertas_panico WHERE resolvido=0")
        if not panicos.empty:
            for _, p in panicos.iterrows():
                st.error(f"🆘 PÂNICO: {p['operador']} em {p['etapa']} ({p['data']})")
                if st.button(f"Resolver Chamado {p['id']}"):
                    executar_query("UPDATE alertas_panico SET resolvido=1 WHERE id=:id", {"id": p['id']})
                    st.rerun()
            st.components.v1.html('<audio autoplay><source src="https://soundjay.com"></audio>', height=0)

        st.divider()
        st.subheader("🛠️ Gestão de Lotes Ativos")
        df_ativos = consultar_db("SELECT id, hospital, status, maquina, inicio_lavagem FROM lotes WHERE status != 'Finalizado'")
        if not df_ativos.empty:
            st.dataframe(df_ativos, use_container_width=True)
            sel_r = st.selectbox("Ação rápida (Abortar/Reiniciar):", df_ativos['id'].astype(str) + " - " + df_ativos['hospital'])
            id_r = int(sel_r.split(" - "))
            c1, c2 = st.columns(2)
            if c1.button("🔄 Reiniciar Lote (Início)"):
                executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL, fim_secagem=NULL, inicio_acabamento=NULL, fim_acabamento=NULL WHERE id=:id", {"id": id_r})
                st.rerun()
            if c2.button("❌ Excluir Permanentemente"):
                executar_query("DELETE FROM lotes WHERE id=:id", {"id": id_r})
                st.rerun()

    elif menu == "1. Lavagem":
        st.header("📥 Configurar Carga da Lavadora")
        maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
        
        if 'tambor' not in st.session_state: st.session_state.tambor = []
        
        with st.form("add_tambor", clear_on_submit=True):
            col_h, col_p = st.columns(2)
            h_nome = col_h.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            h_peso = col_p.number_input("Peso (kg)", min_value=1.0)
            col_t, col_pr = st.columns(2)
            h_tipo = col_t.radio("Tipo", ["Lavagem Comum", "Relave"], horizontal=True)
            h_proc = col_pr.selectbox("Processo", ["Leve", "Pesada", "Superpesada"])
            if st.form_submit_button("➕ Adicionar ao Tambor"):
                st.session_state.tambor.append({"h": h_nome, "p": h_peso, "t": h_tipo, "pr": h_proc})

        if st.session_state.tambor:
            st.table(pd.DataFrame(st.session_state.tambor))
            if st.button("🚀 INICIAR LAVAGEM GERAL"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state.tambor:
                    executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, :proc, 'Lavando', :dt, :op)",
                                   {"h": item['h'], "p": item['p'], "m": maq, "proc": f"{item['t']} | {item['pr']}", "dt": dt, "op": st.session_state['operador']})
                st.session_state.tambor = []
                st.success("Carga Iniciada!"); st.rerun()

    elif menu == "2. Secagem":
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Lavando', 'Secando')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status = df[df['id'] == id_l]['status'].values[0]
            if status == 'Lavando':
                if st.button("🔥 Iniciar Secagem"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Secando', fim_lavagem=:dt, inicio_secagem=:dt, operador_secagem=:op WHERE id=:id", {"dt": dt, "op": st.session_state['operador'], "id": id_l})
                    st.rerun()
            else:
                if st.button("⏪ Estornar p/ Lavagem"):
                    executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL WHERE id=:id", {"id": id_l})
                    st.rerun()

    elif menu == "3. Acabamento":
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status = df[df['id'] == id_l]['status'].values[0]
            if status == 'Secando':
                df_itens = pd.DataFrame([{"Item": i, "Qtd": 0} for i in ["Lençol", "Fronha", "Pijama", "Campo"]])
                edicao = st.data_editor(df_itens, hide_index=True, use_container_width=True)
                if st.button("✅ Salvar Contagem"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Pronto', fim_secagem=:dt, inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id", {"dt": dt, "op": st.session_state['operador'], "id": id_l})
                    for _, r in edicao.iterrows():
                        if r['Qtd'] > 0: executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": r['Item'], "q": r['Qtd']})
                    st.rerun()
            else:
                if st.button("⏪ Estornar Contagem"):
                    executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL, inicio_acabamento=NULL WHERE id=:id", {"id": id_l})
                    executar_query("DELETE FROM contagem_itens WHERE lote_id=:id", {"id": id_l}); st.rerun()

    elif menu == "📊 Relatórios":
        df = consultar_db("SELECT * FROM lotes")
        st.dataframe(df)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
        st.download_button("📥 Baixar Excel", buf.getvalue(), "relatorio.xlsx")
