import streamlit as st
import pandas as pd
from datetime import datetime
import io
import time
import requests
from streamlit_gsheets import GSheetsConnection
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# --- 1. CONFIGURAÇÃO DE PÁGINA ---
st.set_page_config(
    page_title="Lavo e Levo V31 - Gestão Industrial", 
    page_icon="🧺", 
    layout="wide"
)

# Estilo CSS Personalizado
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; background-color: #495057; color: white; }
    .status-card { border-left: 10px solid #ddd; padding: 15px; border-radius: 10px; background-color: #ffffff; margin-bottom: 15px; box-shadow: 2px 2px 8px rgba(0,0,0,0.1); color: black; }
    .card-verde { border-left-color: #28a745; }
    .card-amarelo { border-left-color: #ffc107; }
    .card-vermelho { border-left-color: #dc3545; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DADOS E CONEXÃO ---
URL_ID = "1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ"
URL_PLANILHA = f"https://google.com{URL_ID}/export?format=csv"
MAQUINAS = {"LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120, "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50}

conn = st.connection("gsheets", type=GSheetsConnection)

# --- 3. SISTEMA DE AUTENTICAÇÃO ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("<h2 style='text-align: center;'>🔐 Acesso Restrito - Lavo e Levo</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            usuario_input = st.text_input("Usuário (Operador)").upper()
            senha_input = st.text_input("Senha", type="password")
            
            if st.button("ENTRAR"):
                try:
                    df_usuarios = conn.read(worksheet="usuarios")
                    user_match = df_usuarios[
                        (df_usuarios['usuario'].astype(str).str.upper() == usuario_input) & 
                        (df_usuarios['senha'].astype(str) == senha_input)
                    ]
                    if not user_match.empty:
                        st.session_state["autenticado"] = True
                        st.session_state["operador"] = usuario_input
                        st.success(f"Bem-vindo, {usuario_input}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos.")
                except:
                    st.error("Erro ao carregar aba 'usuarios'. Verifique a planilha.")
        st.stop()

verificar_login()

# --- 4. FUNÇÕES DE SUPORTE ---
@st.cache_data(ttl=10)
def carregar_dados(url):
    cols = ["id", "cli", "p_in", "p_lavagem", "status", "maq", "resp", "detalhe_itens", "etapa_inicio", "h_entrada", "turno"]
    try:
        df_lido = pd.read_csv(url)
        for c in cols:
            if c not in df_lido.columns: df_lido[c] = ""
        df_lido["p_in"] = pd.to_numeric(df_lido["p_in"], errors='coerce').fillna(0.0)
        df_lido["p_lavagem"] = pd.to_numeric(df_lido["p_lavagem"], errors='coerce').fillna(0.0)
        return df_lido
    except:
        return pd.DataFrame(columns=cols)

def gerar_romaneio_pdf(row):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    h = A4
    p.setFont("Helvetica-Bold", 16); p.drawString(100, h - 50, "ROMANEIO DE ENTREGA - LAVO E LEVO")
    p.setFont("Helvetica", 10); p.drawString(100, h - 70, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.line(100, h - 75, 500, h - 75)
    p.setFont("Helvetica-Bold", 12); p.drawString(100, h - 100, f"CLIENTE: {row['cli']}")
    p.setFont("Helvetica", 11); p.drawString(100, h - 120, f"ID do Lote: {row['id']} | Gaiola: {row['maq']}")
    p.rect(100, h - 185, 400, 45)
    p.drawString(110, h - 160, f"PESO ENTRADA (SUJO): {row['p_in']} kg")
    p.drawString(110, h - 178, f"PESO SAÍDA (LIMPO): {row['p_lavagem']} kg")
    y = h - 220
    p.setFont("Helvetica-Bold", 11); p.drawString(100, y, "ITENS PROCESSADOS:"); y -= 20
    p.setFont("Helvetica", 10)
    for item in str(row['detalhe_itens']).split(','):
        if item.strip() and ":" in item:
            p.drawString(120, y, f"• {item.strip()}"); y -= 15
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

df = carregar_dados(URL_PLANILHA)

# --- 5. SIDEBAR ---
st.sidebar.title("🧺 Lavo e Levo")
st.sidebar.write(f"Operador: **{st.session_state['operador']}**")
turno_ativo = st.sidebar.selectbox("Turno Ativo:", ["Manhã", "Tarde", "Noite"])
if st.sidebar.button("🔄 Sincronizar"):
    st.cache_data.clear(); st.rerun()
if st.sidebar.button("🚪 Sair"):
    st.session_state["autenticado"] = False; st.rerun()

# --- 6. DASHBOARD SUPERIOR ---
st.title("Gestão de Produção Industrial")
META_DIA = 5000.0
produzido = df[df['status'].isin(["Gaiola", "Entregue"])]['p_lavagem'].sum()
st.metric("Produção Acumulada", f"{produzido:.1f} kg", f"{produzido - META_DIA:.1f} para meta")
st.progress(min(produzido / META_DIA, 1.0))

# --- 7. ABAS ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Recebimento", "🧼 Lavagem", "⚙️ Produção", "📊 Saída", "📜 Histórico"])

with tab1:
    with st.form("recebimento"):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Nome do Cliente/Hospital")
        peso = c2.number_input("Peso Sujo (kg)", 0.1, 2000.0)
        if st.form_submit_button("REGISTRAR ENTRADA"):
            novo_lote = pd.DataFrame([{
                "id": datetime.now().strftime("%d%H%M%S"), "cli": cli.upper(), "p_in": peso, "p_lavagem": 0.0, 
                "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                "etapa_inicio": datetime.now().isoformat(), "resp": st.session_state['operador'], 
                "turno": turno_ativo, "maq": "", "detalhe_itens": ""
            }])
            conn.update(data=pd.concat([df, novo_lote], ignore_index=True))
            st.cache_data.clear(); st.success("Registrado!"); time.sleep(1); st.rerun()

with tab2:
    esp = df[df['status'] == "Aguardando Lavagem"]
    if not esp.empty:
        mq = st.selectbox("Escolha a Máquina:", list(MAQUINAS.keys()))
        lts = st.multiselect("Selecionar Lotes:", esp['id'].tolist(), format_func=lambda x: f"{df[df['id']==str(x)]['cli'].values[0]} ({df[df['id']==str(x)]['p_in'].values[0]}kg)")
        if st.button("🚀 INICIAR LAVAGEM") and lts:
            for lid in lts:
                idx = df[df['id'] == str(lid)].index
                df.loc[idx, ['status', 'maq', 'etapa_inicio']] = ["Lavagem", mq, datetime.now().isoformat()]
            conn.update(data=df); st.cache_data.clear(); st.rerun()
    else: st.info("Fila vazia.")

with tab3:
    atv = df[df['status'].isin(["Lavagem", "Secagem", "Passadeira"])]
    if atv.empty: st.info("Nenhuma máquina operando.")
    for i, row in atv.iterrows():
        minutos = int((datetime.now() - datetime.fromisoformat(str(row['etapa_inicio']))).total_seconds() // 60)
        cor = "card-verde" if minutos <= 30 else "card-amarelo" if minutos <= 60 else "card-vermelho"
        with st.container():
            st.markdown(f"<div class='status-card {cor}'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 1, 2])
            c1.markdown(f"### {row['cli']} | {row['status']}\n**Máquina:** {row['maq']}")
            c2.markdown(f"⏱️ **{minutos} min**")
            with c3:
                if row['status'] == "Lavagem":
                    if st.button("🌀 Ir p/ Secagem", key=f"s_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'etapa_inicio'] = "Secagem", datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                elif row['status'] == "Secagem":
                    with st.expander("📝 Contagem"):
                        l, f, t = st.number_input("Lençol", 0, key=f"l_{i}"), st.number_input("Fronha", 0, key=f"f_{i}"), st.number_input("Toalha", 0, key=f"t_{i}")
                        if st.button("🧣 Passadeira", key=f"p_{row['id']}"):
                            df.at[i, 'status'], df.at[i, 'detalhe_itens'], df.at[i, 'etapa_inicio'] = "Passadeira", f"Lençol:{l}, Fronha:{f}, Toalha:{t}", datetime.now().isoformat()
                            conn.update(data=df); st.cache_data.clear(); st.rerun()
                elif row['status'] == "Passadeira":
                    p_f = st.number_input("Peso Limpo (kg)", value=float(row['p_in']), key=f"pf_{i}")
                    if st.button("🏁 Concluir", key=f"f_{row['id']}"):
                        df.at[i, 'status'], df.at[i, 'p_lavagem'], df.at[i, 'etapa_inicio'] = "Gaiola", p_f, datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    prontos = df[df['status'] == "Gaiola"]
    if not prontos.empty:
        for i, row in prontos.iterrows():
            with st.expander(f"📦 {row['cli']} - {row['p_lavagem']}kg"):
                c_pdf, c_fim = st.columns(2)
                c_pdf.download_button("📥 PDF Romaneio", data=gerar_romaneio_pdf(row), file_name=f"romaneio_{row['id']}.pdf", mime="application/pdf", key=f"pdf_{i}")
                if c_fim.button("🚚 Confirmar Entrega", key=f"ent_{i}"):
                    df.at[i, 'status'] = "Entregue"
                    conn.update(data=df); st.cache_data.clear(); st.rerun()
    else: st.info("Nada pronto para saída.")

with tab5:
    st.subheader("📜 Histórico Geral")
    c1, c2 = st.columns(2)
    f_cli = c1.text_input("Filtrar Cliente:").upper()
    f_stat = c2.multiselect("Filtrar Status:", df['status'].unique(), default=df['status'].unique())
    df_h = df[df['status'].isin(f_stat)]
    if f_cli: df_h = df_h[df_h['cli'].str.contains(f_cli)]
    st.dataframe(df_h.sort_values(by="id", ascending=False), use_container_width=True, hide_index=True)
    st.download_button("📥 Exportar Excel (CSV)", data=df_h.to_csv(index=False).encode('utf-8'), file_name="historico.csv", mime="text/csv")

st.markdown("---")
st.caption(f"Lavo e Levo V31 | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
