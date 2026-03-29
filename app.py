import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO DE APARÊNCIA (DESIGN INDUSTRIAL) ---
st.set_page_config(page_title="Lavo e Levo V21", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        height: 3.5em;
        background-color: #007bff;
        color: white;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #0056b3; border: 2px solid white; }
    .css-1r6slb0 { border: 1px solid #dee2e6; border-radius: 15px; padding: 20px; background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO COM BANCO DE DADOS ---
from streamlit_gsheets import GSheetsConnection

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
    st.sidebar.success("✅ BANCO DE DADOS CONECTADO")
except Exception as e:
    st.error("❌ ERRO DE ACESSO (404)")
    st.info("💡 AÇÃO NECESSÁRIA: No Google Sheets, clique em COMPARTILHAR e adicione o e-mail do seu App como EDITOR.")
    st.stop()

# Cabeçalhos e Fluxo
cols_f = ["id", "cli", "p_in", "status", "resp", "detalhes", "itens", "h_entrada"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols_f)

FLUXO = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]

st.title("🧺 LAVANDERIA LAVO E LEVO - V21")
st.write("---")

# --- INTERFACE DE OPERAÇÃO ---
col_ent, col_fila = st.columns([1, 2])

with col_ent:
    st.subheader("➕ Novo Recebimento")
    with st.form("nova_entrada", clear_on_submit=True):
        cliente = st.text_input("Hospital / Cliente:")
        peso_in = st.number_input("Peso Entrada (kg):", 0.1)
        equipe = st.text_input("Responsável Lavagem:")
        if st.form_submit_button("REGISTRAR LOTE"):
            if cliente and equipe:
                lote_id = f"{datetime.now().year}-{len(df)+1:03d}"
                h = datetime.now().strftime("%H:%M")
                novo = pd.DataFrame([{
                    "id": lote_id, "cli": cliente.upper(), "p_in": peso_in, "status": "Lavagem",
                    "resp": equipe, "detalhes": f"[{h}] Lavagem: {equipe}", "itens": "", "h_entrada": h
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df)
                st.rerun()

with col_fila:
    st.subheader("📋 Fila de Trabalho Ativa")
    ativos = df[df['status'] != "Entregue"]
    
    for i, row in ativos.iterrows():
        idx = df[df['id'] == row['id']].index
        with st.container():
            st.markdown(f"### {row['cli']} | Lote: {row['id']}")
            c1, c2, c3 = st.columns([2, 1, 1])
            
            c1.write(f"**Etapa:** `{row['status']}` | **Peso:** {row['p_in']}kg")
            c1.caption(f"🕒 Entrada: {row['h_entrada']} | Responsável: {row['resp']}")
            
            # Botão de Avançar com Cor Especial
            if c2.button(f"➡️ AVANÇAR", key=f"av_{row['id']}"):
                proxima = FLUXO[FLUXO.index(row['status']) + 1]
                df.at[idx, 'status'] = proxima
                df.at[idx, 'detalhes'] += f" | [{datetime.now().strftime('%H:%M')}] {proxima}"
                conn.update(data=df)
                st.rerun()

            # Opção de Detalhes
            if c3.button("📝 ITENS", key=f"it_{row['id']}"):
                st.toast(f"Abrindo contagem do Lote {row['id']}")
