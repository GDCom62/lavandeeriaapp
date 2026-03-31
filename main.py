import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Lavo e Levo V26", layout="wide")

# Conexão
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

# --- INTERFACE ---
tab1, tab2, tab3 = st.tabs(["📥 Entrada", "🧺 Lavagem (Máquinas)", "🚀 Produção e Fluxo"])

with tab1:
    with st.form("entrada"):
        st.subheader("Novo Recebimento")
        c1, c2 = st.columns(2)
        cli = c1.text_input("Cliente")
        peso = c2.number_input("Peso (kg)", 0.1)
        if st.form_submit_button("Registrar"):
            novo_id = datetime.now().strftime("%H%M%S")
            novo = pd.DataFrame([{"id": novo_id, "cli": cli.upper(), "p_in": peso, "status": "Aguardando Lavagem", "h_in": datetime.now().isoformat()}])
            df = pd.concat([df, novo], ignore_index=True)
            conn.update(data=df)
            st.rerun()

with tab2:
    st.subheader("🧼 Gestão de Máquinas")
    # Lotes que estão esperando para entrar na máquina
    espera = df[df['status'] == "Aguardando Lavagem"]
    
    if not espera.empty:
        lotes_selecionados = st.multiselect("Selecione os lotes para a mesma máquina:", 
                                            espera['id'].tolist(), 
                                            format_func=lambda x: f"Lote {x} - {df[df['id']==x]['cli'].values[0]}")
        
        num_maquina = st.selectbox("Qual máquina?", ["Máquina 01 (20kg)", "Máquina 02 (20kg)", "Máquina 03 (50kg)"])
        op_lavagem = st.text_input("Operador de Lavagem")

        if st.button("Iniciar Lavagem Conjunta"):
            if lotes_selecionados and op_lavagem:
                for lid in lotes_selecionados:
                    idx = df[df['id'] == lid].index
                    df.at[idx, 'status'] = "Lavando"
                    df.at[idx, 'maquina'] = num_maquina
                    df.at[idx, 'resp_lavagem'] = op_lavagem
                    df.at[idx, 'h_lavagem_inicio'] = datetime.now().isoformat()
                conn.update(data=df)
                st.success("Lavagem Iniciada!")
                st.rerun()

with tab3:
    st.subheader("🏃 Fluxo de Produção")
    # Exibe lotes em processo (exceto entrada e entregue)
    processo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue"])]
    
    for i, row in processo.iterrows():
        with st.expander(f"📦 {row['cli']} | {row['status']} | {row.get('maquina', '')}"):
            c1, c2, c3 = st.columns(3)
            
            # Cálculo de tempo
            inicio = datetime.fromisoformat(row['h_in'])
            tempo_total = datetime.now() - inicio
            c1.metric("Tempo Total", f"{tempo_total.seconds // 60} min")
            
            # Próximo Passo
            fluxo_lista = ["Lavando", "Secagem", "Passadeira", "Dobragem", "Empacotamento", "Gaiola", "Entregue"]
            if row['status'] in fluxo_lista:
                idx = fluxo_lista.index(row['status'])
                proximo = fluxo_lista[idx + 1] if idx + 1 < len(fluxo_lista) else "Finalizado"
                
                op_next = c2.text_input("Próximo Operador", key=f"op_{row['id']}")
                obs = c3.text_input("Obs/Itens", key=f"obs_{row['id']}")
                
                if st.button(f"Mover para {proximo}", key=f"btn_{row['id']}"):
                    df.at[i, 'status'] = proximo
                    df.at[i, f'h_{proximo.lower()}'] = datetime.now().isoformat()
                    df.at[i, 'obs'] = obs
                    conn.update(data=df)
                    st.rerun()
