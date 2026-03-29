import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Configuração de Página
st.set_page_config(page_title="Lavo e Levo V6", page_icon="🧺", layout="wide")

# --- GERENCIAMENTO DE DADOS ---
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
    
    cols = ["id", "cli", "p_in", "p_out", "status", "resp", "detalhes", "itens", "mot", "gaiola"]
    return pd.DataFrame(columns=cols), None

def salvar_dados(df_atual, conn):
    if conn:
        conn.update(data=df_atual)
        st.cache_data.clear()
    else:
        df_atual.to_csv(ARQUIVO_LOCAL, index=False)

df, conexao = carregar_dados()
def agora(): return datetime.now().strftime("%H:%M")

st.title("🧺 LAVANDERIA LAVO E LEVO - V6")
st.caption(f"Status: {'☁️ NUVEM' if conexao else '💻 LOCAL'}")

# --- 1. ENTRADA (LAVAGEM) ---
with st.expander("➕ 1. NOVO RECEBIMENTO / LAVAGEM", expanded=True):
    with st.form("f1", clear_on_submit=True):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente:")
        p_in = c2.number_input("Peso Entrada (kg):", 0.0)
        maq = c1.selectbox("Máquina Lavar:", ["LAV-01", "LAV-02", "Industrial-01"])
        resp = c2.text_input("Responsável Carga:")
        if st.form_submit_button("INICIAR PROCESSO"):
            if cli and resp:
                log = f"[{agora()}] Lavagem: {resp} ({maq})"
                novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0, 
                                      "status": "Lavagem", "resp": resp, "detalhes": log, "itens": "", "mot": "", "gaiola": ""}])
                df = pd.concat([df, novo], ignore_index=True)
                salvar_dados(df, conexao) ; st.rerun()

st.write("---")

# --- FILA DE TRABALHO (FLUXO SIMPLIFICADO) ---
ativos = df[df['status'] != "Entregue"]

for i, row in ativos.iterrows():
    with st.container(border=True):
        col_info, col_acao = st.columns([2, 1])
        
        with col_info:
            st.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg)")
            st.caption(f"📍 Etapa Atual: `{row['status']}` | Responsável: {row['resp']}")
            st.caption(f"📜 Histórico: {row['detalhes']}")
            if row['itens']: st.info(f"📦 Itens: {row['itens']}")

        with col_acao:
            # Menu de Seleção da Próxima Etapa
            fluxo_lista = ["Lavagem", "Secagem", "Passadeira", "Dobragem", "Contagem", "Gaiola", "Entregue"]
            idx_atual = fluxo_lista.index(row['status']) if row['status'] in fluxo_lista else 0
            
            # Só mostra o seletor se não for a última etapa
            if idx_atual < len(fluxo_lista) - 1:
                proxima = st.selectbox("Mover para:", fluxo_lista[idx_atual+1:], key=f"sel_{i}")
                novo_resp = st.text_input("Quem assume?", key=f"res_{i}")
                
                # Campos extras para etapas específicas
                if proxima == "Contagem":
                    t_p = st.text_input("Peça:", key=f"tp_{i}")
                    q_p = st.number_input("Qtd:", 1, key=f"qp_{i}")
                    if st.button("➕ Add Item", key=f"ba_{i}"):
                        df.at[i, 'itens'] = str(row['itens']) + f"{t_p}({q_p}); "
                        salvar_dados(df, conexao) ; st.rerun()

                if proxima == "Entregue":
                    p_out = st.number_input("Peso Saída:", 0.0, key=f"po_{i}")
                    mot = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"m_{i}")
                    gai = st.text_input("Gaiola:", key=f"g_{i}")

                if st.button("✅ Confirmar Mudança", key=f"conf_{i}"):
                    if novo_resp:
                        df.at[i, 'status'] = proxima
                        df.at[i, 'resp'] = novo_resp
                        df.at[i, 'detalhes'] = str(row['detalhes']) + f" | [{agora()}] {proxima} por {novo_resp}"
                        
                        # Se for a entrega final, salva os dados de logística
                        if proxima == "Entregue" and p_out > 0:
                            df.at[i, 'p_out'], df.at[i, 'mot'], df.at[i, 'gaiola'] = p_out, mot, gai
                            
                        salvar_dados(df, conexao) ; st.rerun()
                    else:
                        st.warning("Digite o nome do responsável!")

if st.checkbox("📊 Ver Relatório Completo"):
    st.dataframe(df)
