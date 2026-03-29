import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração Profissional
st.set_page_config(page_title="Lavo e Levo V12 - Auditoria", layout="wide")

# --- CONEXÃO G-SHEETS ---
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# --- PARÂMETROS CONTRATUAIS ---
CUSTO_ALVO_KG = 1.35  # R$ 0,45 + R$ 0,30 + R$ 0,60
MIN_PROJETADO_KG = 3.0 # Média de 3 min por kg para lavagem+secagem
LISTA_ROUPAS = ["LENÇOL SOLTEIRO", "LENÇOL CASAL", "FRONHA", "TOALHA BANHO", "TOALHA ROSTO", "PISO", "COBERTOR", "EDREDOM"]

st.title("🧺 LAVANDERIA LAVO E LEVO - V12 (GESTÃO E LOGÍSTICA)")

tab_op, tab_mot, tab_fin = st.tabs(["🚀 Produção Industrial", "🚚 Conferência Motorista", "💰 Auditoria de Custos"])

# --- ABA 1: PRODUÇÃO ---
with tab_op:
    with st.expander("➕ Nova Entrada de Hospital"):
        with st.form("entrada"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Hospital:")
            peso = c2.number_input("Peso (kg):", 0.1)
            if st.form_submit_button("INICIAR"):
                t_ini = datetime.now().isoformat()
                novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": peso, "p_out": 0.0, 
                                      "status": "Lavagem", "itens": "", "tempos_json": f"Lavagem|{t_ini}"}])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df) ; st.rerun()

    # Fila de Trabalho
    for i, row in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            col_a, col_b = st.columns([2, 1])
            col_a.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg)")
            
            # Etapa de Contagem (Passadeira/Dobra)
            if row['status'] in ["Passadeira", "Dobragem"]:
                st.write("**📦 Contagem Técnica para o Motorista:**")
                c1, c2, c3 = st.columns([2, 1, 1])
                item_sel = c1.selectbox("Tipo de Roupa:", LISTA_ROUPAS, key=f"sel_{i}")
                qtd_sel = c2.number_input("Qtd:", 1, key=f"qtd_{i}")
                if c3.button("➕ Add", key=f"add_{i}"):
                    df.at[i, 'itens'] = str(row['itens']) + f"{item_sel}:{qtd_sel}; "
                    conn.update(data=df) ; st.rerun()
                st.caption(f"Lista Atual: {row['itens']}")

            # Avançar Etapa
            if col_b.button(f"➡️ Avançar de {row['status']}", key=f"next_{i}"):
                fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Gaiola", "Entregue"]
                novo_st = fluxo[fluxo.index(row['status']) + 1] if row['status'] in fluxo else "Entregue"
                t_fim = datetime.now().isoformat()
                df.at[i, 'status'] = novo_st
                df.at[i, 'tempos_json'] = str(row['tempos_json']) + f";{novo_st}|{t_fim}"
                conn.update(data=df) ; st.rerun()

# --- ABA 2: MOTORISTA (CONFERÊNCIA) ---
with tab_mot:
    st.subheader("🚚 Romaneio de Carga para Motoristas")
    lotes_prontos = df[df['status'] == "Gaiola"]
    if lotes_prontos.empty:
        st.info("Nenhuma gaiola aguardando motorista.")
    for _, r in lotes_prontos.iterrows():
        with st.container(border=True):
            st.write(f"**CLIENTE: {r['cli']}** | Lote: #{r['id']}")
            st.warning(f"**CONFERIR NA GAIOLA:** {r['itens']}")
            if st.button(f"Confirmar Carregamento #{r['id']}", key=f"mot_{r['id']}"):
                df.at[df['id'] == r['id'], 'status'] = "Entregue"
                conn.update(data=df) ; st.rerun()

# --- ABA 3: AUDITORIA FINANCEIRA ---
with tab_fin:
    st.subheader("⚠️ Alerta de Desvio de Custo (Energia)")
    for _, r in df.iterrows():
        etapas = str(r['tempos_json']).split(";")
        if len(etapas) > 1:
            t1 = datetime.fromisoformat(etapas[0].split("|")[1])
            t2 = datetime.fromisoformat(etapas[-1].split("|")[1])
            tempo_real = (t2 - t1).total_seconds() / 60
            tempo_proj = r['p_in'] * MIN_PROJETADO_KG
            
            custo_real = r['p_in'] * CUSTO_ALVO_KG
            desvio = (tempo_real / tempo_proj) if tempo_proj > 0 else 1
            
            if desvio > 1.2: # 20% de atraso = Alerta de prejuízo
                st.error(f"🔴 Lote {r['id']} ({r['cli']}): Prejuízo Operacional! Tempo Real: {tempo_real:.0f}min (Esperado: {tempo_proj:.0f}min). Custo de Insumos excedido.")
            else:
                st.success(f"🟢 Lote {r['id']} ({r['cli']}): Custo dentro do contrato (R$ {CUSTO_ALVO_KG}/kg).")
