import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração de Layout Amplo
st.set_page_config(page_title="Lavo e Levo V10 - Rendimento", layout="wide")

# --- CONEXÃO E DADOS ---
from streamlit_gsheets import GSheetsConnection
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0")
except:
    st.error("Erro de conexão com a planilha.")
    st.stop()

# --- CÁLCULO DE PROJETADO (DINÂMICO) ---
MIN_KG_LAVAR = 2.0  # 2 min por kg
MIN_KG_SECAR = 3.0  # 3 min por kg

def calcular_performance(peso, tempo_real, etapa):
    if tempo_real <= 0: return 0
    # Rendimento Real: Quantos KG a pessoa/máquina processou por hora
    kg_hora = (peso / tempo_real) * 60
    return round(kg_hora, 2)

st.title("🧺 LAVANDERIA LAVO E LEVO - GESTÃO DE RENDIMENTO")

menu = st.tabs(["🚀 Operação", "📈 Dashboards de Rendimento", "⚖️ Auditoria de Pesos"])

# --- ABA 1: OPERAÇÃO (FLUXO COMPLETO) ---
with menu[0]:
    with st.expander("➕ Nova Entrada de Lote", expanded=False):
        with st.form("f1"):
            c1, c2 = st.columns(2)
            cli = c1.text_input("Hospital:")
            peso = c2.number_input("Peso (kg):", 0.1)
            maq = c1.selectbox("Lavadora:", ["LAV-01 (20kg)", "LAV-02 (50kg)", "LAV-03 (100kg)"])
            resp = c2.text_input("Responsável Carga:")
            if st.form_submit_button("INICIAR"):
                t_ini = datetime.now().isoformat()
                novo = pd.DataFrame([{"id": len(df)+1, "cli": cli.upper(), "p_in": peso, "p_out": 0.0, 
                                      "status": "Lavagem", "resp": resp, "maq": maq, 
                                      "tempos_json": f"Lavagem|{t_ini}", "h_in": datetime.now().strftime("%H:%M")}])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df) ; st.cache_data.clear() ; st.rerun()

    # Fila Ativa
    for i, row in df[df['status'] != "Entregue"].iterrows():
        with st.container(border=True):
            col_a, col_b = st.columns([2,1])
            col_a.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg)")
            col_a.caption(f"Etapa: {row['status']} | Resp: {row['resp']}")
            
            prox = col_b.selectbox("Mover para:", ["Secagem", "Passadeira", "Dobragem", "Gaiola", "Entregue"], key=f"s{i}")
            n_res = col_b.text_input("Quem assume?", key=f"r{i}")
            
            if col_b.button("✅ Confirmar", key=f"b{i}"):
                if n_res:
                    t_fim = datetime.now().isoformat()
                    df.at[i, 'status'], df.at[i, 'resp'] = prox, n_res
                    df.at[i, 'tempos_json'] = str(row['tempos_json']) + f";{prox}|{t_fim}"
                    conn.update(data=df) ; st.cache_data.clear() ; st.rerun()

# --- ABA 2: DASHBOARDS (RENDIMENTO KG/HORA) ---
with menu[1]:
    st.subheader("📊 Eficiência Industrial (KG / Hora)")
    
    if not df.empty:
        dados_prod = []
        for _, r in df.iterrows():
            etapas = str(r['tempos_json']).split(";")
            for j in range(len(etapas)-1):
                n_e, t1 = etapas[j].split("|")
                _, t2 = etapas[j+1].split("|")
                minutos = int((datetime.fromisoformat(t2) - datetime.fromisoformat(t1)).total_seconds() / 60)
                kg_h = calcular_performance(r['p_in'], minutos, n_e)
                dados_prod.append({"Lote": r['id'], "Etapa": n_e, "Minutos": minutos, "KG_Hora": kg_h, "Colab": r['resp']})
        
        df_dash = pd.DataFrame(dados_prod)

        if not df_dash.empty:
            c1, c2 = st.columns(2)
            
            # Gráfico 1: Rendimento por Colaborador
            fig1 = px.bar(df_dash, x="Colab", y="KG_Hora", color="Etapa", 
                          title="Produtividade: Média de KG processados por Hora", barmode="group")
            c1.plotly_chart(fig1, use_container_width=True)

            # Gráfico 2: Gargalos por Etapa
            fig2 = px.line(df_dash, x="Lote", y="Minutos", color="Etapa", markers=True,
                           title="Tempo de Ciclo por Lote (Minutos)")
            c2.plotly_chart(fig2, use_container_width=True)
            
            st.write("💡 **Dica:** Colaboradores com KG/Hora mais alto são seus 'puxadores' de produção.")

# --- ABA 3: AUDITORIA DE PESO ---
with menu[2]:
    st.subheader("⚖️ Conferência de Entrada vs Saída")
    st.dataframe(df[["id", "cli", "p_in", "p_out", "status", "h_in"]])
