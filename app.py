import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração de Página e Estilo Industrial
st.set_page_config(page_title="Lavo e Levo V15 - Rastreio", page_icon="🧺", layout="wide")

# --- CONEXÃO G-SHEETS ---
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# Lista Técnica Fixa
LISTA_ROUPAS = ["LENÇOL SOLTEIRO", "LENÇOL CASAL", "FRONHA", "TOALHA BANHO", "TOALHA ROSTO", "PISO", "COBERTOR", "EDREDOM"]

st.title("🧺 LAVANDERIA LAVO E LEVO - RASTREIO INTELIGENTE")

# Função para busca rápida via QR Code ou Digitação
busca = st.sidebar.text_input("🔍 BUSCA RÁPIDA (Escaneie ou Digite o Lote):")

tab_op, tab_mot, tab_etiq = st.tabs(["🚀 Produção Industrial", "📲 Digital Motorista", "🏷️ Etiquetas com QR Code"])

# --- FILTRAGEM POR BUSCA ---
if busca:
    df_exibicao = df[df['id'].str.contains(busca, case=False, na=False)]
    st.sidebar.warning(f"Exibindo apenas Lote: {busca}")
else:
    df_exibicao = df

# --- ABA 1: PRODUÇÃO ---
with tab_op:
    with st.expander("➕ REGISTRAR ENTRADA (GERAR QR CODE)", expanded=not busca):
        with st.form("entrada"):
            cli = st.text_input("Hospital:")
            peso = st.number_input("Peso Entrada (kg):", 0.1)
            if st.form_submit_button("GERAR LOTE E QR CODE"):
                if cli:
                    cod_lote = f"{datetime.now().year}-{len(df)+1:03d}"
                    t_ini = datetime.now().isoformat()
                    novo = pd.DataFrame([{"id": cod_lote, "cli": cli.upper(), "p_in": peso, "status": "Lavagem", "itens": "", "tempos_json": f"Lavagem|{t_ini}"}])
                    df = pd.concat([df, novo], ignore_index=True)
                    conn.update(data=df) ; st.rerun()

    # Fila de Trabalho (Dinâmica com a busca)
    for i, row in df_exibicao[df_exibicao['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            st.write(f"**Lote: {row['id']}** | **{row['cli']}**")
            
            if row['status'] in ["Passadeira", "Dobragem"]:
                c1, c2, c3 = st.columns(3)
                it = c1.selectbox("Peça:", LISTA_ROUPAS, key=f"it{i}")
                qt = c2.number_input("Qtd:", 1, key=f"qt{i}")
                if c3.button("➕", key=f"ad{i}"):
                    df.at[i, 'itens'] = str(row['itens']) + f"{it}:{qt}; "
                    conn.update(data=df) ; st.rerun()
            
            if st.button(f"➡️ Mover para {row['status']}...", key=f"nx{i}"):
                fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Gaiola", "Entregue"]
                df.at[i, 'status'] = fluxo[fluxo.index(row['status']) + 1]
                conn.update(data=df) ; st.rerun()

# --- ABA 2: MOTORISTA ---
with tab_mot:
    for _, r in df_exibicao[df_exibicao['status'] == "Gaiola"].iterrows():
        with st.container(border=True):
            st.write(f"**Lote: {r['id']}** | Cliente: {r['cli']}")
            st.info(f"📋 Itens: {r['itens']}")
            if st.button(f"Confirmar Saída #{r['id']}", key=f"mot{r['id']}"):
                df.at[df['id'] == r['id'], 'status'] = "Entregue"
                conn.update(data=df) ; st.rerun()

# --- ABA 3: ETIQUETAS ---
with tab_etiq:
    for _, r in df_exibicao[df_exibicao['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            col_txt, col_qr = st.columns([2, 1])
            col_txt.write(f"### LOTE: {r['id']}")
            col_txt.write(f"**HOSPITAL: {r['cli']}**")
            col_txt.write(f"**PESO: {r['p_in']}kg**")
            
            # QR Code aponta para o ID do lote
            qr_url = f"https://api.qrserver.com{r['id']}"
            col_qr.image(qr_url, caption=f"QR do Lote {r['id']}")
