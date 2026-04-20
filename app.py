import streamlit as st
import pandas as pd
from datetime import datetime
import io
import smtplib
from email.message import EmailMessage
from sqlalchemy import create_engine, text
from fpdf import FPDF

# --- 1. DESIGN E CONFIGURAÇÃO ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")

# CSS para Design Elegante
st.markdown("""
    <style>
    .stButton>button, .stTextInput>div>div>input, .stSelectbox>div>div>div, .stNumberInput>div>div>input, .stDataEditor { border-radius: 12px !important; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #e0e0e0; }
    [data-testid="stForm"], div[data-testid="stExpander"], .stMetric { 
        border-radius: 15px !important; border: 1px solid #eef2f6 !important; 
        background-color: #ffffff; padding: 20px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.05); 
    }
    h1, h2, h3 { color: #1E3A8A; font-family: 'Segoe UI', sans-serif; }
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
    executar_query('CREATE TABLE IF NOT EXISTS alertas_panico (id INTEGER PRIMARY KEY AUTOINCREMENT, operador TEXT, etapa TEXT, data TEXT, resolvido INTEGER)')
    if consultar_db("SELECT * FROM operadores WHERE nome='admin'").empty:
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES ('admin', '1234', 'Administrador')")

init_db()

# --- 3. ESTADO DA SESSÃO ---
for key, val in {'logado': False, 'operador': "", 'funcao': "", 'tambor': [], 'etapa_atual': "Início"}.items():
    if key not in st.session_state: st.session_state[key] = val

# --- 4. FUNÇÕES AUXILIARES (PDF E BACKUP) ---
def gerar_pdf_etiqueta(lote, itens):
    pdf = FPDF()
    pdf.add_page()
    try: pdf.image('logo.png', 10, 8, 33)
    except: pass
    pdf.set_font("Arial", "B", 18)
    pdf.cell(190, 15, "ETIQUETA DE GAIOLA", 1, 1, "C")
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(95, 10, f"Hospital: {lote['hospital']}", 0, 0)
    pdf.cell(95, 10, f"Gaiola N°: {lote['gaiola_num']}", 0, 1)
    pdf.cell(95, 10, f"Peso Final: {lote['peso_saida']} kg", 0, 0)
    pdf.cell(95, 10, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1)
    pdf.ln(5); pdf.set_font("Arial", "B", 12); pdf.cell(190, 10, "CONTEÚDO:", 0, 1)
    for _, item in itens.iterrows():
        pdf.cell(190, 8, f"- {item['item']}: {item['quantidade']} un", 0, 1)
    return bytes(pdf.output())

def enviar_backup_email():
    try:
        remetente = st.secrets["email_remetente"]
        senha = st.secrets["email_senha"]
        destinatario = st.secrets["email_destinatario"]
        msg = EmailMessage()
        msg['Subject'] = f"📦 BACKUP LAVANDERIA - {datetime.now().strftime('%d/%m/%Y')}"
        msg['From'], msg['To'] = remetente, destinatario
        msg.set_content("Backup em anexo.")
        with open("gestao_lavanderia.db", "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="x-sqlite3", filename="gestao_lavanderia.db")
        with smtplib.SMTP_SSL('://gmail.com', 465) as smtp:
            smtp.login(remetente, senha)
            smtp.send_message(msg)
        return True
    except: return False

# --- 5. LOGIN ---
if not st.session_state['logado']:
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        try: st.image("logo.png", use_container_width=True)
        except: st.title("🏥 Gestão Lavanderia")
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
    try: st.sidebar.image("logo.png", use_container_width=True)
    except: pass
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    
    menu = st.sidebar.radio("Navegação", ["Painel Geral", "1. Lavagem", "2. Rampa", "3. Secagem", "4. Acabamento", "5. Expedição", "📊 Relatórios", "⚙️ Gestão"])
    if st.sidebar.button("Sair"): st.session_state['logado'] = False; st.rerun()

    # --- 6. TELAS ---
    if menu == "Painel Geral":
        col_t1, col_t2 = st.columns([1, 4])
        with col_t1:
            try: st.image("logo.png", width=120)
            except: pass
        with col_t2:
            st.title("📈 Monitoramento Ativo")
        
        panicos = consultar_db("SELECT * FROM alertas_panico WHERE resolvido=0")
        if not panicos.empty:
            for _, p in panicos.iterrows():
                st.error(f"🆘 PÂNICO: {p['operador']} em {p['etapa']} ({p['data']})")
                if st.button(f"Resolver {p['id']}", key=f"pan_{p['id']}"):
                    executar_query("UPDATE alertas_panico SET resolvido=1 WHERE id=:id", {"id": p['id']}); st.rerun()
        
        df_l = consultar_db("SELECT id, hospital, status, maquina, inicio_lavagem FROM lotes WHERE status != 'Finalizado'")
        if not df_l.empty:
            st.dataframe(df_l, use_container_width=True)
            sel_raw = st.selectbox("Gerenciar Lote:", ["Selecione..."] + (df_l['id'].astype(str) + " - " + df_l['hospital']).tolist())
            if sel_raw != "Selecione...":
                id_r = int(sel_raw.split(" - "))
                c1, c2 = st.columns(2)
                if c1.button("🔄 Reiniciar"):
                    executar_query("UPDATE lotes SET status='Lavando', fim_lavagem=NULL, inicio_secagem=NULL, fim_secagem=NULL, inicio_acabamento=NULL, fim_acabamento=NULL WHERE id=:id", {"id": id_r}); st.rerun()
                if c2.button("❌ Excluir"):
                    executar_query("DELETE FROM lotes WHERE id=:id", {"id": id_r}); st.rerun()
        else: st.info("Sem lotes em processamento.")

    elif menu == "1. Lavagem":
        st.header("📥 Entrada Lavadora")
        maq = st.selectbox("Máquina", ["M1 (120kg)", "M2 (120kg)", "M3 (100kg)", "M4 (60kg)", "M5 (50kg)"])
        with st.form("add_tambor", clear_on_submit=True):
            h_n = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            h_p = st.number_input("Peso (kg)", min_value=1.0)
            h_t = st.radio("Classificação", ["Leve", "Pesada", "Relave"], horizontal=True)
            if st.form_submit_button("➕ Adicionar"): st.session_state.tambor.append({"h": h_n, "p": h_p, "t": h_t})
        if st.session_state.tambor:
            st.table(pd.DataFrame(st.session_state.tambor))
            if st.button("🚀 INICIAR LAVAGEM"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                for i in st.session_state.tambor:
                    executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, processo, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, :pr, 'Lavando', :dt, :op)",
                                   {"h": i['h'], "p": i['p'], "m": maq, "pr": i['t'], "dt": dt, "op": st.session_state['operador']})
                st.session_state.tambor = []; st.rerun()

    elif menu == "2. Rampa":
        st.header("⏳ Rampa (Saída Lavagem)")
        df = consultar_db("SELECT id, hospital FROM lotes WHERE status='Lavando'")
        if not df.empty:
            sel = st.selectbox("Lote saindo:", df['id'].astype(str) + " - " + df['hospital'])
            if st.button("✅ Enviar p/ Rampa"):
                executar_query("UPDATE lotes SET status='Na Rampa', fim_lavagem=:dt WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "id": int(sel.split(" - "))}); st.rerun()

    elif menu == "3. Secagem":
        st.header("🔥 Secagem")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Na Rampa', 'Secando')")
        if not df.empty:
            sel = st.selectbox("Lote:", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            stat = df[df['id']==id_l].iloc[0]['status']
            if stat == 'Na Rampa' and st.button("🚀 Iniciar Secagem"):
                executar_query("UPDATE lotes SET status='Secando', inicio_secagem=:dt, operador_secagem=:op WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "op": st.session_state['operador'], "id": id_l}); st.rerun()
            elif stat == 'Secando' and st.button("⏪ Estornar"):
                executar_query("UPDATE lotes SET status='Na Rampa', inicio_secagem=NULL WHERE id=:id", {"id": id_l}); st.rerun()

    elif menu == "4. Acabamento":
        st.header("🧺 Dobra e Passagem")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote:", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            if df[df['id']==id_l].iloc[0]['status'] == 'Secando':
                lista = ["Lencol", "Fronha", "Oleado", "Colcha", "Edredon", "Calca", "Camisa", "Campo", "Tracado", "Camisola Adulto", "Camisola Infantil", "Cobertor", "Capote", "Toalha de Banho", "Toalha de Rosto", "Piso", "Cortina", "Outros"]
                ed = st.data_editor(pd.DataFrame([{"Item": i, "Qtd": 0} for i in lista]), use_container_width=True, hide_index=True)
                if st.button("✅ Salvar"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M")
                    executar_query("UPDATE lotes SET status='Pronto', fim_secagem=:dt, inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id", {"dt": dt, "op": st.session_state['operador'], "id": id_l})
                    for _, r in ed.iterrows():
                        if r['Qtd'] > 0: executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": r['Item'], "q": r['Qtd']})
                    st.rerun()
            elif st.button("⏪ Estornar"):
                executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL, inicio_acabamento=NULL WHERE id=:id", {"id": id_l}); executar_query("DELETE FROM contagem_itens WHERE lote_id=:id", {"id": id_l}); st.rerun()

    elif menu == "5. Expedição":
        st.header("📦 Expedição")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Pronto', 'Disponível')")
        if not df.empty:
            sel = st.selectbox("Lote:", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            if df[df['id']==id_l].iloc[0]['status'] == 'Pronto':
                ps, gai = st.number_input("Peso Saída", min_value=0.1), st.text_input("Gaiola N°")
                if st.button("✅ Liberar"):
                    executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=:dt, peso_saida=:ps, gaiola_num=:g WHERE id=:id", {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "ps": ps, "g": gai, "id": id_l}); st.rerun()
            else:
                ld = consultar_db("SELECT * FROM lotes WHERE id=:id", {"id": id_l}).iloc[0]
                it = consultar_db("SELECT item, quantidade FROM contagem_itens WHERE lote_id=:id", {"id": id_l})
                st.download_button("📥 Etiqueta PDF", gerar_pdf_etiqueta(ld, it), f"etiq_{id_l}.pdf", "application/pdf")

    elif menu == "📊 Relatórios":
        st.title("📊 Ranking e Produtividade")
        df = consultar_db("SELECT * FROM lotes")
        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏆 Top 3 Clientes (Kg)")
                st.write(df.groupby('hospital')['peso_entrada'].sum().sort_values(ascending=False).head(3))
            with c2:
                st.subheader("👷 Top 3 Colaboradores (Kg)")
                ops = pd.concat([df[['operador_lavagem', 'peso_entrada']].rename(columns={'operador_lavagem': 'op'}), df[['operador_secagem', 'peso_entrada']].rename(columns={'operador_secagem': 'op'}), df[['operador_acabamento', 'peso_entrada']].rename(columns={'operador_acabamento': 'op'})])
                st.write(ops.dropna().groupby('op')['peso_entrada'].sum().sort_values(ascending=False).head(3))
            st.divider(); st.dataframe(df)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as wr: df.to_excel(wr, index=False)
            st.download_button("📥 Exportar Excel", buf.getvalue(), "relatorio.xlsx")

    elif menu == "⚙️ Gestão":
        st.header("⚙️ Gestão e Backup")
        with st.expander("Cadastrar Colaborador"):
            with st.form("cad"):
                n, s, f = st.text_input("Nome"), st.text_input("Senha"), st.selectbox("Função", ["Operador", "Motorista", "Administrador"])
                if st.form_submit_button("Salvar"): executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (:n, :s, :f)", {"n": n, "s": s, "f": f}); st.rerun()
        if st.button("🚀 Enviar Backup por E-mail"):
            if enviar_backup_email(): st.success("Backup enviado!")
            else: st.error("Erro no backup. Verifique os Secrets.")
