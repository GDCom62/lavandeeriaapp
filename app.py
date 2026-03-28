import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração de Página
st.set_page_config(page_title="Lavo e Levo Pro", page_icon="🧺", layout="wide")

# Título fixo para saber que o código novo carregou
st.title("🧺 LAVANDERIA LAVO E LEVO - V3")

# Conexão com Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl=0)
except Exception as e:
    st.error("Erro na conexão com a planilha. Verifique os Secrets.")
    st.stop()

# Garantir colunas mínimas para não dar erro de "Index"
colunas_necessarias = ["id", "cli", "p_in", "p_out", "tipo", "status", "resp", "itens", "gaiola", "mot", "h_in"]
if df is None or df.empty:
    df = pd.DataFrame(columns=colunas_necessarias)
else:
    # Garante que todas as colunas existem
    for col in colunas_necessarias:
        if col not in df.columns:
            df[col] = ""

# Função Salvar
def salvar(dados):
    conn.update(data=dados)
    st.cache_data.clear()

# --- 1. ENTRADA ---
with st.expander("➕ NOVO RECEBIMENTO", expanded=True):
    with st.form("form_in", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente:")
        peso_e = c2.number_input("Peso Entrada (kg):", 0.0)
        equipe = c1.text_input("Sua Equipe (Lavagem):")
        tipo_p = c2.selectbox("Processo:", ["Novo", "Relave"])
        if st.form_submit_button("REGISTRAR"):
            if cliente and equipe:
                novo = pd.DataFrame([{
                    "id": len(df) + 1, "cli": cliente.upper(), "p_in": peso_e, "p_out": 0.0,
                    "tipo": tipo_p, "status": "Lavagem", "resp": equipe, "itens": "", 
                    "gaiola": "", "mot": "", "h_in": datetime.now().strftime("%H:%M")
                }])
                df = pd.concat([df, novo], ignore_index=True)
                salvar(df)
                st.rerun()

st.write("---")

# --- 2. FILA ATIVA ---
st.subheader("📋 Fila de Trabalho")
ativos = df[df['status'] != "Entregue"]

for i, row in ativos.iterrows():
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** | Status: `{row['status']}`")
        
        # Lógica de Etapas detalhada
        if row['status'] == "Lavagem":
            r2 = st.text_input("Equipe p/ Secagem:", key=f"r2_{row['id']}")
            if st.button("➡️ Para Secadora", key=f"b2_{row['id']}"):
                df.at[i, 'status'], df.at[i, 'resp'] = "Secagem", r2
                salvar(df) ; st.rerun()

        elif row['status'] == "Secagem":
            r3 = st.text_input("Equipe Secadora:", key=f"r3_{row['id']}")
            c_p, c_d = st.columns(2)
            if c_p.button("👔 Passadeira", key=f"bp_{row['id']}"):
                df.at[i, 'status'], df.at[i, 'resp'] = "Passadeira", r3
                salvar(df) ; st.rerun()
            if c_d.button("📦 Dobragem", key=f"bd_{row['id']}"):
                df.at[i, 'status'], df.at[i, 'resp'] = "Dobragem", r3
                salvar(df) ; st.rerun()

        elif row['status'] in ["Passadeira", "Dobragem"]:
            r4 = st.text_input("Equipe Contagem:", key=f"r4_{row['id']}")
            if st.button("🔢 Iniciar Contagem", key=f"bc_{row['id']}"):
                df.at[i, 'status'], df.at[i, 'resp'] = "Contagem", r4
                salvar(df) ; st.rerun()

        elif row['status'] == "Contagem":
            st.write(f"Contagem: {row['itens']}")
            t_it = st.text_input("Item:", key=f"ti_{row['id']}")
            q_it = st.number_input("Qtd:", 1, key=f"qi_{row['id']}")
            if st.button("➕ Add Item", key=f"add_{row['id']}"):
                df.at[i, 'itens'] = f"{row['itens']}, {t_it}({q_it}un)"
                salvar(df) ; st.rerun()
            if st.button("⚖️ Finalizar p/ Gaiola", key=f"bg_{row['id']}"):
                df.at[i, 'status'] = "Gaiola"
                salvar(df) ; st.rerun()

        elif row['status'] == "Gaiola":
            p_s = st.number_input("Peso Saída:", 0.0, key=f"ps_{row['id']}")
            mot = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"mot_{row['id']}")
            if st.button("🚚 LIBERAR ENTREGA", key=f"ble_{row['id']}"):
                df.at[i, 'p_out'], df.at[i, 'status'], df.at[i, 'mot'] = p_s, "Entregue", mot
                salvar(df) ; st.rerun()

if st.checkbox("📊 Ver Planilha"):
    st.dataframe(df)
