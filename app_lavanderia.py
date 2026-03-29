import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="Lavo e Levo V7 - Produtividade", page_icon="🧺", layout="wide")

# --- BANCO DE DADOS (LOCAL/NUVEM) ---
ARQUIVO_LOCAL = "dados_lavanderia.csv"

def carregar_dados():
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="0")
        if not df.empty: return df, conn
    except: pass
    if os.path.exists(ARQUIVO_LOCAL):
        return pd.read_csv(ARQUIVO_LOCAL), None
    cols = ["id", "cli", "p_in", "p_out", "status", "resp", "detalhes", "itens", "h_entrada", "tempos_json"]
    return pd.DataFrame(columns=cols), None

def salvar_dados(df_atual, conn):
    if conn:
        conn.update(data=df_atual)
        st.cache_data.clear()
    else:
        df_atual.to_csv(ARQUIVO_LOCAL, index=False)

df, conexao = carregar_dados()

# Funções de Tempo
def agora(): return datetime.now().strftime("%H:%M")
def agora_bruto(): return datetime.now().isoformat()

st.title("🧺 LAVANDERIA LAVO E LEVO - V7")
st.caption(f"Status: {'☁️ NUVEM' if conexao else '💻 LOCAL'} | Foco: Produtividade e Cronometragem")

# --- 1. ENTRADA (LAVAGEM) ---
with st.expander("➕ 1. RECEBIMENTO HOSPITALAR / LAVAGEM", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Hospital/Cliente:")
        p_in = c2.number_input("Peso Entrada (kg):", 0.0)
        resp = c1.text_input("Responsável Carga:")
        if st.form_submit_button("INICIAR PROCESSO"):
            if cli and resp:
                t_inicio = agora_bruto()
                log = f"[{agora()}] Lavagem iniciada por {resp}"
                # tempos_json guarda o início de cada etapa para cálculo posterior
                novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0, 
                                      "status": "Lavagem", "resp": resp, "detalhes": log, "itens": "", 
                                      "h_entrada": agora(), "tempos_json": f"Lavagem|{t_inicio}"}])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_dados(df, conexao) ; st.rerun()

st.write("---")

# --- 2. FILA DE OPERAÇÃO ---
ativos = df[df['status'] != "Entregue"]

for i, row in ativos.iterrows():
    with st.container(border=True):
        col_info, col_acao = st.columns([2, 1])
        
        with col_info:
            st.write(f"**Lote #{row['id']} - {row['cli']}**")
            st.caption(f"📍 Etapa: `{row['status']}` | Responsável: {row['resp']}")
            st.caption(f"📜 Histórico: {row['detalhes']}")

        with col_acao:
            fluxo = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]
            idx = fluxo.index(row['status']) if row['status'] in fluxo else 0
            
            if idx < len(fluxo) - 1:
                proxima = st.selectbox("Próxima Etapa:", fluxo[idx+1:], key=f"sel_{i}")
                novo_resp = st.text_input("Quem assume?", key=f"res_{i}")
                
                # Campos de Inventário (Se for Contagem)
                if proxima == "Contagem":
                    t_p = st.text_input("Item:", key=f"tp_{i}")
                    q_p = st.number_input("Qtd:", 1, key=f"qp_{i}")
                    if st.button("➕ Add Item", key=f"ba_{i}"):
                        df.at[i, 'itens'] = str(row['itens']) + f"{t_p}({q_p}); "
                        salvar_dados(df, conexao) ; st.rerun()

                if st.button("✅ Confirmar Mudança", key=f"conf_{i}"):
                    if novo_resp:
                        t_agora = agora_bruto()
                        # Atualiza log, status e anexa novo marco de tempo
                        df.at[i, 'status'] = proxima
                        df.at[i, 'resp'] = novo_resp
                        df.at[i, 'detalhes'] = str(row['detalhes']) + f" | [{agora()}] {proxima} ({novo_resp})"
                        df.at[i, 'tempos_json'] = str(row['tempos_json']) + f";{proxima}|{t_agora}"
                        salvar_dados(df, conexao) ; st.rerun()

# --- 3. RELATÓRIO DE PRODUTIVIDADE (PREVISTO VS REALIZADO) ---
st.write("---")
if st.checkbox("📊 Ver Relatório de Produtividade e Tempos"):
    st.subheader("⏱️ Cronometragem por Lote")
    for idx, r in df.iterrows():
        with st.expander(f"Lote {r['id']} - {r['cli']}"):
            st.write(f"**Itens:** {r['itens']}")
            # Quebra o texto de tempos para calcular duração
            etapas_tempo = str(r['tempos_json']).split(";")
            for j in range(len(etapas_tempo)-1):
                nome_e, t1 = etapas_tempo[j].split("|")
                _, t2 = etapas_tempo[j+1].split("|")
                
                d1 = datetime.fromisoformat(t1)
                d2 = datetime.fromisoformat(t2)
                duracao = int((d2 - d1).total_seconds() / 60)
                
                # Exemplo de Comparação Futura:
                # Se duracao > 30 min e nome_e == "Lavagem": st.error("Atrasado")
                st.write(f"⏱️ **{nome_e}**: {duracao} minutos")
