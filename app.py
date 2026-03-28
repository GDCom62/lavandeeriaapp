import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração de Layout e Ícone
st.set_page_config(page_title="Lavo e Levo - Controle Total", page_icon="🧺", layout="wide")

# Conexão com Google Sheets (Secrets configurados no Streamlit Cloud)
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# Inicializa colunas se a planilha estiver vazia
cols = ["id", "cli", "p_in", "p_out", "tipo", "status", "detalhes_processo", "itens_contagem", "gaiola", "mot", "h_entrada"]
if df is None or df.empty:
    df = pd.DataFrame(columns=cols)

def agora(): return datetime.now().strftime("%H:%M")

def salvar(novo_df):
    conn.update(data=novo_df)
    st.cache_data.clear()

st.title("🧺 LAVANDERIA LAVO E LEVO - GESTÃO INDUSTRIAL")

# --- 1. RECEBIMENTO E LAVAGEM ---
with st.expander("➕ 1. RECEBIMENTO E ENTRADA NA MÁQUINA", expanded=True):
    with st.form("form_lavagem", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente:")
        peso = c2.number_input("Peso Bruto (kg):", 0.1)
        tipo = c1.selectbox("Processo:", ["Novo", "Relave"])
        maq = c2.selectbox("Máquina de Lavar:", ["LAV-01", "LAV-02", "Industrial-01"])
        resp = c1.text_input("Colaborador (Recebe e Põe na Máquina):")
        
        if st.form_submit_button("REGISTRAR E INICIAR LAVAGEM"):
            if cli and resp:
                h = agora()
                log = f"[{h}] Lavagem: {resp} na {maq}"
                novo = pd.DataFrame([{
                    "id": len(df)+1, "cli": cli.upper(), "p_in": peso, "p_out": 0.0,
                    "tipo": tipo, "status": "Lavagem", "detalhes_processo": log,
                    "itens_contagem": "", "gaiola": "", "mot": "", "h_entrada": h
                }])
                df = pd.concat([df, novo], ignore_index=True)
                salvar(df) ; st.rerun()

st.write("---")
st.subheader("📋 Fluxo de Produção em Tempo Real")

ativos = df[df['status'] != "Entregue"]

for i, row in ativos.iterrows():
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** | Status: `{row['status']}`")
        st.caption(f"Histórico: {row['detalhes_processo']}")

        # --- ETAPA 2: RETIRADA DA LAVADORA E ENVIO P/ SECADORA ---
        if row['status'] == "Lavagem":
            r2 = st.text_input("Colaborador (Retira Lavadora e Leva Secagem):", key=f"r2_{i}")
            if st.button("➡️ Entregar na Secadora", key=f"b2_{i}"):
                if r2:
                    df.at[i, 'status'] = "Secagem"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Levado p/ Secar por: {r2}"
                    salvar(df) ; st.rerun()

        # --- ETAPA 3: OPERAÇÃO SECADORA E RETIRADA ---
        elif row['status'] == "Secagem":
            c3, c4 = st.columns(2)
            r3 = c3.text_input("Colaborador (Põe e Tira da Secadora):", key=f"r3_{i}")
            m_s = c4.selectbox("Máquina Secar:", ["SEC-01", "SEC-02"], key=f"ms_{i}")
            
            col_p, col_d = st.columns(2)
            if col_p.button("👔 Ir para Passadeira", key=f"bp_{i}"):
                if r3:
                    df.at[i, 'status'] = "Passadeira"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Secagem: {r3} na {m_s}. Destino: Passadeira"
                    salvar(df) ; st.rerun()
            if col_d.button("📦 Ir para Dobragem", key=f"bd_{i}"):
                if r3:
                    df.at[i, 'status'] = "Dobragem"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Secagem: {r3} na {m_s}. Destino: Dobragem"
                    salvar(df) ; st.rerun()

        # --- ETAPA 4/5: PROCESSAMENTO E CONTAGEM ---
        elif row['status'] in ["Passadeira", "Dobragem"]:
            r4 = st.text_input("Colaborador (Processamento e Contagem):", key=f"r4_{i}")
            
            st.write("**Relação de Peças:**")
            t_p = st.text_input("Tipo (ex: Lençol):", key=f"tp_{i}")
            q_p = st.number_input("Qtd:", 1, key=f"qp_{i}")
            if st.button("➕ Add Item", key=f"ba_{i}"):
                df.at[i, 'itens_contagem'] += f"{t_p}({q_p}un); "
                salvar(df) ; st.rerun()
            
            st.info(f"Contagem Atual: {row['itens_contagem']}")
            
            if st.button("🎁 Finalizar e Empacotar", key=f"bf_{i}"):
                if r4:
                    df.at[i, 'status'] = "Gaiola"
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Acabamento: {r4}"
                    salvar(df) ; st.rerun()

        # --- ETAPA 6/7: GAIOLA E MOTORISTA ---
        elif row['status'] == "Gaiola":
            st.subheader("⚖️ Pesagem Final e Expedição")
            p_out = st.number_input("Peso Saída (kg):", 0.1, key=f"po_{i}")
            gaiola = st.text_input("Nº da Gaiola:", key=f"g_{i}")
            motorista = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"mot_{i}")
            
            if p_out > 0:
                perda = ((row['p_in'] - p_out) / row['p_in']) * 100
                if perda > 5.0: st.error(f"⚠️ Alerta de Perda: {perda:.1f}%")
                else: st.success(f"✅ Perda dentro do limite: {perda:.1f}%")

            if st.button("🚚 LIBERAR PARA MOTORISTA", key=f"bl_{i}"):
                if p_out > 0:
                    df.at[i, 'status'], df.at[i, 'p_out'] = "Entregue", p_out
                    df.at[i, 'mot'], df.at[i, 'gaiola'] = motorista, gaiola
                    df.at[i, 'detalhes_processo'] += f" | [{agora()}] Expedido na Gaiola {gaiola} por {motorista}"
                    salvar(df) ; st.rerun()

# --- RELATÓRIO DE AUDITORIA ---
st.write("---")
if st.checkbox("📊 Ver Relatório de Produtividade"):
    st.dataframe(df)
