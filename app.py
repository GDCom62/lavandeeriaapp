import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração de Página
st.set_page_config(page_title="Lavo e Levo V5", page_icon="🧺", layout="wide")

# Conexão com Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

# Colunas do Banco de Dados
cols = ["id", "cli", "p_in", "p_out", "tipo", "status", "detalhes", "itens", "gaiola", "mot", "h_entrada"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

def agora(): return datetime.now().strftime("%H:%M")

def salvar(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()

st.title("🧺 LAVANDERIA LAVO E LEVO - V5")

# --- PAINEL DE METAS DIÁRIAS ---
st.sidebar.header("🎯 Metas de Produção")
meta_kg = st.sidebar.number_input("Meta do Dia (kg):", 100, 5000, 500)
kg_processados = df[df['status'] == 'Entregue']['p_out'].sum()
progresso = min(float(kg_processados / meta_kg), 1.0)

st.sidebar.metric("Produzido Hoje", f"{kg_processados:.1f} kg")
st.sidebar.progress(progresso)
st.sidebar.write(f"Faltam: {max(0.0, meta_kg - kg_processados):.1f} kg")

# --- 1. RECEBIMENTO / LAVAGEM ---
with st.expander("➕ 1. RECEBIMENTO", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente:")
        p_in = c2.number_input("Peso Entrada (kg):", 0.0)
        tipo = c1.selectbox("Processo:", ["Novo", "Relave"])
        maq = c2.selectbox("Máquina Lavar:", ["LAV-01", "LAV-02", "Industrial-01"])
        resp = c1.text_input("Responsável Carga:")
        if st.form_submit_button("REGISTRAR"):
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
    idx = df[df['id'] == row['id']].index
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** | Status: `{row['status']}`")
        st.caption(f"📜 Histórico: {row['detalhes']}")
        
        if row['status'] == "Lavagem":
            r2 = st.text_input("Quem leva p/ Secar?", key=f"r2_{row['id']}")
            if st.button("➡️ Enviar para Secadora", key=f"b2_{row['id']}"):
                df.at[idx, 'status'] = "Secagem"
                df.at[idx, 'detalhes'] = row['detalhes'] + f" | [{agora()}] Transp: {r2}"
                salvar(df) ; st.rerun()

        elif row['status'] == "Secagem":
            r3 = st.text_input("Quem opera Secadora?", key=f"r3_{row['id']}")
            c1, c2 = st.columns(2)
            if c1.button("👔 Passadeira", key=f"bp_{row['id']}"):
                df.at[idx, 'status'] = "Passadeira"
                df.at[idx, 'detalhes'] = row['detalhes'] + f" | [{agora()}] Secagem: {r3}"
                salvar(df) ; st.rerun()
            if c2.button("📦 Dobragem", key=f"bd_{row['id']}"):
                df.at[idx, 'status'] = "Dobragem"
                df.at[idx, 'detalhes'] = row['detalhes'] + f" | [{agora()}] Secagem: {r3}"
                salvar(df) ; st.rerun()

        elif row['status'] in ["Passadeira", "Dobragem"]:
            r4 = st.text_input("Quem faz contagem?", key=f"r4_{row['id']}")
            t_p = st.text_input("Peça:", key=f"tp_{row['id']}")
            q_p = st.number_input("Qtd:", 1, key=f"qp_{row['id']}")
            if st.button("➕ Add Item", key=f"ba_{row['id']}"):
                df.at[idx, 'itens'] = str(row['itens']) + f"{t_p}({q_p}); "
                salvar(df) ; st.rerun()
            if st.button("🎁 Finalizar p/ Gaiola", key=f"bf_{row['id']}"):
                df.at[idx, 'status'] = "Gaiola"
                df.at[idx, 'detalhes'] = row['detalhes'] + f" | [{agora()}] Acabam: {r4}"
                salvar(df) ; st.rerun()

        elif row['status'] == "Gaiola":
            p_out = st.number_input("Peso Saída:", 0.0, key=f"po_{row['id']}")
            gai = st.text_input("Nº Gaiola:", key=f"g_{row['id']}")
            mot = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"mot_{row['id']}")
            if st.button("🚚 LIBERAR", key=f"be_{row['id']}"):
                if p_out > 0:
                    df.at[idx, 'status'] = "Entregue"
                    df.at[idx, 'p_out'] = p_out
                    df.at[idx, 'mot'] = mot
                    df.at[idx, 'gaiola'] = gai
                    salvar(df) ; st.rerun()

if st.checkbox("📊 Ver Planilha"):
    st.dataframe(df)
