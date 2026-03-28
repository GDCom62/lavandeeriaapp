import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração Visual
st.set_page_config(page_title="Lavo e Levo V5", page_icon="🧺", layout="wide")

# Conexão com Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

# Estrutura de Colunas
cols = ["id", "cli", "p_in", "p_out", "tipo", "status", "detalhes", "itens", "gaiola", "mot", "h_entrada"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

def agora(): return datetime.now().strftime("%H:%M")

def salvar(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()

st.title("🧺 LAVANDERIA LAVO E LEVO - SISTEMA INDUSTRIAL V5")

# --- 1. ENTRADA E LAVAGEM ---
with st.expander("➕ 1. RECEBIMENTO / CARGA MÁQUINA", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente:")
        p_in = c2.number_input("Peso Bruto (kg):", 0.0)
        tipo = c1.selectbox("Processo:", ["Novo", "Relave"])
        maq = c2.selectbox("Máquina Lavar:", ["LAV-01", "LAV-02", "Industrial-01"])
        resp = c1.text_input("Colaborador (Carga):")
        if st.form_submit_button("REGISTRAR ENTRADA"):
            if cli and resp:
                h = agora()
                log = f"[{h}] Lavagem: {resp} ({maq})"
                novo = pd.DataFrame([{
                    "id": len(df)+1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0,
                    "tipo": tipo, "status": "Lavagem", "detalhes": log,
                    "itens": "", "gaiola": "", "mot": "", "h_entrada": h
                }])
                df = pd.concat([df, novo], ignore_index=True)
                salvar(df) ; st.rerun()

st.write("---")

# --- FILA DE TRABALHO ATIVA ---
ativos = df[df['status'] != "Entregue"]

for i, row in ativos.iterrows():
    idx = df[df['id'] == row['id']].index # Localiza o índice real
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg)")
        st.caption(f"📜 Histórico: {row['detalhes']}")

        # 2. LAVAGEM -> TRANSPORTE -> SECAGEM
        if row['status'] == "Lavagem":
            r2 = st.text_input("Colaborador (Retira e leva p/ Secagem):", key=f"r2_{i}")
            if st.button("➡️ Enviar para Secagem", key=f"b2_{i}"):
                if r2:
                    df.at[idx, 'status'] = "Secagem"
                    df.at[idx, 'detalhes'] += f" | [{agora()}] Transporte: {r2}"
                    salvar(df) ; st.rerun()

        # 3. SECAGEM -> ESCOLHA DESTINO
        elif row['status'] == "Secagem":
            r3 = st.text_input("Colaborador (Opera Secadora):", key=f"r3_{i}")
            maq_s = st.selectbox("Máquina Secar:", ["SEC-01", "SEC-02"], key=f"ms_{i}")
            c1, c2 = st.columns(2)
            if c1.button("👔 Passadeira", key=f"bp_{i}"):
                if r3:
                    df.at[idx, 'status'], df.at[idx, 'detalhes'] = "Passadeira", row['detalhes'] + f" | [{agora()}] Secagem: {r3} ({maq_s}) -> Passa"
                    salvar(df) ; st.rerun()
            if c2.button("📦 Dobragem", key=f"bd_{i}"):
                if r3:
                    df.at[idx, 'status'], df.at[idx, 'detalhes'] = "Dobragem", row['detalhes'] + f" | [{agora()}] Secagem: {r3} ({maq_s}) -> Dobra"
                    salvar(df) ; st.rerun()

        # 4/5. ACABAMENTO -> CONTAGEM
        elif row['status'] in ["Passadeira", "Dobragem"]:
            r4 = st.text_input("Colaborador (Contagem/Empacotamento):", key=f"r4_{i}")
            t_p = st.text_input("Peça:", key=f"tp_{i}")
            q_p = st.number_input("Qtd:", 1, key=f"qp_{i}")
            if st.button("➕ Add Item", key=f"ba_{i}"):
                df.at[idx, 'itens'] += f"{t_p}({q_p}); "
                salvar(df) ; st.rerun()
            
            st.info(f"Contagem: {row['itens']}")
            if st.button("🎁 Finalizar p/ Gaiola", key=f"bf_{i}"):
                if r4:
                    df.at[idx, 'status'], df.at[idx, 'detalhes'] = "Gaiola", row['detalhes'] + f" | [{agora()}] Acabamento: {r4}"
                    salvar(df) ; st.rerun()

        # 6/7. GAIOLA -> MOTORISTA
        elif row['status'] == "Gaiola":
            p_out = st.number_input("Peso Saída (kg):", 0.0, key=f"po_{i}")
            gai = st.text_input("Nº Gaiola:", key=f"g_{i}")
            mot = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"m_{i}")
            if st.button("🚚 LIBERAR ENTREGA", key=f"be_{i}"):
                if p_out > 0:
                    df.at[idx, 'status'], df.at[idx, 'p_out'], df.at[idx, 'mot'], df.at[idx, 'gaiola'] = "Entregue", p_out, mot, gai
                    df.at[idx, 'detalhes'] += f" | [{agora()}] Saída: Gaiola {gai} com {mot}"
                    salvar(df) ; st.rerun()

if st.checkbox("📊 Ver Relatório Completo"):
    st.dataframe(df)
