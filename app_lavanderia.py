import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

st.set_page_config(page_title="Lavo e Levo V8 - Inteligência", layout="wide")

# --- BANCO DE DADOS ---
ARQUIVO_LOCAL = "dados_lavanderia.csv"
def carregar_dados():
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="0")
        if not df.empty: return df, conn
    except: pass
    if os.path.exists(ARQUIVO_LOCAL): return pd.read_csv(ARQUIVO_LOCAL), None
    cols = ["id", "cli", "p_in", "status", "resp", "detalhes", "tempos_json", "maq"]
    return pd.DataFrame(columns=cols), None

df, conexao = carregar_dados()

# --- CONFIGURAÇÃO DE RENDIMENTO (PROJETADO) ---
# Quantos minutos por KG em cada máquina (Exemplo ajustável)
MIN_POR_KG_LAVAR = 2.0  # 20kg = 40min projetado
MIN_POR_KG_SECAR = 3.0  # 20kg = 60min projetado

def calcular_projetado(peso, etapa):
    if etapa == "Lavagem": return int(peso * MIN_POR_KG_LAVAR)
    if etapa == "Secagem": return int(peso * MIN_POR_KG_SECAR)
    return 30 # Padrão para dobras/passagem

st.title("🧺 LAVANDERIA LAVO E LEVO - V8")
st.caption(f"Foco: Projetado vs Realizado (Peso {MIN_POR_KG_LAVAR}min/kg Lavar | {MIN_POR_KG_SECAR}min/kg Secar)")

# --- 1. ENTRADA ---
with st.expander("➕ 1. ENTRADA HOSPITALAR", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Hospital:")
        p_in = c2.number_input("Peso (kg):", 0.0)
        maq = c1.selectbox("Lavadora:", ["LAV-01 (20kg)", "LAV-02 (50kg)", "Industrial-01 (100kg)"])
        resp = c2.text_input("Responsável:")
        if st.form_submit_button("INICIAR"):
            if cli and resp:
                t_inicio = datetime.now().isoformat()
                novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": p_in, "status": "Lavagem", 
                                      "resp": resp, "maq": maq, "tempos_json": f"Lavagem|{t_inicio}"}])
                df = pd.concat([df, novo], ignore_index=True)
                if conexao: conexao.update(data=df) ; st.cache_data.clear()
                else: df.to_csv(ARQUIVO_LOCAL, index=False)
                st.rerun()

# --- 2. OPERAÇÃO ---
st.write("---")
for i, row in df[df['status'] != "Entregue"].iterrows():
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg na {row['maq']})")
        
        fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Entregue"]
        idx = fluxo.index(row['status'])
        
        c1, c2 = st.columns(2)
        proxima = c1.selectbox("Próxima Etapa:", fluxo[idx+1:], key=f"s{i}")
        n_resp = c2.text_input("Responsável:", key=f"r{i}")
        
        if st.button("✅ Confirmar Mudança", key=f"b{i}"):
            if n_resp:
                t_agora = datetime.now().isoformat()
                df.at[i, 'status'], df.at[i, 'resp'] = proxima, n_resp
                df.at[i, 'tempos_json'] = str(row['tempos_json']) + f";{proxima}|{t_agora}"
                if conexao: conexao.update(data=df) ; st.cache_data.clear()
                else: df.to_csv(ARQUIVO_LOCAL, index=False)
                st.rerun()

# --- 3. RELATÓRIO: PROJETADO VS REALIZADO ---
st.write("---")
if st.checkbox("📊 Auditoria: Projetado vs Realizado"):
    for idx, r in df.iterrows():
        with st.expander(f"Lote {r['id']} - {r['cli']} ({r['p_in']}kg)"):
            etapas = str(r['tempos_json']).split(";")
            for j in range(len(etapas)-1):
                n_e, t1 = etapas[j].split("|")
                _, t2 = etapas[j+1].split("|")
                
                real = int((datetime.fromisoformat(t2) - datetime.fromisoformat(t1)).total_seconds() / 60)
                proj = calcular_projetado(r['p_in'], n_e)
                
                # Alerta visual de produtividade
                if real > proj:
                    st.error(f"❌ **{n_e}**: Real {real}min | Projetado {proj}min (**ATRASO**)")
                else:
                    st.success(f"✅ **{n_e}**: Real {real}min | Projetado {proj}min (**EFICIENTE**)")
