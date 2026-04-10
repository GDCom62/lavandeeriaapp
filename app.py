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

# --- 2. SISTEMA DE AUTENTICAÇÃO ---
def verificar_login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if not st.session_state["autenticado"]:
        st.markdown("<h2 style='text-align: center;'>🔐 Acesso Restrito - Lavo e Levo</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            usuario = st.text_input("Usuário (Operador)").upper()
            senha = st.text_input("Senha", type="password")
            
            # Credenciais Simples (Pode ser expandido para o GSheets depois)
            USUARIOS = {"ADMIN": "1234", "OP01": "lavo2024", "OP02": "industrial"}

            if st.button("ENTRAR"):
                if usuario in USUARIOS and USUARIOS[usuario] == senha:
                    st.session_state["autenticado"] = True
                    st.session_state["operador"] = usuario
                    st.success(f"Bem-vindo, {usuario}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos.")
        st.stop()

verificar_login()

# --- 3. FUNÇÕES DE SUPORTE (WhatsApp e PDF) ---
def enviar_whatsapp(mensagem):
    telefone = "5521999999999" # Configure seu número
    apikey = "1234567"        # Configure sua API Key do CallMeBot
    url = f"https://callmebot.com{telefone}&text={mensagem}&apikey={apikey}"
    try:
        requests.get(url, timeout=5)
    except:
        pass

def gerar_romaneio_pdf(row):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    h = A4[1]
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
        if item.strip():
            p.drawString(120, y, f"• {item.strip()}"); y -= 15
    p.showPage(); p.save(); buffer.seek(0)
    return buffer

# --- 4. DADOS E CONEXÃO ---
URL_ID = "1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ"
URL_PLANILHA = f"https://google.com{URL_ID}/export?format=csv"
MAQUINAS = {"LAVADORA 01 (120kg)": 120, "LAVADORA 02 (120kg)": 120, "LAVADORA 03 (60kg)": 60, "LAVADORA 04 (50kg)": 50}

conn = st.connection("gsheets", type=GSheetsConnection)

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
progresso = min(produzido / META_DIA, 1.0)
st.metric("Produção Acumulada", f"{produzido:.1f} kg", f"{produzido - META_DIA:.1f} kg para meta")
st.progress(progresso)

# --- 7. ABAS DE PROCESSO ---
tab1, tab2, tab3, tab4 = st.tabs(["📥 Recebimento", "🧼 Lavagem", "⚙️ Produção Ativa", "📊 Saída/Gaiola"])

with tab1:
    with st.form("recebimento"):
        c1, c2 = st.columns(2)
        cli = c1.text_input("Nome do Hospital/Cliente")
        peso = c2.number_input("Peso Sujo (kg)", 0.1, 2000.0)
        if st.form_submit_button("REGISTRAR ENTRADA"):
            novo_id = datetime.now().strftime("%d%H%M%S")
            novo_lote = pd.DataFrame([{
                "id": novo_id, "cli": cli.upper(), "p_in": peso, "p_lavagem": 0.0, 
                "status": "Aguardando Lavagem", "h_entrada": datetime.now().strftime("%H:%M"),
                "etapa_inicio": datetime.now().isoformat(), "resp": st.session_state['operador'], 
                "turno": turno_ativo, "maq": "", "detalhe_itens": ""
            }])
            df = pd.concat([df, novo_lote], ignore_index=True)
            conn.update(data=df); st.cache_data.clear(); st.success("Registrado!"); time.sleep(1); st.rerun()

with tab2:
    esp = df[df['status'] == "Aguardando Lavagem"]
    if not esp.empty:
        mq = st.selectbox("Escolha a Máquina:", list(MAQUINAS.keys()))
        lts = st.multiselect("Lotes para Lavar:", esp['id'].tolist(), format_func=lambda x: f"{df[df['id']==str(x)]['cli'].values[0]} ({df[df['id']==str(x)]['p_in'].values[0]}kg)")
        if st.button("🚀 INICIAR LAVAGEM") and lts:
            for lid in lts:
                idx = df[df['id'] == str(lid)].index
                df.loc[idx, 'status'] = "Lavagem"
                df.loc[idx, 'maq'] = mq
                df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
            conn.update(data=df); st.cache_data.clear(); st.rerun()
    else:
        st.info("Nenhum lote aguardando lavagem.")

with tab3:
    # Mostra lotes em Lavagem, Secagem e Passadeira
    atv = df[df['status'].isin(["Lavagem", "Secagem", "Passadeira"])]
    if atv.empty:
        st.info("Nenhuma máquina operando no momento.")
    
    for i, row in atv.iterrows():
        ini = datetime.fromisoformat(str(row['etapa_inicio']))
        minutos = int((datetime.now() - ini).total_seconds() // 60)
        cor = "card-verde" if minutos <= 30 else "card-amarelo" if minutos <= 60 else "card-vermelho"
        
        with st.container():
            st.markdown(f"<div class='status-card {cor}'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([2, 1, 2])
            c1.markdown(f"### {row['cli']}\n**Etapa atual:** {row['status']} | **Máquina:** {row['maq']}")
            c2.markdown(f"⏱️ **{minutos} min**")
            
            with c3:
                if row['status'] == "Lavagem":
                    if st.button(f"🌀 Ir p/ Secagem", key=f"btn_s_{row['id']}"):
                        df.at[i, 'status'] = "Secagem"
                        df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
                
                elif row['status'] == "Secagem":
                    with st.expander("Contagem de Peças"):
                        l = st.number_input("Lençol", 0, key=f"l_{row['id']}")
                        f = st.number_input("Fronha", 0, key=f"f_{row['id']}")
                        t = st.number_input("Toalha", 0, key=f"t_{row['id']}")
                        if st.button("🧣 Enviar p/ Passadeira", key=f"btn_p_{row['id']}"):
                            df.at[i, 'status'] = "Passadeira"
                            df.at[i, 'detalhe_itens'] = f"Lençol:{l}, Fronha:{f}, Toalha:{t}"
                            df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                            conn.update(data=df); st.cache_data.clear(); st.rerun()

                elif row['status'] == "Passadeira":
                    p_final = st.number_input("Peso Final (kg)", value=float(row['p_in']), key=f"pf_{row['id']}")
                    if st.button("🏁 Concluir Lote", key=f"btn_f_{row['id']}"):
                        df.at[i, 'status'] = "Gaiola"
                        df.at[i, 'p_lavagem'] = p_final
                        df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                        conn.update(data=df); st.cache_data.clear(); st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

with tab4:
    prontos = df[df['status'] == "Gaiola"]
    if not prontos.empty:
        for i, row in prontos.iterrows():
            with st.expander(f"📦 {row['cli']} - {row['p_lavagem']}kg"):
                col_pdf, col_fim = st.columns(2)
                
                # Botão PDF
                pdf = gerar_romaneio_pdf(row)
                col_pdf.download_button(
                    label="📥 Baixar Romaneio PDF",
                    data=pdf,
                    file_name=f"romaneio_{row['cli']}_{row['id']}.pdf",
                    mime="application/pdf"
                )
                
                # Botão Finalizar
                if col_fim.button("🚚 Confirmar Entrega", key=f"ent_{row['id']}"):
                    df.at[i, 'status'] = "Entregue"
                    conn.update(data=df); st.cache_data.clear(); st.success("Entregue!"); time.sleep(1); st.rerun()
    else:
        st.info("Aguardando lotes finalizados na passadeira.")

st.markdown("---")
st.caption(f"Lavo e Levo V31 | Sistema Industrial | {datetime.now().strftime('%d/%m/%Y %H:%M')}")
