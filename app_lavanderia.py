import streamlit as st
import pandas as pd
import os
from datetime import datetime
import plotly.express as px # Biblioteca para gráficos profissionais

st.set_page_config(page_title="Lavo e Levo V9 - Dashboard", layout="wide")

# --- CONFIGURAÇÃO DE RENDIMENTO ---
MIN_POR_KG_LAVAR = 2.0  
MIN_POR_KG_SECAR = 3.0  

def calcular_projetado(peso, etapa):
    if etapa == "Lavagem": return int(peso * MIN_POR_KG_LAVAR)
    if etapa == "Secagem": return int(peso * MIN_POR_KG_SECAR)
    return 30 

# --- BANCO DE DADOS ---
ARQUIVO_LOCAL = "dados_lavanderia.csv"
def carregar_dados():
    try:
        from streamlit_gsheets import GSheetsConnection
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(ttl="0")
        if not df.empty: return df, conn
    except: pass
    if os.path.exists(ARQUIVO_LOCAL): return pd.read_csv(ARQUIVO_LOCAL), None
    return pd.DataFrame(columns=["id", "cli", "p_in", "status", "resp", "tempos_json"]), None

df, conexao = carregar_dados()

st.title("🧺 LAVANDERIA LAVO E LEVO - DASHBOARD")

menu = st.radio("Navegação:", ["Operação", "Dashboard de Eficiência"], horizontal=True)

if menu == "Operação":
    # (Mantemos o código de entrada e avanço da V8 aqui...)
    with st.expander("➕ Nova Entrada"):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Hospital:")
        peso = c2.number_input("Peso (kg):", 0.1)
        resp = c1.text_input("Responsável:")
        if st.button("INICIAR"):
            t_ini = datetime.now().isoformat()
            novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": peso, "status": "Lavagem", "resp": resp, "tempos_json": f"Lavagem|{t_ini}"}])
            df = pd.concat([df, novo], ignore_index=True)
            if conexao: conexao.update(data=df) ; st.cache_data.clear()
            else: df.to_csv(ARQUIVO_LOCAL, index=False)
            st.rerun()

    for i, row in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            st.write(f"**Lote #{row['id']} - {row['cli']}**")
            proxima = st.selectbox("Próxima Etapa:", ["Secagem", "Passadeira", "Dobragem", "Entregue"], key=f"s{i}")
            n_resp = st.text_input("Responsável:", key=f"r{i}")
            if st.button("Confirmar", key=f"b{i}"):
                t_fim = datetime.now().isoformat()
                df.at[i, 'status'], df.at[i, 'resp'] = proxima, n_resp
                df.at[i, 'tempos_json'] = str(row['tempos_json']) + f";{proxima}|{t_fim}"
                if conexao: conexao.update(data=df) ; st.cache_data.clear()
                else: df.to_csv(ARQUIVO_LOCAL, index=False)
                st.rerun()

else:
    # --- ABA DASHBOARD ---
    st.header("📊 Análise de Performance")
    
    if not df.empty:
        # Processamento de dados para o gráfico
        lista_tempos = []
        for _, r in df.iterrows():
            etapas = str(r['tempos_json']).split(";")
            for j in range(len(etapas)-1):
                n_e, t1 = etapas[j].split("|")
                _, t2 = etapas[j+1].split("|")
                real = int((datetime.fromisoformat(t2) - datetime.fromisoformat(t1)).total_seconds() / 60)
                proj = calcular_projetado(r['p_in'], n_e)
                lista_tempos.append({"Lote": r['id'], "Etapa": n_e, "Real": real, "Projetado": proj, "Colab": r['resp']})
        
        df_plot = pd.DataFrame(lista_tempos)

        if not df_plot.empty:
            # 1. Gráfico Realizado vs Projetado
            fig_comp = px.bar(df_plot, x="Lote", y=["Real", "Projetado"], 
                             title="Comparativo de Tempo (Minutos) por Lote", barmode="group",
                             color_discrete_map={"Real": "#EF553B", "Projetado": "#636EFA"})
            st.plotly_chart(fig_comp, use_container_width=True)

            # 2. Produtividade por Colaborador (Média de tempo por etapa)
            st.subheader("🏆 Eficiência por Colaborador")
            fig_colab = px.box(df_plot, x="Colab", y="Real", points="all", title="Distribuição de Tempo por Funcionário")
            st.plotly_chart(fig_colab, use_container_width=True)

            # 3. Alertas de Atraso
            df_plot['Atraso'] = df_plot['Real'] - df_plot['Projetado']
            atrasados = df_plot[df_plot['Atraso'] > 0]
            if not atrasados.empty:
                st.error(f"⚠️ Atenção: {len(atrasados)} etapas excederam o tempo projetado.")
                st.dataframe(atrasados[["Lote", "Etapa", "Real", "Projetado", "Atraso", "Colab"]])
    else:
        st.info("Aguardando finalização de etapas para gerar gráficos.")
