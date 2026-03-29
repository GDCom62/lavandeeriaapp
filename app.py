import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração de Página e Estilo
st.set_page_config(page_title="Lavo e Levo V5", page_icon="🧺", layout="wide")

# --- FUNÇÕES DE SALVAMENTO (DETECTOR DE AMBIENTE) ---
ARQUIVO_LOCAL = "dados_lavanderia.csv"

def carregar_dados():
    # Tenta carregar do Google Sheets (Nuvem)
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="0")
        if not df.empty: return df, conn
    except: pass
    
    # Se falhar ou estiver no PC, carrega arquivo local
    if os.path.exists(ARQUIVO_LOCAL):
        return pd.read_csv(ARQUIVO_LOCAL), None
    
    cols = ["id", "cli", "p_in", "p_out", "status", "resp", "detalhes", "itens", "mot", "gaiola"]
    return pd.DataFrame(columns=cols), None

def salvar_dados(df_atual, conn):
    if conn: # Se estiver na nuvem
        conn.update(data=df_atual)
        st.cache_data.clear()
    else: # Se estiver no PC
        df_atual.to_csv(ARQUIVO_LOCAL, index=False)

# Inicialização
df, conexao = carregar_dados()
def agora(): return datetime.now().strftime("%H:%M")

st.title("🧺 LAVANDERIA LAVO E LEVO - V5")
if conexao: st.success("☁️ Modo: NUVEM (Google Sheets)")
else: st.info("💻 Modo: LOCAL (Arquivo no PC)")

# --- 1. RECEBIMENTO E LAVAGEM ---
with st.expander("➕ 1. RECEBIMENTO / LAVAGEM", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente:")
        p_in = c2.number_input("Peso Entrada (kg):", 0.0)
        maq = c1.selectbox("Máquina Lavar:", ["LAV-01", "LAV-02", "Industrial-01"])
        resp = c2.text_input("Responsável Carga:")
        if st.form_submit_button("REGISTRAR"):
            if cli and resp:
                log = f"[{agora()}] Lavagem: {resp} ({maq})"
                novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0, 
                                      "status": "Lavagem", "resp": resp, "detalhes": log, "itens": "", "mot": "", "gaiola": ""}])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_dados(df, conexao) ; st.rerun()

st.write("---")
# --- FILA DE TRABALHO (AS 7 ETAPAS) ---
ativos = df[df['status'] != "Entregue"]
for i, row in ativos.iterrows():
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** | Status: `{row['status']}`")
        st.caption(f"📜 Histórico: {row['detalhes']}")
        
        # 2. LAVAGEM -> TRANSPORTE -> SECAGEM
        if row['status'] == "Lavagem":
            r2 = st.text_input("Quem leva p/ Secar?", key=f"r2_{i}")
            if st.button("➡️ Enviar para Secadora", key=f"b2_{i}"):
                df.at[i, 'status'], df.at[i, 'detalhes'] = "Secagem", row['detalhes'] + f" | [{agora()}] Transp: {r2}"
                salvar_dados(df, conexao) ; st.rerun()

        # 3. SECAGEM -> ESCOLHA DESTINO
        elif row['status'] == "Secagem":
            r3 = st.text_input("Quem opera Secadora?", key=f"r3_{i}")
            maq_s = st.selectbox("Máquina Secar:", ["SEC-01", "SEC-02"], key=f"ms_{i}")
            c1, c2 = st.columns(2)
            if c1.button("👔 Passadeira", key=f"bp_{i}"):
                df.at[i, 'status'], df.at[i, 'detalhes'] = "Passadeira", row['detalhes'] + f" | [{agora()}] Secagem: {r3} ({maq_s})"
                salvar_dados(df, conexao) ; st.rerun()
            if c2.button("📦 Dobragem", key=f"bd_{i}"):
                df.at[i, 'status'], df.at[i, 'detalhes'] = "Dobragem", row['detalhes'] + f" | [{agora()}] Secagem: {r3} ({maq_s})"
                salvar_dados(df, conexao) ; st.rerun()

        # 4/5. ACABAMENTO -> CONTAGEM
        elif row['status'] in ["Passadeira", "Dobragem"]:
            r4 = st.text_input("Quem faz contagem?", key=f"r4_{i}")
            t_p = st.text_input("Item:", key=f"tp_{i}")
            q_p = st.number_input("Qtd:", 1, key=f"qp_{i}")
            if st.button("➕ Add Item", key=f"ba_{i}"):
                df.at[i, 'itens'] = str(row['itens']) + f"{t_p}({q_p}); "
                salvar_dados(df, conexao) ; st.rerun()
            if st.button("🎁 Finalizar p/ Gaiola", key=f"bf_{i}"):
                df.at[i, 'status'], df.at[i, 'detalhes'] = "Gaiola", row['detalhes'] + f" | [{agora()}] Contagem: {r4}"
                salvar_dados(df, conexao) ; st.rerun()

        # 6/7. GAIOLA -> MOTORISTA
        elif row['status'] == "Gaiola":
            p_out = st.number_input("Peso Saída:", 0.0, key=f"po_{i}")
            gai = st.text_input("Nº Gaiola:", key=f"g_{i}")
            mot = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"m_{i}")
            if st.button("🚚 LIBERAR", key=f"be_{i}"):
                if p_out > 0:
                    df.at[i, 'status'], df.at[i, 'p_out'], df.at[i, 'mot'], df.at[i, 'gaiola'] = "Entregue", p_out, mot, gai
                    salvar_dados(df, conexao) ; st.rerun()
