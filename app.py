import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Lavo e Levo V5", page_icon="🧺", layout="wide")

# Conexão com tratamento de erro
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
except Exception as e:
    st.error("⚠️ Erro de conexão com a planilha (404).")
    st.info("Verifique se a URL nos Secrets está correta e se a planilha está compartilhada como EDITOR.")
    st.stop()

# Cabeçalhos necessários
cols = ["id", "cli", "p_in", "p_out", "tipo", "status", "detalhes", "itens", "gaiola", "mot", "h_entrada"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

def agora(): return datetime.now().strftime("%H:%M")

def salvar(novo_df):
    try:
        conn.update(data=novo_df)
        st.cache_data.clear()
        st.success("✅ Sincronizado com a nuvem!")
    except:
        st.error("❌ Falha ao salvar. Verifique se a planilha permite edição.")

st.title("🧺 LAVANDERIA LAVO E LEVO - V5")

# --- 1. ENTRADA ---
with st.expander("➕ 1. RECEBIMENTO", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente:")
        p_in = c2.number_input("Peso Entrada (kg):", 0.0)
        resp = c1.text_input("Responsável:")
        if st.form_submit_button("REGISTRAR"):
            if cli and resp:
                h = agora()
                novo = pd.DataFrame([{
                    "id": len(df)+1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0,
                    "tipo": "Novo", "status": "Lavagem", "detalhes": f"[{h}] Lavagem: {resp}",
                    "itens": "", "gaiola": "", "mot": "", "h_entrada": h
                }])
                df = pd.concat([df, novo], ignore_index=True)
                salvar(df); st.rerun()

st.write("---")
# --- FILA DE TRABALHO (AVANÇO DE ETAPAS) ---
ativos = df[df['status'] != "Entregue"]
for i, row in ativos.iterrows():
    idx = df[df['id'] == row['id']].index
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** | Status: `{row['status']}`")
        
        # Lógica de Fluxo (Exemplo simplificado para teste)
        proxima = {"Lavagem": "Secagem", "Secagem": "Passadeira", "Passadeira": "Gaiola", "Gaiola": "Entregue"}
        if row['status'] in proxima:
            if st.button(f"➡️ Mover para {proxima[row['status']]}", key=f"btn_{row['id']}"):
                df.at[idx, 'status'] = proxima[row['status']]
                df.at[idx, 'detalhes'] += f" | [{agora()}] {proxima[row['status']]}"
                salvar(df); st.rerun()

if st.checkbox("📊 Ver Planilha"):
    st.dataframe(df)
