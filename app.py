import streamlit as st
import pandas as pd
from datetime import datetime
import io
from sqlalchemy import create_engine, text
from fpdf import FPDF

# --- 1. DESIGN E CONFIGURAÇÃO ---
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
    if consultar_db("SELECT * FROM operadores WHERE nome='admin'").empty:
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES ('admin', '1234', 'Administrador')")

init_db()

# --- 3. LOGIN E ESTADO ---
for key, val in {'logado': False, 'operador': "", 'funcao': "", 'tambor': []}.items():
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state['logado']:
    st.title("🏥 Gestão Lavanderia Hospitalar")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=:u AND senha=:s", {"u": u, "s": s})
            if not res.empty:
                st.session_state.update({"logado": True, "operador": res.iloc[0]['nome'], "funcao": res.iloc[0]['funcao']})
                st.rerun()
            else: st.error("Acesso Negado")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    menu = st.sidebar.radio("Navegação", ["Painel Geral", "1. Lavagem", "2. Rampa (Saída Lavagem)", "3. Secagem", "4. Acabamento", "5. Expedição", "📊 Relatórios"])
    if st.sidebar.button("Sair"): st.session_state['logado'] = False; st.rerun()

    # --- TELAS ---
    
    # 1. LAVAGEM (Entrada por peso e tipo)
    if menu == "1. Lavagem":
        st.header("📥 Entrada na Lavadora")
        maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
        
        with st.form("carga_tambor", clear_on_submit=True):
            hosp = st.selectbox("Hospital/Cliente", ["Hospital A", "Hospital B", "Hospital C"])
            peso = st.number_input("Peso (kg)", min_value=1.0)
            tipo = st.radio("Classificação", ["Leve", "Pesada", "Relave"], horizontal=True)
            if st.form_submit_button("➕ Adicionar à Máquina"):
                st.session_state.tambor.append({"h": hosp, "p": peso, "t": tipo})
        
        if st.session_state.tambor:
            st.write("### Carga Atual:")
            st.table(pd.DataFrame(st.session_state.tambor))
            if st.button("🚀 Iniciar Lavagem Geral", type="primary"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for item in st.session_state.tambor:
                    executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, :pr, 'Lavando', :dt, :op)",
                                   {"h": item['h'], "p": item['p'], "m": maq, "pr": item['t'], "dt": dt, "op": st.session_state['operador']})
                st.session_state.tambor = []; st.success("Lavagem Iniciada!"); st.rerun()

    # 2. RAMPA (Onde a lavagem termina e aguarda transporte para secagem)
    elif menu == "2. Rampa (Saída Lavagem)":
        st.header("⏳ Rampa de Saída da Lavadora")
        st.info("O tempo aqui registra o fim da lavagem e o início da espera para secagem.")
        df = consultar_db("SELECT id, hospital, maquina, processo FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Lote que saiu da máquina", df['id'].astype(str) + " - " + df['hospital'])
            if sel and st.button("✅ Confirmar Saída para Rampa", type="primary"):
                id_l = int(str(sel).split(" - ")[0])
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Na Rampa', fim_lavagem=:dt WHERE id=:id", {"dt": dt, "id": id_l})
                st.rerun()
        else: st.info("Nenhuma máquina finalizando lavagem.")

    # 3. SECAGEM (Início do transporte da rampa para secadora)
    elif menu == "3. Secagem":
        st.header("🔥 Entrada na Secagem")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Na Rampa'")
        if not df.empty:
            sel = st.selectbox("Lote na Rampa", df['id'].astype(str) + " - " + df['hospital'])
            if sel and st.button("🚀 Iniciar Secagem", type="primary"):
                id_l = int(str(sel).split(" - ")[0])
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                executar_query("UPDATE lotes SET status='Secando', inicio_secagem=:dt, operador_secagem=:op WHERE id=:id", 
                               {"dt": dt, "op": st.session_state['operador'], "id": id_l})
                st.rerun()
        else: st.info("Nenhum lote na rampa aguardando secagem.")

    # 4. ACABAMENTO (Dobra ou Passadeira)
    elif menu == "4. Acabamento":
        st.header("🧺 Dobra e Passadeira")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote para Acabamento", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(str(sel).split(" - ")[0])
            status = df[df['id'] == id_l]['status'].values[0]
            
            if status == 'Secando':
                destino = st.radio("Destino:", ["Dobra", "Passadeira"], horizontal=True)
                ed = st.data_editor(pd.DataFrame([{"Item": i, "Qtd": 0} for i in ["Lençol", "Fronha", "Pijama", "Campo"]]), hide_index=True)
                if st.button("✅ Finalizar Processo", type="primary"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Pronto', fim_secagem=:dt, inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id", 
                                   {"dt": dt, "op": st.session_state['operador'], "id": id_l})
                    for _, r in ed.iterrows():
                        if r['Qtd'] > 0: executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": r['Item'], "q": r['Qtd']})
                    st.success("Registrado!"); st.rerun()
            else:
                if st.button("⏪ Estornar Contagem"):
                    executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL, inicio_acabamento=NULL WHERE id=:id", {"id": id_l})
                    executar_query("DELETE FROM contagem_itens WHERE lote_id=:id", {"id": id_l}); st.rerun()

    # RELATÓRIOS (Com cálculo de produtividade)
    elif menu == "📊 Relatórios":
        st.title("📊 Desempenho e Produtividade")
        df_f = consultar_db("SELECT * FROM lotes")
        st.dataframe(df_f)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_f.to_excel(wr, index=False)
        st.download_button("📥 Baixar Excel Completo", buf.getvalue(), "relatorio_lavanderia.xlsx")
