import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Lavo e Levo Cloud", page_icon="🧺", layout="wide")

# Inicializa o banco de dados na memória da nuvem
if "banco" not in st.session_state:
    st.session_state.banco = []

st.title("🧺 LAVANDERIA LAVO E LEVO - GESTÃO CLOUD")

# MENU DE NAVEGAÇÃO
menu = st.radio("Navegação:", ["Fila de Produção", "Relatórios e Auditoria"], horizontal=True)

def agora():
    return datetime.now().strftime("%H:%M")

if menu == "Fila de Produção":
    # 1. ENTRADA
    with st.expander("➕ NOVO LOTE (RECEBIMENTO)", expanded=True):
        with st.form("entrada", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cli = col1.text_input("Cliente:")
            p_in = col2.number_input("Peso Entrada (kg):", 0.1)
            r1 = col1.text_input("Responsável Lavagem:")
            lista_in = col2.text_area("Itens (Ex: 50 Lençol, 20 Fronha):")
            
            if st.form_submit_button("INICIAR PROCESSO"):
                if cli and r1:
                    st.session_state.banco.append({
                        "id": len(st.session_state.banco) + 1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0,
                        "status": "Lavagem", "resp": r1, "entrada": lista_in, "saida": [], 
                        "mot": "", "h_in": agora(), "gaiola": ""
                    })
                    st.rerun()

    st.write("---")
    # 2. FILA DE TRABALHO (7 ETAPAS)
    for i, item in enumerate(st.session_state.banco):
        if item['status'] != "Entregue":
            with st.container(border=True):
                st.write(f"**Lote #{item['id']} - {item['cli']}** ({item['p_in']}kg)")
                st.caption(f"Status Atual: {item['status']} | Com: {item['resp']}")

                if item['status'] == "Lavagem":
                    r2 = st.text_input("Quem leva p/ Secar?", key=f"r2{i}")
                    if st.button("➡️ Para Secagem", key=f"b2{i}"):
                        item['status'], item['resp'] = "Secagem", r2 ; st.rerun()

                elif item['status'] == "Secagem":
                    r3 = st.text_input("Operador Secadora:", key=f"r3{i}")
                    c1, c2 = st.columns(2)
                    if c1.button("👔 Passadeira", key=f"bp{i}"):
                        item['status'], item['resp'] = "Passadeira", r3 ; st.rerun()
                    if c2.button("📦 Dobragem", key=f"bd{i}"):
                        item['status'], item['resp'] = "Dobragem", r3 ; st.rerun()

                elif item['status'] in ["Passadeira", "Dobragem"]:
                    r4 = st.text_input("Quem fará contagem?", key=f"r4{i}")
                    if st.button("🔢 Para Contagem", key=f"bc{i}"):
                        item['status'], item['resp'] = "Contagem", r4 ; st.rerun()

                elif item['status'] == "Contagem":
                    it_s = st.text_input("Item Saída:", key=f"is{i}")
                    qt_s = st.number_input("Qtd:", 1, key=f"qs{i}")
                    if st.button("➕ Add Item", key=f"ba{i}"):
                        item['saida'].append(f"{it_s}: {qt_s}") ; st.rerun()
                    st.write("Saída:", ", ".join(item['saida']))
                    if st.button("⚖️ Finalizar e Pesar", key=f"bf{i}"):
                        item['status'] = "Gaiola" ; st.rerun()

                elif item['status'] == "Gaiola":
                    p_out = st.number_input("Peso Saída:", 0.1, key=f"po{i}")
                    gai = st.text_input("Nº Gaiola:", key=f"g{i}")
                    mot = st.selectbox("Motorista:", ["Carlos", "Ricardo", "Fábio"], key=f"m{i}")
                    
                    if p_out > 0:
                        perda = ((item['p_in'] - p_out) / item['p_in']) * 100
                        if perda > 5: st.error(f"⚠️ Perda de {perda:.1f}%")
                        else: st.success(f"✅ Perda de {perda:.1f}%")

                    if st.button("🚚 LIBERAR ENTREGA", key=f"be{i}"):
                        item['p_out'], item['status'], item['mot'], item['gaiola'] = p_out, "Entregue", mot, gai
                        st.rerun()

else:
    # --- RELATÓRIOS ---
    st.header("📊 Relatório de Produção")
    if st.session_state.banco:
        df = pd.DataFrame(st.session_state.banco)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Planilha Excel (CSV)", csv, "producao_lavanderia.csv", "text/csv")
    else:
        st.info("Nenhum dado registrado.")
