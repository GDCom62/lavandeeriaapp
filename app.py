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

# --- 3. ESTADO DA SESSÃO ---
for key, val in {'logado': False, 'operador': "", 'funcao': "", 'tambor': []}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 4. FUNÇÃO PDF ---
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
    for _, item in itens.iterrows():
        pdf.cell(190, 8, f"- {item['item']}: {item['quantidade']} un", 0, 1)
    return bytes(pdf.output())

# --- 5. LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Gestão Lavanderia Hospitalar")
    with st.form("login"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=:u AND senha=:s", {"u": u, "s": s})
            if not res.empty:
                st.session_state.update({"logado": True, "operador": res.iloc[0]['nome'], "funcao": res.iloc[0]['funcao']})
                st.rerun()
            else: st.error("Acesso Negado")
else:
    # --- BARRA LATERAL ---
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    menu = st.sidebar.radio("Navegação", ["Painel Geral", "1. Lavagem", "2. Rampa", "3. Secagem", "4. Acabamento", "5. Expedição", "📊 Relatórios", "⚙️ Gestão de Equipe"])
    if st.sidebar.button("Sair"): st.session_state.update({"logado": False}); st.rerun()

    # --- TELAS OPERACIONAIS (RESUMIDAS) ---
    if menu == "1. Lavagem":
        st.header("📥 Carregar Lavadora")
        maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
        with st.form("add_tambor", clear_on_submit=True):
            h_n = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            h_p = st.number_input("Peso (kg)", min_value=1.0)
            h_t = st.radio("Tipo", ["Leve", "Pesada", "Relave"], horizontal=True)
            if st.form_submit_button("➕ Adicionar ao Tambor"):
                st.session_state.tambor.append({"h": h_n, "p": h_p, "t": h_t})
        if st.session_state.tambor:
            st.table(pd.DataFrame(st.session_state.tambor))
            if st.button("🚀 INICIAR LAVAGEM"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                for i in st.session_state.tambor:
                    executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, :pr, 'Lavando', :dt, :op)",
                                   {"h": i['h'], "p": i['p'], "m": maq, "pr": i['t'], "dt": dt, "op": st.session_state['operador']})
                st.session_state.tambor = []; st.rerun()

    elif menu == "2. Rampa":
        st.header("⏳ Rampa")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Lote saindo:", df['id'].astype(str) + " - " + df['hospital'])
            if st.button("✅ Enviar para Rampa"):
                executar_query("UPDATE lotes SET status='Na Rampa', fim_lavagem=:dt WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "id": int(sel.split(" - ")[0])}); st.rerun()

    elif menu == "3. Secagem":
        st.header("🔥 Secagem")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Na Rampa'")
        if not df.empty:
            sel = st.selectbox("Lote na Rampa:", df['id'].astype(str) + " - " + df['hospital'])
            if st.button("🚀 Iniciar Secagem"):
                executar_query("UPDATE lotes SET status='Secando', inicio_secagem=:dt, operador_secagem=:op WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "op": st.session_state['operador'], "id": int(sel.split(" - ")[0])}); st.rerun()

    elif menu == "4. Acabamento":
        st.header("🧺 Dobra e Passagem")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote:", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - ")[0])
            if df[df['id'] == id_l].iloc[0]['status'] == 'Secando':
                lista = ["Lencol", "Fronha", "Oleado", "Colcha", "Edredon", "Calca", "Camisa", "Campo", "Tracado", "Camisola Adulto", "Camisola Infantil", "Cobertor", "Capote", "Toalha de Banho", "Toalha de Rosto", "Piso", "Cortina", "Outros"]
                ed = st.data_editor(pd.DataFrame([{"Item": i, "Quantidade": 0} for i in lista]), use_container_width=True, hide_index=True)
                if st.button("✅ Finalizar"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Pronto', fim_secagem=:dt, inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id", {"dt": dt, "op": st.session_state['operador'], "id": id_l})
                    for _, r in ed.iterrows():
                        if r['Quantidade'] > 0: executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": r['Item'], "q": r['Quantidade']})
                    st.rerun()

    # --- 📊 RELATÓRIO DE PRODUTIVIDADE ---
    elif menu == "📊 Relatórios":
        st.title("📊 Relatório de Produtividade")
        df = consultar_db("SELECT * FROM lotes")
        
        if not df.empty:
            # Converter colunas de tempo
            for col in ['inicio_lavagem', 'fim_lavagem', 'inicio_secagem', 'fim_secagem', 'inicio_acabamento', 'fim_acabamento']:
                df[col] = pd.to_datetime(df[col], errors='coerce')

            # 1. Produtividade por Empresa (Hospital)
            st.subheader("🏢 Desempenho por Empresa")
            # Peso total e tempo médio de ciclo (entrada até acabamento)
            df['ciclo_total'] = (df['fim_acabamento'] - df['inicio_lavagem']).dt.total_seconds() / 3600
            prod_hosp = df.groupby('hospital').agg({'peso_entrada': 'sum', 'id': 'count', 'ciclo_total': 'mean'}).rename(columns={'id': 'Qtd Lotes', 'peso_entrada': 'Total Kg', 'ciclo_total': 'Média Horas/Ciclo'})
            st.dataframe(prod_hosp.style.format("{:.2f}"), use_container_width=True)

            # 2. Produtividade por Colaborador
            st.subheader("👥 Produtividade por Colaborador")
            # Unificar operadores de todas as etapas
            ops = pd.concat([
                df[['operador_lavagem', 'peso_entrada']].rename(columns={'operador_lavagem': 'Colaborador'}),
                df[['operador_secagem', 'peso_entrada']].rename(columns={'operador_secagem': 'Colaborador'}),
                df[['operador_acabamento', 'peso_entrada']].rename(columns={'operador_acabamento': 'Colaborador'})
            ])
            prod_colab = ops.groupby('Colaborador').agg({'peso_entrada': 'sum', 'Colaborador': 'count'}).rename(columns={'peso_entrada': 'Kg Processados', 'Colaborador': 'Etapas Realizadas'})
            st.bar_chart(prod_colab['Kg Processados'])
            st.table(prod_colab)

            # Download
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr:
                df.to_excel(wr, index=False, sheet_name='Geral')
                prod_hosp.to_excel(wr, sheet_name='Por_Empresa')
                prod_colab.to_excel(wr, sheet_name='Por_Colaborador')
            st.download_button("📥 Baixar Relatório de Produtividade", buf.getvalue(), "produtividade_lavanderia.xlsx")
        else: st.info("Sem dados.")

    elif menu == "⚙️ Gestão de Equipe":
        st.header("⚙️ Cadastro de Equipe")
        with st.form("cad"):
            n, s, f = st.text_input("Nome"), st.text_input("Senha"), st.selectbox("Função", ["Operador", "Administrador"])
            if st.form_submit_button("Salvar"):
                executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (:n, :s, :f)", {"n": n, "s": s, "f": f}); st.rerun()
