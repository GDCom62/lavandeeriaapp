import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração de Página e Estilo Industrial
st.set_page_config(page_title="Lavo e Levo V16 - Gestão", page_icon="🧺", layout="wide")

# --- CONEXÃO G-SHEETS ---
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# Lista Técnica Fixa
LISTA_ROUPAS = ["LENÇOL SOLTEIRO", "LENÇOL CASAL", "FRONHA", "TOALHA BANHO", "TOALHA ROSTO", "PISO", "COBERTOR", "EDREDOM"]

st.sidebar.title("🧺 CONTROLE LAVO E LEVO")
# Busca rápida via QR Code ou Digitação
busca = st.sidebar.text_input("🔍 BUSCA RÁPIDA (Lote ou Cliente):")

# MENU DE NAVEGAÇÃO
tab_op, tab_mot, tab_etiq, tab_hist = st.tabs(["🚀 Operação", "🚚 Motorista", "🏷️ Etiquetas", "📊 Histórico e Limpeza"])

# Filtragem para busca
if busca:
    df_ativos = df[(df['status'] != "Entregue") & (df['id'].str.contains(busca, case=False, na=False) | df['cli'].str.contains(busca, case=False, na=False))]
else:
    df_ativos = df[df['status'] != "Entregue"]

# --- ABA 1: OPERAÇÃO ---
with tab_op:
    with st.expander("➕ REGISTRAR ENTRADA (GERAR QR CODE)", expanded=not busca):
        with st.form("entrada"):
            cli = st.text_input("Hospital:")
            peso = st.number_input("Peso Entrada (kg):", 0.1)
            if st.form_submit_button("GERAR LOTE"):
                if cli:
                    cod_lote = f"{datetime.now().year}-{len(df)+1:03d}"
                    t_ini = datetime.now().isoformat()
                    novo = pd.DataFrame([{"id": cod_lote, "cli": cli.upper(), "p_in": peso, "p_out": 0.0, "status": "Lavagem", "itens": "", "tempos_json": f"Lavagem|{t_ini}"}])
                    df = pd.concat([df, novo], ignore_index=True)
                    conn.update(data=df) ; st.rerun()

    for i, row in df_ativos.iterrows():
        idx_real = df[df['id'] == row['id']].index
        with st.container(border=True):
            st.write(f"**Lote: {row['id']}** | **{row['cli']}**")
            
            if row['status'] in ["Passadeira", "Dobragem"]:
                c1, c2, c3 = st.columns(3)
                it = c1.selectbox("Peça:", LISTA_ROUPAS, key=f"it{row['id']}")
                qt = c2.number_input("Qtd:", 1, key=f"qt{row['id']}")
                if c3.button("➕ Add", key=f"ad{row['id']}"):
                    df.at[idx_real, 'itens'] = str(row['itens']) + f"{it}:{qt}; "
                    conn.update(data=df) ; st.rerun()
            
            if st.button(f"➡️ Avançar de {row['status']}", key=f"nx{row['id']}"):
                fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Gaiola", "Entregue"]
                df.at[idx_real, 'status'] = fluxo[fluxo.index(row['status']) + 1]
                conn.update(data=df) ; st.rerun()

# --- ABA 4: HISTÓRICO E LIMPEZA ---
with tab_hist:
    st.subheader("📜 Histórico de Lotes Entregues")
    df_entregue = df[df['status'] == "Entregue"]
    st.dataframe(df_entregue, use_container_width=True)
    
    st.write("---")
    if st.button("🚨 LIMPAR FILA (Apagar entregues da planilha)"):
        # Mantém apenas o que ainda está em processo
        df_limpo = df[df['status'] != "Entregue"]
        conn.update(data=df_limpo)
        st.success("A planilha foi limpa! Lotes entregues foram removidos.")
        st.rerun()
