import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io

# --- 1. BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('gestao_lavanderia.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS operadores (id INTEGER PRIMARY KEY, nome TEXT UNIQUE, senha TEXT, funcao TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS lotes (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 hospital TEXT, peso_entrada REAL, maquina TEXT, processo TEXT, status TEXT,
                 inicio_lavagem TEXT, fim_lavagem TEXT,
                 inicio_secagem TEXT, fim_secagem TEXT,
                 inicio_acabamento TEXT, fim_acabamento TEXT,
                 saida_motorista TEXT, motorista_nome TEXT,
                 peso_saida REAL, gaiola_num TEXT,
                 operador_lavagem TEXT, operador_secagem TEXT, operador_acabamento TEXT)''')
    c.execute('CREATE TABLE IF NOT EXISTS contagem_itens (lote_id INTEGER, item TEXT, quantidade INTEGER)')
    
    # Criar admin e um motorista de exemplo se vazio
    if not executar_query("SELECT * FROM operadores WHERE nome='admin'"):
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", ('admin', '1234', 'Gerente'))
        executar_query("INSERT INTO operadores (nome, senha, funcao) VALUES (?,?,?)", ('motorista1', '123', 'Motorista'))
    conn.commit()
    conn.close()

def executar_query(sql, params=()):
    with sqlite3.connect('gestao_lavanderia.db') as conn:
        if "SELECT" in sql.upper():
            return pd.read_sql_query(sql, conn, params=params)
        conn.execute(sql, params)
        conn.commit()

# --- 2. INICIALIZAÇÃO ---
init_db()
if 'logado' not in st.session_state: st.session_state['logado'] = False

# --- 3. LOGIN ---
if not st.session_state['logado']:
    st.title("🏥 Lavanderia Hospitalar - Rastreabilidade")
    u = st.text_input("Usuário")
    s = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        res = executar_query("SELECT nome, funcao FROM operadores WHERE nome=? AND senha=?", (u, s))
        if not res.empty:
            st.session_state.update({"logado": True, "operador": u, "funcao": res.iloc[0]['funcao']})
            st.rerun()
        else: st.error("Login inválido")
else:
    st.sidebar.title(f"👤 {st.session_state['operador']}")
    st.sidebar.info(f"Função: {st.session_state['funcao']}")
    
    # Menu filtrado por função
    opcoes_menu = ["1. Lavagem", "2. Secagem", "3. Acabamento", "4. Expedição", "📊 Relatórios"]
    if st.session_state['funcao'] == 'Motorista':
        opcoes_menu = ["🚚 Retirada Motorista"]
    
    etapa = st.sidebar.radio("Navegação", opcoes_menu)
    
    if st.sidebar.button("Sair"):
        st.session_state['logado'] = False
        st.rerun()

    # --- ETAPA MOTORISTA (NOVA) ---
    if etapa == "🚚 Retirada Motorista":
        st.header("🚚 Confirmação de Entrega (Motorista)")
        # Lotes que estão na expedição mas ainda não saíram com motorista
        df_pronto = executar_query("SELECT id, hospital, gaiola_num, peso_saida FROM lotes WHERE status='Finalizado'")
        
        if not df_pronto.empty:
            st.write("Selecione os lotes/gaiolas que você está carregando agora:")
            for idx, row in df_pronto.iterrows():
                col1, col2 = st.columns([3, 1])
                col1.warning(f"Gaiola: {row['gaiola_num']} | Hospital: {row['hospital']} | Peso: {row['peso_saida']}kg")
                if col2.button("Confirmar Retirada", key=f"mot_{row['id']}"):
                    dt_saida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Em Transito', saida_motorista=?, motorista_nome=? WHERE id=?", 
                                   (dt_saida, st.session_state['operador'], row['id']))
                    st.success(f"Gaiola {row['gaiola_num']} registrada com você!")
                    st.rerun()
        else:
            st.info("Nenhuma gaiola pronta para retirada no momento.")

    # --- ETAPA 4: EXPEDIÇÃO (Ajustada para preparar para o motorista) ---
    elif etapa == "4. Expedição":
        st.header("📦 Preparar Gaiola")
        df = executar_query("SELECT id, hospital FROM lotes WHERE status='Pronto'")
        if not df.empty:
            with st.form("exp"):
                sel = st.selectbox("Lote", df['id'].astype(str) + " - " + df['hospital'])
                id_l = sel.split(" - ")[0]
                pf = st.number_input("Peso Final Total (kg)", min_value=0.1)
                g = st.text_input("Número da Gaiola")
                if st.form_submit_button("Disponibilizar para Motorista"):
                    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    executar_query("UPDATE lotes SET status='Finalizado', fim_acabamento=?, peso_saida=?, gaiola_num=? WHERE id=?", 
                                   (dt, pf, g, id_l))
                    st.success("Gaiola enviada para a doca de saída!")
                    st.rerun()
        else: st.info("Nada pendente para pesagem final.")

    # [Manter as outras etapas de Lavagem, Secagem, Acabamento e Relatórios...]

    # --- RELATÓRIOS (Ajustado para mostrar o motorista) ---
    elif etapa == "📊 Relatórios":
        st.title("📊 Histórico de Saídas")
        df_saidas = executar_query("SELECT id, hospital, gaiola_num, motorista_nome, saida_motorista, peso_saida FROM lotes WHERE status='Em Transito'")
        if not df_saidas.empty:
            st.write("### Roupas em Trânsito com Motoristas")
            st.dataframe(df_saidas)
        else:
            st.info("Nenhuma entrega em trânsito no momento.")

