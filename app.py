import streamlit as st
import pandas as pd
from datetime import datetime
import io
import time
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- CONFIGURAÇÕES VISUAIS ---
URL_ICONE_INDUSTRIAL = "https://flaticon.com"

# 1. CONFIGURAÇÃO DE PÁGINA
st.set_page_config(
    page_title="Lavo e Levo V30", 
    page_icon=URL_ICONE_INDUSTRIAL, 
    layout="wide"
)

# Estilos CSS Customizados
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #495057; color: white; }
    .status-card { border-left: 10px solid #ddd; padding: 15px; border-radius: 10px; background-color: #ffffff; margin-bottom: 15px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); }
    .card-verde { border-left-color: #28a745; }
    .card-amarelo { border-left-color: #ffc107; }
    .card-vermelho { border-left-color: #dc3545; }
    .metric-container { background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #dee2e6; }
    .sidebar-logo { display: block; margin-left: auto; margin-right: auto; width: 50%; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONFIGURAÇÕES TÉCNICAS ---
MAQUINAS = {
    "LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120,
    "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50, "LAVADORA 05 (10kg)": 10
}
URL_ID = "1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ"
URL_PLANILHA = f"https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0/export?format=csv"

# --- FUNÇÃO GERADORA DE PDF ---
def gerar_romaneio_pdf(row):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    h = A4
    p.setFont("Helvetica-Bold", 16); p.drawString(100, h - 50, "ROMANEIO DE ENTREGA - LAVO E LEVO")
    p.setFont("Helvetica", 10); p.drawString(100, h - 70, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.setFont("Helvetica-Bold", 12); p.drawString(100, h - 100, f"CLIENTE: {row['cli']}")
    p.setFont("Helvetica", 11); p.drawString(100, h - 120, f"Gaiola: {row['maq']} | ID: {row['id']}")
    p.rect(100, h - 180, 400, 40); p.drawString(110, h - 160, f"PESO ENTRADA: {row['p_in']} kg"); p.drawString(110, h - 175, f"PESO SAÍDA: {row['p_lavagem']} kg")
    y = h - 220
    p.setFont("Helvetica-Bold", 11); p.drawString(100, y, "ITENS PROCESSADOS:"); y -= 20
    p.setFont("Helvetica", 10)
    for item in str(row['detalhe_itens']).split(','):
        p.drawString(120, y, f"• {item.strip()}"); y -= 15
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 3. CONEXÃO E CARREGAMENTO (ANTI-ERRO) ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=15)
def carregar_dados(url):
    cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
    try:
        df_lido = pd.read_csv(url)
        if df_lido.empty or "status" not in df_lido.columns: return pd.DataFrame(columns=cols)
        for c in cols:
            if c in df_lido.columns: df_lido[c] = df_lido[c].astype(str).replace(['nan', 'None'], '')
            else: df_lido[c] = ""
        df_lido["p_in"] = pd.to_numeric(df_lido["p_in"], errors='coerce').fillna(0.0)
        df_lido["p_lavagem"] = pd.to_numeric(df_lido["p_lavagem"], errors='coerce').fillna(0.0)
        return df_lido
    except: return pd.DataFrame(columns=cols)

df = carregar_dados(URL_PLANILHA)

# --- SIDEBAR COM LOGOTIPO ---
st.sidebar.image(URL_ICONE_INDUSTRIAL, width=120)
st.sidebar.markdown("<h2 style='text-align: center; color: #495057;'>Lavo e Levo</h2>", unsafe_allow_html=True)
turno_ativo = st.sidebar.selectbox("Turno Ativo:", ["Manhã", "Tarde"])
operador_logado = st.sidebar.text_input("Nome do Operador:").upper()
if st.sidebar.button("🔄 Sincronizar Sistema"):
    st.cache_data.clear(); st.rerun()

# --- 4. TELA PRINCIPAL: META DIÁRIA ---
st.title("🧺 GESTÃO INDUSTRIAL LAVO E LEVO")

META_DIA = 5000.0
produzido = df[df['status'].isin(["Gaiola", "Entregue"])]['p_lavagem'].sum()
progresso = min(produzido / META_DIA, 1.0)
st.markdown(f"**Produção Atual:** {produzido:.1f}kg de {META_DIA}kg (Meta Diária)")
st.progress(progresso)
if produzido >= META_DIA: st.success("🎯 META DIÁRIA ATINGIDA!"); st.balloons()

tab1, tab2, tab3, tab4 = st.tabs(["📥 Recebimento", "🧼 Lavagem", "⚙️ Produção", "📊 Dashboards"])

# --- ABAS DE PROCESSO ---
with tab1:
    with st.form("f_receb"):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Hospital")
        peso = c2.number_input("Peso Sujo (kg)", 0.1, 2000.0)
        if st.form_submit_button("REGISTRAR ENTRADA") and operador_logado:
            novo = pd.DataFrame([{"id": datetime.now().strftime("%d%H%M%S"), "cli": cli.upper(), "p_in": peso, "p_lavagem": 0.0, "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"), "etapa_inicio": datetime.now().isoformat(), "resp": operador_logado, "turno": turno_ativo, "maq": "", "detalhe_itens": ""}])
            df = pd.concat([df, novo], ignore_index=True)
            conn.update(data=df); st.cache_data.clear(); st.rerun()

with tab2:
    espera = df[df['status'] == "Aguardando Lavagem"]
    if not espera.empty:
        maq_sel = st.selectbox("Lavadora:", list(MAQUINAS.keys()))
        lotes = st.multiselect("Lotes:", espera['id'].tolist(), format_func=lambda x: f"{df[df['id']==x]['cli'].values} ({df[df['id']==x]['p_in'].values}kg)")
        if st.button("🚀 INICIAR CARGA") and lotes:
            for lid in lotes:
                idx = df[df['id'] == str(lid)].index
                df.loc[idx, 'status'], df.loc[idx, 'maq'], df.loc[idx, 'etapa_inicio'] = "Lavagem", maq_sel, datetime.now().isoformat()
            conn.update(data=df); st.cache_data.clear(); st.rerun()

with tab3:
    ativos = df[~df['status'].isin(["Aguardando Lavagem", "Entregue", "Gaiola"])]
    for i, row in ativos.iterrows():
        ini = datetime.fromisoformat(str(row['etapa_inicio']))
        minutos = int((datetime.now() - ini).total_seconds() // 60)
        cor = "card-verde" if minutos <= 30 else "card-amarelo" if minutos <= 60 else "card-vermelho"
        with st.container():
            st.markdown(f"<div class='status-card {cor}'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2.5])
            c1.markdown(f"**{row['cli']}** ({row['p_in']}kg)\n\nEtapa: {row['status']}")
            c2.markdown(f"⏱️ **{minutos} min**")
            if c2.button("↩️ Reverter", key=f"rev_{row['id']}"):
                mapa = {"Lavagem":"Aguardando Lavagem", "Secagem":"Lavagem", "Passadeira":"Secagem", "Dobragem":"Secagem"}
                df.at[i, 'status'] = mapa.get(row['status'], row['status'])
                conn.update(data=df); st.cache_data.clear(); st.rerun()
            if row['status'] == "Lavagem":
                if c3.button("🌀 Ir p/ Secagem", key=f"s_{row['id']}"):
                    df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Secagem", datetime.now().isoformat()
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
            elif row['status'] == "Secagem":
                with c3.expander("📝 Relatar Peças"):
                    l, f, t = st.number_input("Lençol", 0, key=f"l_{row['id']}"), st.number_input("Fronha", 0, key=f"f_{row['id']}"), st.number_input("Toalha", 0, key=f"t_{row['id']}")
                    res = f"Lencol:{l}, Fronha:{f}, Toalha:{t}"
                    if st.button("🧣 Passadeira", key=f"p_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'], df.at[i, 'etapa_inicio'] = "Passadeira", res, datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                    if st.button("🧺 Dobragem", key=f"d_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'detalhe_itens'], df.at[i, 'etapa_inicio'] = "Dobragem", res, datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            elif row['status'] in ["Passadeira", "Dobragem"]:
                with c3.expander("⚖️ Finalizar"):
                    ps = st.number_input("Peso Limpo (kg)", 0.1, 2000.0, float(row['p_in']), key=f"ps_{row['id']}")
                    gn = st.text_input("Nº Gaiola", key=f"gn_{row['id']}")
                    if st.button("🏁 GAIOLA", key=f"f_{row['id']}") and gn:
                        df.at[i, 'p_lavagem'], df.at[i, 'maq'], df.at[i, 'status'], df.at[i, 'etapa_inicio'] = ps, f"GAIOLA {gn}", "Gaiola", datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider(); st.subheader("📦 Expedição")
    for i, r in df[df['status'] == "Gaiola"].iterrows():
        with st.expander(f"🚚 {r['maq']} - {r['cli']} ({r['p_lavagem']}kg)"):
            st.download_button("📄 PDF Romaneio", gerar_romaneio_pdf(r), f"romaneio_{r['id']}.pdf", key=f"pdf_{r['id']}")
            if st.button("✅ CONFIRMAR ENTREGA", key=f"out_{r['id']}"):
                df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Entregue", datetime.now().isoformat()
                conn.update(data=df); st.cache_data.clear(); st.rerun()

with tab4:
    st.subheader("📊 Dashboards Industrial")
    if not df.empty:
        df_fin = df[df['status'].isin(["Gaiola", "Entregue"])].copy()
        if not df_fin.empty:
            df_fin['Variação kg'] = df_fin['p_lavagem'] - df_fin['p_in']
            st.write("### Histórico e Quebra de Peso")
            st.dataframe(df_fin[['cli', 'p_in', 'p_lavagem', 'Variação kg', 'maq']], use_container_width=True)
            
            st.write("### Distribuição de Carga por Máquina (kg)")
            lav_data = df[df['maq'].str.contains("LAVADORA")].groupby('maq')['p_in'].sum().reset_index()
            st.plotly_chart({"data": [{"labels": lav_data['maq'], "values": lav_data['p_in'], "type": "pie", "hole": .4}]})
