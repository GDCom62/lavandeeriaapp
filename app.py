import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração de Página
st.set_page_config(page_title="Lavo e Levo V11 - Custos", layout="wide")

# --- CONEXÃO COM PLANILHA ---
from streamlit_gsheets import GSheetsConnection
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(ttl="0")

st.title("🧺 LAVANDERIA LAVO E LEVO - GESTÃO DE CUSTOS")

# --- BARRA LATERAL: CONFIGURAÇÃO DE PREÇOS (INSUMOS) ---
st.sidebar.header("💰 Configuração de Insumos")
custo_energia_kg = st.sidebar.number_input("Custo Energia (por kg):", 0.01, 5.0, 0.45)
custo_agua_kg = st.sidebar.number_input("Custo Água (por kg):", 0.01, 5.0, 0.30)
custo_quimico_kg = st.sidebar.number_input("Custo Químicos (por kg):", 0.01, 5.0, 0.60)
custo_fixo_total = custo_energia_kg + custo_agua_kg + custo_quimico_kg

st.sidebar.info(f"Custo Total por KG: R$ {custo_fixo_total:.2f}")

# --- NAVEGAÇÃO POR ABAS ---
tab_op, tab_dash, tab_custo = st.tabs(["🚀 Operação", "📊 Produtividade", "💵 Custos Industriais"])

# --- ABA 1: OPERAÇÃO (Simplificada para velocidade) ---
with tab_op:
    with st.expander("➕ Nova Entrada Hospitalar"):
        with st.form("f1"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Hospital:")
            peso = c2.number_input("Peso (kg):", 0.1)
            resp = c1.text_input("Responsável:")
            if st.form_submit_button("INICIAR"):
                t_ini = datetime.now().isoformat()
                novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": peso, "p_out": 0.0, 
                                      "status": "Lavagem", "resp": resp, "tempos_json": f"Lavagem|{t_ini}"}])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df) ; st.rerun()

    # Fila Ativa
    for i, row in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            col_a, col_b = st.columns([3, 1])
            col_a.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg)")
            if col_b.button("Avançar ➡️", key=f"b{i}"):
                fluxo = ["Lavagem", "Secagem", "Dobragem", "Entregue"]
                novo_st = fluxo[fluxo.index(row['status']) + 1]
                t_fim = datetime.now().isoformat()
                df.at[i, 'status'] = novo_st
                df.at[i, 'tempos_json'] = str(row['tempos_json']) + f";{novo_st}|{t_fim}"
                conn.update(data=df) ; st.rerun()

# --- ABA 3: CUSTOS INDUSTRIAIS ---
with tab_custo:
    st.subheader("💹 Demonstrativo de Custos por Lote")
    
    if not df.empty:
        # Cálculo de Custos
        df_custo = df.copy()
        df_custo['Custo Energia'] = df_custo['p_in'] * custo_energia_kg
        df_custo['Custo Água'] = df_custo['p_in'] * custo_agua_kg
        df_custo['Custo Químico'] = df_custo['p_in'] * custo_quimico_kg
        df_custo['Custo Total Lote'] = df_custo['Custo Energia'] + df_custo['Custo Água'] + df_custo['Custo Químico']

        # Métricas Gerais
        c1, c2, c3 = st.columns(3)
        total_gasto = df_custo['Custo Total Lote'].sum()
        c1.metric("Gasto Total (Hoje)", f"R$ {total_gasto:.2f}")
        c2.metric("Peso Total Processado", f"{df_custo['p_in'].sum():.1f} kg")
        c3.metric("Ticket Médio Custo/Lote", f"R$ {(total_gasto/len(df_custo)):.2f}" if len(df_custo)>0 else 0)

        # Tabela de Custos Detalhada
        st.write("**Detalhamento por Hospital:**")
        st.dataframe(df_custo[["id", "cli", "p_in", "Custo Energia", "Custo Água", "Custo Químico", "Custo Total Lote"]])
        
        # Gráfico de Distribuição de Custos
        st.write("📊 **Proporção de Gastos por Hospital**")
        st.bar_chart(df_custo.set_index('cli')['Custo Total Lote'])
    else:
        st.info("Nenhum lote para calcular custos.")
