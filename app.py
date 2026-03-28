import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração de Página e Ícone
st.set_page_config(page_title="Lavo e Levo Industrial", page_icon="🧺", layout="wide")

# Conector com Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
except:
    st.error("Erro de conexão. Verifique os Secrets.")
    st.stop()

# Garantir colunas se estiver vazio
cols = ["id", "cli", "p_in", "p_out", "tipo", "status", "detalhes_processo", "itens_contagem", "gaiola", "mot", "h_entrada"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

def agora(): return datetime.now().strftime("%H:%M")

def salvar(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()

st.title("🧺 LAVANDERIA LAVO E LEVO - FLUXO INDUSTRIAL")

# --- 1. RECEBIMENTO E LAVAGEM ---
with st.expander("➕ 1. RECEBIMENTO / ENTRADA NA MÁQUINA", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente:")
        p_in = c2.number_input("Peso Bruto (kg):", 0.1)
        tipo = c1.selectbox("Processo:", ["Novo", "Relave"])
        maq = c2.selectbox("Máquina Lavar:", ["LAV-01", "LAV-02", "Industrial-01"])
        resp = c1.text_input("Colaborador (Separação/Lavagem):")
        if st.form_submit_button("REGISTRAR"):
            if cli and resp:
                h = agora()
                log = f"[{h}] Lavagem: {resp} na {maq}"
                novo = pd.DataFrame([{
                    "id": len(df)+1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0,
                    "tipo": tipo, "status": "Lavagem", "detalhes_processo": log,
                    "itens_contagem": "", "gaiola": "", "mot": "", "h_entrada": h
                }])
                df = pd.concat([df, novo], ignore_index=True)
                salvar(df) ; st.rerun()

st.write("---")

# --- FILA DE TRABALHO ---
ativos = df[df['status'] != "Entregue"]

for i, row in ativos.iterrows():
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg)")
        st.caption(f"📜 Histórico: {row['detalhes_processo']}")

        # 2. LAVAGEM -> SECAGEM
        if row['status'] == "Lavagem":
            r2 = st.text_input("Colaborador (Leva p/ Secagem):", key=f"r2_{i}")
            if st.button("➡️ Entregar na Secadora", key=f"b2_{i}"):
                if r2:
                    df.at[i, 'status'] = "Secagem"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Levado p/ Secagem por: {r2}"
                    salvar(df) ; st.rerun()

        # 3. OPERAÇÃO SECADORA -> ESCOLHA
        elif row['status'] == "Secagem":
            r3 = st.text_input("Colaborador (Opera Secadora):", key=f"r3_{i}")
            maq_s = st.selectbox("Máquina Secar:", ["SEC-01", "SEC-02"], key=f"ms_{i}")
            c_p, c_d = st.columns(2)
            if c_p.button("👔 Passadeira", key=f"bp_{i}"):
                if r3:
                    df.at[i, 'status'] = "Passadeira"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Secagem: {r3} na {maq_s}. Destino: Passadeira"
                    salvar(df) ; st.rerun()
            if c_d.button("📦 Dobragem", key=f"bd_{i}"):
                if r3:
                    df.at[i, 'status'] = "Dobragem"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Secagem: {r3} na {maq_s}. Destino: Dobragem"
                    salvar(df) ; st.rerun()

        # 4/5. PROCESSAMENTO -> CONTAGEM
        elif row['status'] in ["Passadeira", "Dobragem"]:
            r4 = st.text_input("Colaborador (Dobra/Passa e Conta):", key=f"r4_{i}")
            st.write("Relação de Peças:")
            t_p = st.text_input("Tipo:", key=f"tp_{i}")
            q_p = st.number_input("Qtd:", 1, key=f"qp_{i}")
            if st.button("➕ Add Item", key=f"ba_{i}"):
                df.at[i, 'itens_contagem'] += f"{t_p}({q_p}); "
                salvar(df) ; st.rerun()
            
            st.info(f"Contagem: {row['itens_contagem']}")
            if st.button("🎁 Finalizar e Pesar", key=f"bf_{i}"):
                if r4:
                    df.at[i, 'status'] = "Gaiola"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Acabamento: {r4}"
                    salvar(df) ; st.rerun()

        # 6/7. GAIOLA E MOTORISTA
        elif row['status'] == "Gaiola":
            p_out = st.number_input("Peso Saída (kg):", 0.1, key=f"po_{i}")
            gaiola = st.text_input("Nº Gaiola:", key=f"g_{i}")
            mot = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"mot_{i}")
            if st.button("🚚 LIBERAR PARA ENTREGA", key=f"be_{i}"):
                if p_out > 0:
                    df.at[i, 'status'], df.at[i, 'p_out'] = "Entregue", p_out
                    df.at[i, 'mot'], df.at[i, 'gaiola'] = mot, gaiola
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Expedição: Gaiola {gaiola} com {mot}"
                    salvar(df) ; st.rerun()

if st.checkbox("📊 Relatório"):
    st.dataframe(df)
