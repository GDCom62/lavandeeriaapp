import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração de Página e Estilo Industrial
st.set_page_config(page_title="Lavo e Levo V14 - QR Code", page_icon="🧺", layout="wide")

# --- CONEXÃO G-SHEETS ---
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# Lista Técnica Fixa
LISTA_ROUPAS = ["LENÇOL SOLTEIRO", "LENÇOL CASAL", "FRONHA", "TOALHA BANHO", "TOALHA ROSTO", "PISO", "COBERTOR", "EDREDOM"]

st.title("🧺 LAVANDERIA LAVO E LEVO - GESTÃO COM QR CODE")

tab_op, tab_mot, tab_etiq = st.tabs(["🚀 Produção Industrial", "📲 Digital Motorista", "🏷️ Etiquetas com QR Code"])

# --- ABA 1: PRODUÇÃO (Criação de Lote com ID Único) ---
with tab_op:
    with st.expander("➕ REGISTRAR ENTRADA (GERAR QR CODE)", expanded=True):
        with st.form("entrada"):
            cli = st.text_input("Hospital:")
            peso = st.number_input("Peso Entrada (kg):", 0.1)
            if st.form_submit_button("GERAR LOTE E QR CODE"):
                if cli:
                    t_ini = datetime.now().isoformat()
                    # ID Único do Lote (Ex: 2024-001)
                    cod_lote = f"{datetime.now().year}-{len(df)+1:03d}"
                    novo = pd.DataFrame([{"id": cod_lote, "cli": cli.upper(), "p_in": peso, "status": "Lavagem", "itens": "", "tempos_json": f"Lavagem|{t_ini}"}])
                    df = pd.concat([df, novo], ignore_index=True)
                    conn.update(data=df) ; st.rerun()

    # Fluxo de Trabalho
    for i, row in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            st.write(f"**Lote: {row['id']}** | **{row['cli']}**")
            
            # Contagem Técnica
            if row['status'] in ["Passadeira", "Dobragem"]:
                c1, c2, c3 = st.columns([3,2,1])
                it = c1.selectbox("Peça:", LISTA_ROUPAS, key=f"it{i}")
                qt = c2.number_input("Qtd:", 1, key=f"qt{i}")
                if c3.button("➕", key=f"ad{i}"):
                    df.at[i, 'itens'] = str(row['itens']) + f"{it}:{qt}; "
                    conn.update(data=df) ; st.rerun()
            
            # Botão de Avanço
            if st.button(f"➡️ Mover para {row['status']}...", key=f"nx{i}"):
                fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Gaiola", "Entregue"]
                df.at[i, 'status'] = fluxo[fluxo.index(row['status']) + 1]
                conn.commit() ; conn.update(data=df) ; st.rerun()

# --- ABA 2: DIGITAL MOTORISTA (Uso Atual) ---
with tab_mot:
    st.subheader("📲 Conferência Digital")
    for _, r in df[df['status'] == "Gaiola"].iterrows():
        with st.container(border=True):
            st.write(f"**Lote: {r['id']}** | Cliente: {r['cli']}")
            st.warning(f"📦 Conferir na Gaiola: {r['itens']}")
            if st.button(f"Confirmar Saída #{r['id']}", key=f"mot{r['id']}"):
                df.at[df['id'] == r['id'], 'status'] = "Entregue"
                conn.update(data=df) ; st.rerun()

# --- ABA 3: ETIQUETAS (Visualização do QR Code) ---
with tab_etiq:
    st.subheader("🖨️ Etiquetas de Identificação de Lote")
    for _, r in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            col_txt, col_qr = st.columns([2, 1])
            with col_txt:
                st.write(f"### LOTE: {r['id']}")
                st.write(f"**HOSPITAL: {r['cli']}**")
                st.write(f"**PESO: {r['p_in']}kg**")
                st.caption(f"Status Atual: {r['status']}")
            
            with col_qr:
                # Gera link do QR Code para busca rápida (exemplo aponta para o próprio lote)
                qr_data = f"Lote:{r['id']}|Cliente:{r['cli']}"
                st.image(f"https://api.qrserver.com{qr_data}", caption=f"QR Code do Lote {r['id']}")
            
            if st.button(f"🖨️ Imprimir Etiqueta {r['id']}", key=f"pr{r['id']}"):
                st.info("Pressione Ctrl + P para imprimir esta tela como etiqueta.")
