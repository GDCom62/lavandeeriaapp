import streamlit as st
import pandas as pd
from datetime import datetime
import io
import time
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(page_title="Lavo e Levo V27 Final", page_icon="🧺", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #007bff; color: white; }
    .status-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #ffffff; margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    .metric-container { background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #dee2e6; }
    .alerta-tempo { color: #d9534f; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÕES FIXAS (Evita NameError) ---
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120, 
    "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60, 
    "LAVADORA 04 (50kg)": 50, 
    "LAVADORA 05 (10kg)": 10
}

# ID da sua planilha Google
URL_ID = "1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ"
URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0/export?format=csv"

# --- FUNÇÃO PARA GERAR O ROMANEIO PDF ---
def gerar_romaneio_pdf(row):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, "ROMANEIO DE ENTREGA - LAVO E LEVO")
    p.setFont("Helvetica", 10)
    p.drawString(100, height - 70, f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.line(100, height - 75, 500, height - 75)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, height - 100, f"CLIENTE: {row['cli']}")
    p.setFont("Helvetica", 11)
    p.drawString(100, height - 120, f"ID do Lote: {row['id']} | Gaiola: {row['maq']}")
    p.rect(100, height - 190, 400, 40)
    p.drawString(110, height - 170, f"PESO ENTRADA (SUJO): {row['p_in']} kg")
    p.drawString(110, height - 185, f"PESO SAÍDA (LIMPO): {row['p_lavagem']} kg")
    p.setFont("Helvetica-Bold", 12)
    p.drawString(100, height - 220, "DETALHAMENTO DE PEÇAS:")
    p.setFont("Helvetica", 11)
    y = height - 240
    for item in str(row['detalhe_itens']).split(','):
        p.drawString(120, y, f"• {item.strip()}")
        y -= 20
    p.line(100, 100, 250, 100); p.drawString(100, 85, "Lavanderia")
    p.line(300, 100, 450, 100); p.drawString(300, 85, "Motorista")
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 3. CONEXÃO E DADOS (ECONOMIA DE COTA) ---
@st.cache_data(ttl=30)
def carregar_dados():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_lido = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
        # Limpeza de tipos para evitar TypeError
        for c in ["id", "cli", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]:
            df_lido[c] = df_lido[c].astype(str).replace(['nan', 'None'], '')
        for n in ["p_in", "p_lavagem"]:
            df_lido[n] = pd.to_numeric(df_lido[n], errors='coerce').fillna(0.0)
        return df_lido, conn
    except:
        return None, None

# --- SIDEBAR ---
st.sidebar.title("👤 Operador")
turno_ativo = st.sidebar.selectbox("Turno:", ["Manhã", "Tarde"])
operador_logado = st.sidebar.text_input("Seu Nome:").upper()

if st.sidebar.button("🔄 Sincronizar Dados"):
    st.cache_data.clear()
    st.rerun()

df, conn = carregar_dados()

if df is None:
    st.error("⚠️ Falha ao ler a planilha. Verifique a URL ou aguarde a cota do Google liberar.")
    st.stop()

# --- 4. INTERFACE ---
tab1, tab2, tab3, tab4 = st.tabs(["📥 Recebimento", "🧼 Lavagem", "⚙️ Produção", "📊 Relatórios"])

with tab1:
    with st.form("f1", clear_on_submit=True):
        st.subheader("Entrada de Lote")
        c1, c2 = st.columns(2)
        cli = c1.text_input("Hospital / Cliente")
        peso = c2.number_input("Peso Sujo (kg)", 0.1, 2000.0)
        if st.form_submit_button("REGISTRAR ENTRADA"):
            if cli and operador_logado:
                novo = pd.DataFrame([{
                    "id": datetime.now().strftime("%d%H%M%S"), "cli": cli.upper(), 
                    "p_in": peso, "p_lavagem": 0.0, "status": "Aguardando Lavagem", 
                    "h_entrada": datetime.now().strftime("%H:%M"), "etapa_inicio": datetime.now().isoformat(), 
                    "resp": operador_logado, "turno": turno_ativo, "maq": "", "detalhe_itens": ""
                }])
                df = pd.concat([df, novo], ignore_index=True)
                conn.update(data=df); st.cache_data.clear(); st.rerun()
            else: st.warning("Preencha o cliente e seu nome!")

with tab2:
    st.subheader("Carregamento")
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        maq_sel = st.selectbox("Selecione a Lavadora:", list(MAQUINAS.keys()))
        lotes = st.multiselect("Selecione os Lotes:", espera['id'].tolist(), 
                              format_func=lambda x: f"{df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)")
        if st.button("🚀 INICIAR LAVAGEM") and lotes:
            for lid in lotes:
                idx = df[df['id'] == lid].index
                df.loc[idx, 'status'], df.loc[idx, 'maq'], df.loc[idx, 'etapa_inicio'] = "Lavagem", maq_sel, datetime.now().isoformat()
            conn.update(data=df); st.cache_data.clear(); st.rerun()
    else: st.info("Nenhum lote aguardando lavagem.")

with tab3:
    st.subheader("Processamento Ativo")
    ativos = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    for i, row in ativos.iterrows():
        with st.container():
            st.markdown("<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2.5])
            
            # Cronômetro
            ini = datetime.fromisoformat(str(row['etapa_inicio']))
            minutos = int((datetime.now() - ini).total_seconds() // 60)
            
            c1.markdown(f"**{row['cli']}** ({row['p_in']}kg)\n\nEtapa: {row['status']}")
            c2.markdown(f"⏱️ {minutos} min")
            if c2.button("↩️ Reverter", key=f"rev_{row['id']}"):
                mapa = {"Lavagem":"Aguardando Lavagem", "Secagem":"Lavagem", "Passadeira":"Secagem", "Dobragem":"Secagem"}
                df.at[i, 'status'] = mapa.get(row['status'], row['status'])
                conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            if row['status'] == "Lavagem":
                if c3.button("🌀 Ir p/ Secagem", key=f"s_{row['id']}"):
                    df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Secagem", datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            elif row['status'] == "Secagem":
                with c3.expander("📝 Relatar Itens"):
                    col1, col2 = st.columns(2)
                    l = col1.number_input("Lençol", 0, key=f"l_{row['id']}")
                    f = col1.number_input("Fronha", 0, key=f"f_{row['id']}")
                    t = col2.number_input("Toalha", 0, key=f"t_{row['id']}")
                    c = col2.number_input("Campo", 0, key=f"c_{row['id']}")
                    res = f"Lencol:{l}, Fronha:{f}, Toalha:{t}, Campo:{c}"
                    
                    b1, b2 = st.columns(2)
                    if b1.button("🧣 Passadeira", key=f"p_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'], df.at[i, 'etapa_inicio'] = "Passadeira", res, datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                    if b2.button("🧺 Dobragem", key=f"d_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'], df.at[i, 'etapa_inicio'] = "Dobragem", res, datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            
            elif row['status'] in ["Passadeira", "Dobragem"]:
                with c3.expander("⚖️ Peso Final e Gaiola"):
                    ps = st.number_input("Peso Limpo (kg)", 0.1, 2000.0, float(row['p_in']), key=f"ps_{row['id']}")
                    gn = st.text_input("Nº da Gaiola", key=f"gn_{row['id']}")
                    if st.button("🏁 Enviar p/ GAIOLA", key=f"f_{row['id']}") and gn:
                        df.at[i, 'p_lavagem'], df.at[i, 'maq'], df.at[i, 'status'], df.at[i, 'etapa_inicio'] = ps, f"GAIOLA {gn}", "Gaiola", datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📦 Expedição (Gaiola)")
    gaiola_ativos = df[df['status'] == "Gaiola"]
    for i, r in gaiola_ativos.iterrows():
        with st.expander(f"🚚 {r['maq']} - {r['cli']} ({r['p_lavagem']}kg)"):
            st.download_button("📄 Baixar Romaneio PDF", gerar_romaneio_pdf(r), f"romaneio_{r['id']}.pdf", "application/pdf", key=f"pdf_{r['id']}")
            if st.button("✅ CONFIRMAR ENTREGA", key=f"out_{r['id']}"):
                df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Entregue", datetime.now().isoformat()
                conn.update(data=df); st.cache_data.clear(); st.rerun()

with tab4:
    st.subheader("📊 Relatório de Pesos")
    df_fin = df[df['status'].isin(["Gaiola", "Entregue"])].copy()
    if not df_fin.empty:
        df_fin['Variação'] = df_fin['p_lavagem'] - df_fin['p_in']
        st.dataframe(df_fin[['cli', 'p_in', 'p_lavagem', 'Variação', 'maq', 'detalhe_itens']], use_container_width=True)
    else:
        st.info("Aguardando lotes finalizados.")
