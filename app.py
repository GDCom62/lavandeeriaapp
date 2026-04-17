import streamlit as st
import pandas as pd
from datetime import datetime
import io
from sqlalchemy import create_engine, text
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO DE ACESSO E DESIGN ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")

st.markdown("""
    <style>
    .stButton>button, .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input, .stDataEditor {
        border-radius: 12px !important;
    }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e0e0e0; }
    [data-testid="stForm"], div[data-testid="stExpander"], .stMetric {
        border-radius: 15px !important; border: 1px solid #eef2f6 !important;
        background-color: #ffffff; padding: 20px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #1E3A8A; font-family: 'Segoe UI', sans-serif; }
    .stButton>button:hover { transform: translateY(-2px); transition: 0.2s; border-color: #1E3A8A !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS ---
engine = create_engine("sqlite:///gestao_lavanderia.db", pool_size=20, max_overflow=30)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

def init_db():
    executar_query('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)')
    executar_query('''CREATE TABLE IF NOT EXISTS lotes (
                      id INTEGER PRIMARY KEY AUTOINCREMENT, hospital TEXT, peso_entrada REAL, maquina TEXT, 
                      processo TEXT, status TEXT, inicio_lavagem TEXT, fim_lavagem TEXT, inicio_secagem TEXT, 
                      fim_secagem TEXT, inicio_acabamento TEXT, fim_acabamento TEXT, saida_motorista TEXT, 
                      motorista_nome TEXT, peso_saida REAL, gaiola_num TEXT, operador_lavagem TEXT, 
                      operador_secagem TEXT, operador_acabamento TEXT)''')
    executar_query('CREATE TABLE IF NOT EXISTS contagem_itens (lote_id INTEGER, item TEXT, quantidade INTEGER)')
    executar_query('CREATE TABLE IF NOT EXISTS alertas_panico (id INTEGER PRIMARY KEY AUTOINCREMENT, operador TEXT, etapa TEXT, data TEXT, resolvido INTEGER)')
    if consultar_db("SELECT * FROM operadores WHERE nome='admin'").empty:
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES ('admin', '1234', 'Administrador')")

init_db()

# --- 3. ESTADO DA SESSÃO ---
for key, val in {'logado': False, 'operador': "", 'funcao': "", 'etapa': "Início", 'tambor': []}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 4. FUNÇÕES AUXILIARES ---
def gerar_pdf_etiqueta(lote, itens):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 18)
    pdf.cell(190, 15, "ETIQUETA DE GAIOLA", 1, 1, "C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(95, 10, f"Hospital: {lote['hospital']}", 0, 0)
    pdf.cell(95, 10, f"Gaiola N°: {lote['gaiola_num']}", 0, 1)
    pdf.cell(95, 10, f"Peso Final: {lote['peso_saida']} kg", 0, 0)
    pdf.cell(95, 10, f"Data: {datetime.now().strftime('%d/%m/%Y')}", 0, 1)
    pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.cell(190, 10, "CONTEÚDO:", 0, 1)
    pdf.set_font("Arial", "", 12)
    for _, item in itens.iterrows():
        pdf.cell(190, 8, f"- {item['item']}: {item['quantidade']} un", 0, 1)
    return pdf.output()

# --- 5. LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Gestão de Lavanderia Hospitalar")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar"):
            res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=:u AND senha=:s", {"u": u, "s": s})
            if not res.empty:
                st.session_state.update({"logado": True, "operador": res.iloc[0]['nome'], "funcao": res.iloc[0]['funcao']})
                st.rerun()
            else: st.error("Acesso Negado")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    if st.sidebar.button("🚨 PÂNICO", type="primary", use_container_width=True):
        executar_query("INSERT INTO alertas_panico (operador, etapa, data, resolvido) VALUES (:op, :et, :dt, 0)",
                       {"op": st.session_state['operador'], "et": st.session_state['etapa'], "dt": datetime.now().strftime("%H:%M")})
        st.sidebar.warning("Alerta Enviado!")

    menu = st.sidebar.radio("Navegação", ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Motorista", "📊 Relatórios"])
    st.session_state['etapa'] = menu
    if st.sidebar.button("Sair"): st.session_state['logado'] = False; st.rerun()

    # --- 6. TELAS ---
    if menu == "Painel Geral":
        st.title("📈 Painel de Controle")
        panicos = consultar_db("SELECT * FROM alertas_panico WHERE resolvido=0")
        if not panicos.empty:
            for _, p in panicos.iterrows():
                st.error(f"🆘 PÂNICO: {p['operador']} em {p['etapa']} ({p['data']})")
                if st.button(f"Limpar Alerta {p['id']}", key=f"pan_{p['id']}"):
                    executar_query("UPDATE alertas_panico SET resolvido=1 WHERE id=:id", {"id": p['id']}); st.rerun()
        
        df_l = consultar_db("SELECT id, hospital, status, maquina, inicio_lavagem FROM lotes WHERE status != 'Finalizado'")
        if not df_l.empty:
            st.dataframe(df_l, use_container_width=True)
            sel = st.selectbox("Ação rápida:", df_l['id'].astype(str) + " - " + df_l['hospital'], key="sel_painel")
            if sel:
                id_r = int(str(sel).split(" - ")[0])
                c1, c2 = st.columns(2)
                if c1.button("🔄 Reiniciar Lote"):
                    executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL, fim_secagem=NULL, inicio_acabamento=NULL, fim_acabamento=NULL WHERE id=:id", {"id": id_r}); st.rerun()
                if c2.button("❌ Excluir Lote"):
                    executar_query("DELETE FROM lotes WHERE id=:id", {"id": id_r}); st.rerun()

    elif menu == "1. Lavagem":
        st.header("📥 Carregar Tambor")
        maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
        with st.form("add_tambor", clear_on_submit=True):
            h_n = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            h_p = st.number_input("Peso (kg)", min_value=1.0)
            col_t, col_pr = st.columns(2)
            h_t = col_t.radio("Tipo", ["Lavagem Comum", "Relave"], horizontal=True)
            h_proc = col_pr.selectbox("Processo", ["Leve", "Pesada", "Superpesada"])
            if st.form_submit_button("➕ Adicionar"):
                st.session_state.tambor.append({"h": h_n, "p": h_p, "t": h_t, "pr": h_proc})

        if st.session_state.tambor:
            st.table(pd.DataFrame(st.session_state.tambor))
            if st.button("🚀 INICIAR LAVAGEM"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                for i in st.session_state.tambor:
                    executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, :pr, 'Lavando', :dt, :op)",
                                   {"h": i['h'], "p": i['p'], "m": maq, "pr": f"{i['t']} | {i['pr']}", "dt": dt, "op": st.session_state['operador']})
                st.session_state.tambor = []; st.success("Carga Iniciada!"); st.rerun()

    elif menu == "2. Secagem":
        st.header("🔥 Secagem")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Lavando', 'Secando')")
        if not df.empty:
            sel = st.selectbox("Selecione o Lote", df['id'].astype(str) + " - " + df['hospital'], key="sel_secagem")
            if sel:
                id_l = int(str(sel).split(" - ")[0])
                status = df[df['id'] == id_l]['status'].values[0]
                if status == 'Lavando':
                    if st.button("✅ Iniciar Secagem"):
                        dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                        executar_query("UPDATE lotes SET status='Secando', fim_lavagem=:dt, inicio_secagem=:dt, operador_secagem=:op WHERE id=:id", {"dt": dt, "op": st.session_state['operador'], "id": id_l}); st.rerun()
                else:
                    if st.button("⏪ Estornar p/ Lavagem"):
                        executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL WHERE id=:id", {"id": id_l}); st.rerun()

    elif menu == "3. Acabamento":
        st.header("🧺 Dobra e Passagem")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'], key="sel_acab")
            if sel:
                id_l = int(str(sel).split(" - ")[0])
                status = df[df['id'] == id_l]['status'].values[0]
                if status == 'Secando':
                    ed = st.data_editor(pd.DataFrame([{"Item": i, "Qtd": 0} for i in ["Lençol", "Fronha", "Pijama", "Campo"]]), hide_index=True, key=f"ed_{id_l}")
                    if st.button("✅ Salvar Contagem"):
                        executar_query("UPDATE lotes SET status='Pronto', fim_secagem=:dt, inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "op": st.session_state['operador'], "id": id_l})
                        for _, r in ed.iterrows():
                            if r['Qtd'] > 0: executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": r['Item'], "q": r['Qtd']})
                        st.rerun()
                else:
                    if st.button("⏪ Estornar p/ Secagem"):
                        executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL, inicio_acabamento=NULL WHERE id=:id", {"id": id_l}); st.rerun()

    elif menu == "4. Expedição":
        st.header("📦 Expedição")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Pronto', 'Disponível')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'], key="sel_exp")
            if sel:
                id_l = int(str(sel).split(" - ")[0])
                status = df[df['id'] == id_l]['status'].values[0]
                if status == 'Pronto':
                    ps, gai = st.number_input("Peso Saída", min_value=0.1), st.text_input("Gaiola N°")
                    if st.button("✅ Liberar p/ Motorista"):
                        executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=:dt, peso_saida=:ps, gaiola_num=:g WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "ps": ps, "g": gai, "id": id_l}); st.rerun()
                else:
                    l_data = consultar_db("SELECT * FROM lotes WHERE id=:id", {"id": id_l}).iloc[0]
                    itens = consultar_db("SELECT item, quantidade FROM contagem_itens WHERE lote_id=:id", {"id": id_l})
                    st.download_button("📥 Baixar Etiqueta PDF", gerar_pdf_etiqueta(l_data, itens), f"etiqueta_{id_l}.pdf")
                    if st.button("⏪ Estornar"):
                        executar_query("UPDATE lotes SET status='Pronto', peso_saida=NULL, gaiola_num=NULL WHERE id=:id", {"id": id_l}); st.rerun()

    elif menu == "🚚 Motorista":
        st.header("🚚 Retirada de Carga")
        df = consultar_db("SELECT * FROM lotes WHERE status='Disponível'")
        if not df.empty:
            for _, r in df.iterrows():
                if st.button(f"Confirmar Retirada: Gaiola {r['gaiola_num']} ({r['hospital']})", key=f"mot_{r['id']}"):
                    executar_query("UPDATE lotes SET status='Finalizado', saida_motorista=:dt, motorista_nome=:m WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "m": st.session_state['operador'], "id": r['id']}); st.rerun()

    elif menu == "📊 Relatórios":
        st.title("📊 Histórico Geral")
        df_f = consultar_db("SELECT * FROM lotes")
        st.dataframe(df_f)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_f.to_excel(wr, index=False)
        st.download_button("📥 Exportar para Excel", buf.getvalue(), "relatorio_lavanderia.xlsx")
