import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Lavo e Levo V13 - Etiquetas", layout="wide")

# --- CONEXÃO ---
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# Parâmetros
LISTA_ROUPAS = ["LENÇOL SOLTEIRO", "LENÇOL CASAL", "FRONHA", "TOALHA BANHO", "TOALHA ROSTO", "PISO", "COBERTOR", "EDREDOM"]

st.title("🧺 LAVANDERIA LAVO E LEVO - V13")

tab_op, tab_mot, tab_etiq = st.tabs(["🚀 Produção", "🚚 Digital Motorista", "🏷️ Etiquetas de Gaiola"])

# --- ABA 1: PRODUÇÃO (Inclusão de ID Único) ---
with tab_op:
    with st.expander("➕ Nova Entrada"):
        with st.form("entrada"):
            cli = st.text_input("Hospital:")
            peso = st.number_input("Peso (kg):", 0.1)
            if st.form_submit_button("GERAR LOTE"):
                t_ini = datetime.now().isoformat()
                # Gerando código único (Ex: 2024-001)
                cod_lote = f"{datetime.now().year}-{len(df)+1:03d}"
                novo = pd.DataFrame([{"id": cod_lote, "cli": cli.upper(), "p_in": peso, "status": "Lavagem", "itens": "", "tempos_json": f"Lavagem|{t_ini}"}])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df) ; st.rerun()

    # Fluxo de Trabalho (Mesma lógica V12)
    for i, row in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            st.write(f"**Lote: {row['id']}** | **{row['cli']}**")
            if row['status'] in ["Passadeira", "Dobragem"]:
                c1, c2, c3 = st.columns([2,1,1])
                it = c1.selectbox("Peça:", LISTA_ROUPAS, key=f"it{i}")
                qt = c2.number_input("Qtd:", 1, key=f"qt{i}")
                if c3.button("➕ Add", key=f"ad{i}"):
                    df.at[i, 'itens'] = str(row['itens']) + f"{it}:{qt}; "
                    conn.update(data=df) ; st.rerun()
            
            if st.button(f"➡️ Avançar {row['status']}", key=f"nx{i}"):
                fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Gaiola", "Entregue"]
                df.at[i, 'status'] = fluxo[fluxo.index(row['status']) + 1]
                conn.update(data=df) ; st.rerun()

# --- ABA 2: DIGITAL MOTORISTA (Conferência por Tela) ---
with tab_mot:
    st.subheader("📲 Conferência Digital (Uso Atual)")
    gaiolas = df[df['status'] == "Gaiola"]
    for _, r in gaiolas.iterrows():
        with st.container(border=True):
            st.write(f"**Lote: {r['id']}** | Cliente: {r['cli']}")
            st.info(f"📋 Relação: {r['itens']}")
            if st.button(f"Confirmar Saída {r['id']}", key=f"ok{r['id']}"):
                df.at[df['id'] == r['id'], 'status'] = "Entregue"
                conn.update(data=df) ; st.rerun()

# --- ABA 3: ETIQUETAS (Preparação p/ QR Code) ---
with tab_etiq:
    st.subheader("🖨️ Impressão de Etiquetas de Identificação")
    for _, r in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            c1.write(f"### LOTE: {r['id']}")
            c1.write(f"**CLIENTE: {r['cli']}**")
            c1.write(f"**PESO: {r['p_in']}kg**")
            c1.caption("Escaneie este código para rastreamento futuro.")
            
            # Aqui simulamos a etiqueta que será impressa
            if c2.button("🖨️ Imprimir Etiqueta", key=f"pr{r['id']}"):
                st.toast(f"Enviando Lote {r['id']} para impressora...")
                # No futuro, aqui geramos o QR Code real
