import streamlit as st
import pandas as pd
from datetime import datetime
import io
from sqlalchemy import create_engine, text
from fpdf import FPDF

# --- 1. CONFIGURAÇÃO DE ACESSO MÚLTIPLO ---
engine = create_engine("sqlite:///gestao_lavanderia.db", pool_size=20, max_overflow=30)

def executar_query(sql, params={}):
    with engine.begin() as conn:
        conn.execute(text(sql), params)

def consultar_db(sql, params={}):
    with engine.connect() as conn:
        return pd.read_sql_query(text(sql), conn, params=params)

# --- 2. FUNÇÃO PARA GERAR PDF (ETIQUETA) ---
def gerar_pdf_gaiola(dados_lote, itens):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, "ETIQUETA DE EXPEDIÇÃO - LAVANDERIA", 1, 1, "C")
    
    pdf.set_font("Arial", "", 12)
    pdf.ln(10)
    pdf.cell(95, 10, f"Hospital: {dados_lote['hospital']}", 0, 0)
    pdf.cell(95, 10, f"Gaiola N°: {dados_lote['gaiola_num']}", 0, 1)
    pdf.cell(95, 10, f"Data Saída: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 0)
    pdf.cell(95, 10, f"Peso Saída: {dados_lote['peso_saida']} kg", 0, 1)
    
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(190, 10, "RELAÇÃO DE PEÇAS:", 0, 1)
    pdf.set_font("Arial", "", 12)
    
    for _, item in itens.iterrows():
        pdf.cell(190, 8, f"- {item['item']}: {item['quantidade']} unidades", 0, 1)
    
    pdf.ln(10)
    pdf.cell(190, 10, f"Responsável: {st.session_state['operador']}", 0, 1)
    
    return pdf.output()

# --- 3. INICIALIZAÇÃO DO BANCO ---
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

# --- 4. INTERFACE ---
st.set_page_config(page_title="Lavanderia Hospitalar Pro", layout="wide")
init_db()

for key, val in {'logado': False, 'operador': "", 'funcao': "", 'etapa_atual': "Início"}.items():
    if key not in st.session_state: st.session_state[key] = val

if not st.session_state['logado']:
    st.title("🏥 Lavanderia Hospitalar - Gestão")
    with st.container(border=True):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.button("Entrar"):
            res = consultar_db("SELECT nome, funcao FROM operadores WHERE nome=:u AND senha=:s", {"u": u, "s": s})
            if not res.empty:
                st.session_state.update({"logado": True, "operador": res.iloc[0]['nome'], "funcao": res.iloc[0]['funcao']})
                st.rerun()
            else: st.error("Acesso Negado")
else:
    # --- BARRA LATERAL ---
    st.sidebar.header(f"👤 {st.session_state['operador']}")
    menu_op = ["Painel Geral", "1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "🚚 Motorista", "📊 Relatórios"]
    menu = st.sidebar.radio("Navegação", menu_op)
    if st.sidebar.button("Sair"):
        st.session_state.update({"logado": False}); st.rerun()

    # --- TELA 4: EXPEDIÇÃO E PDF ---
    if menu == "4. Expedição":
        st.header("📦 Pesagem e Gaiola")
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Pronto', 'Disponível')")
        if not df.empty:
            sel = st.selectbox("Selecione o Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status = df[df['id'] == id_l]['status'].values[0]

            if status == 'Pronto':
                with st.form("exp_form"):
                    ps = st.number_input("Peso Final Saída (kg)", min_value=0.1)
                    gai = st.text_input("Nº da Gaiola")
                    if st.form_submit_button("✅ Liberar para Motorista"):
                        executar_query("UPDATE lotes SET status='Disponível', fim_acabamento=:dt, peso_saida=:ps, gaiola_num=:g WHERE id=:id",
                                       {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "ps": ps, "g": gai, "id": id_l})
                        st.rerun()
            else:
                st.success("Gaiola Disponível para o Motorista")
                # Busca itens para o PDF
                itens = consultar_db("SELECT item, quantidade FROM contagem_itens WHERE lote_id=:id", {"id": id_l})
                lote_data = consultar_db("SELECT * FROM lotes WHERE id=:id", {"id": id_l}).iloc[0]
                
                pdf_bytes = gerar_pdf_gaiola(lote_data, itens)
                st.download_button("📥 Baixar Etiqueta (PDF)", pdf_bytes, f"etiqueta_gaiola_{lote_data['gaiola_num']}.pdf", "application/pdf")
                
                if st.button("⏪ Estornar para Acabamento"):
                    executar_query("UPDATE lotes SET status='Pronto', peso_saida=NULL, gaiola_num=NULL WHERE id=:id", {"id": id_l})
                    st.rerun()
        else: st.info("Nada pendente para expedição.")

    # [AS OUTRAS ETAPAS (1, 2, 3) DEVEM SER MANTIDAS CONFORME O CÓDIGO ANTERIOR]
    elif menu == "1. Lavagem":
        st.header("📥 Configurar Carga")
        maq = st.selectbox("Máquina", ["M1", "M2", "M3", "M4", "M5"])
        with st.form("add_tambor", clear_on_submit=True):
            h_nome = st.selectbox("Hospital", ["Hospital A", "Hospital B", "Hospital C"])
            h_peso = st.number_input("Peso (kg)", min_value=1.0)
            if st.form_submit_button("➕ Adicionar"):
                executar_query("INSERT INTO lotes (hospital, peso_entrada, maquina, status, inicio_lavagem, operador_lavagem) VALUES (:h, :p, :m, 'Lavando', :dt, :op)",
                               {"h": h_nome, "p": h_peso, "m": maq, "dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "op": st.session_state['operador']})
                st.success("Lote Iniciado!"); st.rerun()

    elif menu == "2. Secagem":
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Lavando', 'Secando')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status = df[df['id'] == id_l]['status'].values[0]
            if status == 'Lavando' and st.button("🔥 Iniciar Secagem"):
                executar_query("UPDATE lotes SET status='Secando', fim_lavagem=:dt, inicio_secagem=:dt, operador_secagem=:op WHERE id=:id", 
                               {"dt": datetime.now().strftime("%Y-%m-%d %H:%M"), "op": st.session_state['operador'], "id": id_l})
                st.rerun()
            elif status == 'Secando' and st.button("⏪ Estornar"):
                executar_query("UPDATE lotes SET status='Lavando' WHERE id=:id", {"id": id_l}); st.rerun()

    elif menu == "3. Acabamento":
        df = consultar_db("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
        if not df.empty:
            sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
            id_l = int(sel.split(" - "))
            status = df[df['id'] == id_l]['status'].values[0]
            if status == 'Secando':
                df_itens = pd.DataFrame([{"Item": i, "Qtd": 0} for i in ["Lençol", "Fronha", "Pijama"]])
                ed = st.data_editor(df_itens, hide_index=True)
                if st.button("✅ Salvar"):
                    executar_query("UPDATE lotes SET status='Pronto' WHERE id=:id", {"id": id_l})
                    for _, r in ed.iterrows():
                        if r['Qtd'] > 0: executar_query("INSERT INTO contagem_itens VALUES (:id, :it, :q)", {"id": id_l, "it": r['Item'], "q": r['Qtd']})
                    st.rerun()
