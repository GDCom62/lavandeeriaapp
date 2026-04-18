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

# --- 2. BANCO DE DADOS (SQLAlchemy) ---
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
for key, val in {'logado': False, 'operador': "", 'funcao': "", 'tambor': [], 'etapa_atual': "Início"}.items():
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
    pdf.cell(95, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
    pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.cell(190, 10, "CONTEÚDO:", 0, 1)
    pdf.set_font("Arial", "", 12)
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
    st.sidebar.info(f"Função: {st.session_state['funcao']}")
    
    opcoes_menu = ["Painel Geral", "1. Lavagem", "2. Rampa", "3. Secagem", "4. Acabamento", "5. Expedição", "📊 Relatórios"]
    if st.session_state['funcao'] == "Administrador":
        opcoes_menu.append("⚙️ Gestão de Equipe")
    
    menu = st.sidebar.radio("Navegação", opcoes_menu)
    st.session_state['etapa_atual'] = menu
    
    if st.sidebar.button("Sair"): 
        st.session_state.update({"logado": False, "operador": "", "funcao": ""})
        st.rerun()

    # --- TELAS ---
    if menu == "Painel Geral":
        st.title("📈 Monitoramento Ativo")
        df_l = consultar_db("SELECT id, hospital, status, maquina, inicio_lavagem FROM lotes WHERE status != 'Finalizado'")
        st.dataframe(df_l, use_container_width=True)

    elif menu == "1. Lavagem":
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
                dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                for i in st.session_state.tambor:
                    executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, :pr, 'Lavando', :dt, :op)",
                                   {"h": i['h'], "p": i['p'], "m": maq, "pr": i['t'], "dt": dt, "op": st.session_state['operador']})
                st.session_state.tambor = []; st.success("Carga Iniciada!"); st.rerun()

    elif menu == "2. Rampa":
        st.header("⏳ Rampa (Saída Lavadora)")
        df = consultar_db("SELECT id, hospital, maquina FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Lote saindo da máquina:", df['id'].astype(str) + " - " + df['hospital'])
            if sel and st.button("✅ Enviar para Rampa"):
                id_l = int(str(sel).split(" - ")[0])
                executar_query("UPDATE lotes SET status='Na Rampa', fim_lavagem=:dt WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "id": id_l}); st.rerun()

    elif menu == "3. Secagem":
        st.header("🔥 Secagem")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Na Rampa'")
        if not df.empty:
            sel = st.selectbox("Lote na Rampa:", df['id'].astype(str) + " - " + df['hospital'])
            if sel and st.button("🚀 Iniciar Secagem"):
                id_l = int(str(sel).split(" - ")[0])
                executar_query("UPDATE lotes SET status='Secando', inicio_secagem=:dt, operador_secagem=:op WHERE id=:id", 
                               {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "op": st.session_state['operador'], "id": id_l}); st.rerun()

    elif menu == "4. Acabamento":
        st.header("🧺 Dobra e Passagem")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Selecione o Lote:", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(str(sel).split(" - ")[0])
            status = df[df['id'] == id_l].iloc[0]['status']

            if status == 'Secando':
                lista_itens = ["Lencol", "Fronha", "Oleado", "Colcha", "Edredon", "Calca", "Camisa", "Campo", "Tracado", "Camisola Adulto", "Camisola Infantil", "Cobertor", "Capote", "Toalha de Banho", "Toalha de Rosto", "Piso", "Cortina", "Outros"]
                itens_df = pd.DataFrame([{"Item": i, "Quantidade": 0} for i in lista_itens])
                edicao = st.data_editor(itens_df, use_container_width=True, hide_index=True)

                if st.button("✅ Salvar e Finalizar"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    executar_query("UPDATE lotes SET status='Pronto', fim_secagem=:dt, inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id", {"dt": dt, "op": st.session_state['operador'], "id": id_l})
                    for _, row in edicao.iterrows():
                        if row['Quantidade'] > 0:
                            executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": row['Item'], "q": row['Quantidade']})
                    st.success("Contagem salva!"); st.rerun()
            else:
                if st.button("⏪ Estornar p/ Secagem"):
                    executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL WHERE id=:id", {"id": id_l})
                    executar_query("DELETE FROM contagem_itens WHERE lote_id=:id", {"id": id_l}); st.rerun()

    elif menu == "5. Expedição":
        st.header("📦 Expedição")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Pronto', 'Disponível')")
        if not df.empty:
            sel = st.selectbox("Lote:", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(str(sel).split(" - ")[0])
            lote_row = df[df['id'] == id_l].iloc[0]

            if lote_row['status'] == 'Pronto':
                ps, gai = st.number_input("Peso Saída", min_value=0.1), st.text_input("Gaiola N°")
                if st.button("✅ Liberar"):
                    executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=:dt, peso_saida=:ps, gaiola_num=:g WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "ps": ps, "g": gai, "id": id_l}); st.rerun()
            else:
                l_data = consultar_db("SELECT * FROM lotes WHERE id=:id", {"id": id_l}).iloc[0]
                itens = consultar_db("SELECT item, quantidade FROM contagem_itens WHERE lote_id=:id", {"id": id_l})
                st.download_button("📥 Baixar Etiqueta PDF", gerar_pdf_etiqueta(l_data, itens), f"etiqueta_{id_l}.pdf", mime="application/pdf")

    elif menu == "📊 Relatórios":
        st.title("📊 Relatórios Gerenciais")
        df_f = consultar_db("SELECT * FROM lotes")
        st.dataframe(df_f)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df_f.to_excel(wr, index=False)
        st.download_button("📥 Baixar Excel", buf.getvalue(), "relatorio.xlsx")

    elif menu == "⚙️ Gestão de Equipe":
        st.header("⚙️ Gerenciamento de Usuários")
        with st.form("cad_usuario"):
            novo_nome = st.text_input("Nome do Usuário")
            nova_senha = st.text_input("Senha", type="password")
            nova_funcao = st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
            if st.form_submit_button("Cadastrar Colaborador"):
                try:
                    executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (:n, :s, :f)", {"n": novo_nome, "s": nova_senha, "f": nova_funcao})
                    st.success(f"Usuário {novo_nome} cadastrado com sucesso!")
                except:
                    st.error("Erro: Nome de usuário já existe ou dados inválidos.")
        
        st.subheader("Colaboradores Ativos")
        usuarios = consultar_db("SELECT nome, funcao FROM operadores")
        st.table(usuarios)
