import streamlit as st
import pandas as pd
import mysql.connector
import plotly.express as px

st.set_page_config(page_title="Dashboards - Lavo e Levo", layout="wide")

# Conexão TiDB
def get_db_connection():
    return mysql.connector.connect(
        host=st.secrets["tidb"]["host"],
        port=st.secrets["tidb"]["port"],
        user=st.secrets["tidb"]["user"],
        password=st.secrets["tidb"]["password"],
        database=st.secrets["tidb"]["database"]
    )

st.title("📊 Painel de Produtividade Industrial")

try:
    conn = get_db_connection()
    # Puxar dados
    df = pd.read_sql("SELECT * FROM producao", conn)
    conn.close()

    if not df.empty:
        # KPI's Principais
        c1, c2, c3 = st.columns(3)
        total_kg = df['p_lavagem'].sum()
        c1.metric("Total Processado (kg)", f"{total_kg:.1f}")
        c2.metric("Lotes Entregues", len(df[df['status'] == 'Entregue']))
        c3.metric("Peso Médio por Lote", f"{(df['p_in'].mean()):.1f} kg")

        st.markdown("---")

        col_esq, col_dir = st.columns(2)

        # Gráfico 1: Produção por Turno
        fig_turno = px.bar(df, x='turno', y='p_lavagem', color='turno',
                           title="Produção por Turno (kg)",
                           labels={'p_lavagem': 'Quilos', 'turno': 'Turno'})
        col_esq.plotly_chart(fig_turno, use_container_width=True)

        # Gráfico 2: Produção por Cliente
        fig_cli = px.pie(df, values='p_lavagem', names='cli', 
                         title="Distribuição por Cliente (%)")
        col_dir.plotly_chart(fig_cli, use_container_width=True)

        # Gráfico 3: Desempenho por Operador
        st.subheader("🚀 Top Operadores (kg)")
        fig_resp = px.bar(df, x='resp', y='p_lavagem', 
                          color='resp', barmode='group')
        st.plotly_chart(fig_resp, use_container_width=True)

    else:
        st.warning("Ainda não há dados para gerar gráficos.")

except Exception as e:
    st.error(f"Erro ao carregar Dashboards: {e}")
