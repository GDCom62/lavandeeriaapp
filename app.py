import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página (DEVE SER A PRIMEIRA LINHA)
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

# Estilo Visual
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .status-card { border: 1px solid #ddd; padding: 20px; border-radius: 12px; background-color: #ffffff; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🧺 SISTEMA LAVANDERIA - V26")

# 2. Conexão com Google Sheets
# IMPORTANTE: Verifique se este link é o que aparece na barra do navegador (terminando em /edit...)
URL_PLANILHA = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Lendo os dados - Usamos ttl=0 para atualização em tempo real
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    # Tratamento para o erro de 'Response [200]' ou DataFrame vazio
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        # Cria um DataFrame inicial se a planilha estiver vazia
        cols = ["id", "cli", "p_in", "status", "maquina", "resp", "detalhe_itens", "h_in", "etapa_inicio"]
        df = pd.DataFrame(columns=cols)
    else:
        # Garante que as colunas necessárias existam no DF carregado
        cols_necessarias = ["id", "cli", "p_in", "status", "maquina", "resp", "detalhe_itens", "h_in", "etapa_inicio"]
        for col in cols_necessarias:
            if col not in df.columns:
                df[col] = ""
    
    # Limpa linhas fantasmas (vazias) do Google Sheets
    df = df.dropna(subset=['id']) if 'id' in df.columns else df

    st.sidebar.success("✅ Conectado à Planilha")
except Exception as e:
    st.error(f"❌ Erro Crítico de Conexão: {e}")
    st.info("Verifique se as 'Secrets' estão corretas e se a Google Drive API está ativa.")
    st.stop()

# 3. Navegação
tab1, tab2, tab3, tab4 = st.tabs(["📥 Entrada", "🧼 Máquinas", "🚀 Produção", "📊 Histórico"])

# --- ABA 1: ENTRADA ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Novo Recebimento de Roupa")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente / Hospital")
        peso = c2.number_input("Peso (kg)", 0.1, 500.0, step=0.1)
        obs = st.text_input("Observações de Entrada")
        
        if st.form_submit_button("REGISTRAR LOTE"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo_row = pd.DataFrame([{
                    "id": novo_id, 
                    "cli": cliente.upper(), 
                    "p_in": peso, 
                    "status": "Aguardando Lavagem",
                    "h_in": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(),
                    "detalhe_itens": obs
                }])
                df = pd.concat([df, novo_row], ignore_index=True)
                conn.update(data=df)
                st.toast(f"Lote {novo_id} registrado!", icon="✅")
                st.rerun()

# --- ABA 2: MÁQUINAS (LAVAGEM CONJUNTA) ---
with tab2:
    st.subheader("Processo de Lavagem")
    espera = df[df['status'] == "Aguardando Lavagem"]
    
    if not espera.empty:
        c1, c2 = st.columns([2, 1])
        lotes_lavar = c1.multiselect(
            "Selecione os lotes para a mesma máquina:", 
            espera['id'].tolist(),
            format_func=lambda x: f"Lote {x} - {df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)"
        )
        
        maq = c2.selectbox("Qual Máquina?", ["LAVADORA 01", "LAVADORA 02", "LAVADORA 03"])
        operador_lav = c2.text_input("Operador", key="op_lav")

        if st.button("🚀 INICIAR CICLO DE LAVAGEM"):
            if lotes_lavar and operador_lav:
                for lid in lotes_lavar:
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'] = "Secagem" # Próxima etapa automática
                    df.loc[idx, 'maquina'] = maq
                    df.loc[idx, 'resp'] = operador_lav.upper()
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                
                conn.update(data=df)
                st.success("Lavagem iniciada!")
                st.rerun()
    else:
        st.info("Nenhum lote na fila de espera.")

# --- ABA 3: PRODUÇÃO (FLUXO) ---
with tab3:
    st.subheader("Linha de Produção Ativa")
    # Mostra tudo que não é entrada nem entrega
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue"])]
    
    etapas = ["Secagem", "Passadeira", "Dobragem", "Empacotamento", "Gaiola", "Entregue"]

    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2])
            
            # Coluna 1: Dados do Lote
            c1.markdown(f"### {row['cli']}\n**ID:** `{row['id']}` | **Peso:** {row['p_in']}kg")
            c1.caption(f"Máquina: {row.get('maquina', 'N/A')}")
            
            # Coluna 2: Tempo na Etapa
            try:
                inicio_etapa = datetime.fromisoformat(str(row['etapa_inicio']))
                minutos = int((datetime.now() - inicio_etapa).total_seconds() // 60)
                c2.metric("⏱️ Tempo", f"{minutos} min", help=f"Início: {inicio_etapa.strftime('%H:%M')}")
                c2.write(f"**Etapa:** {row['status']}")
            except:
                c2.write("Erro no tempo")

            # Coluna 3: Ação
            idx_atual = etapas.index(row['status']) if row['status'] in etapas else 0
            prox_etapa = etapas[idx_atual + 1]
            
            op_atual = c3.text_input("Operador Responsável", key=f"op_{row['id']}")
            
            # Campo extra para itens (Checklist)
            detalhe = ""
            if row['status'] in ["Passadeira", "Dobragem"]:
                detalhe = c3.text_input("Lista de Itens (ex: 20 Lençóis, 10 Fronhas)", key=f"det_{row['id']}")

            if c3.button(f"Concluir e Mover para {prox_etapa}", key=f"btn_{row['id']}"):
                if op_atual:
                    df.at[i, 'status'] = prox_etapa
                    df.at[i, 'resp'] = op_atual.upper()
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    if detalhe:
                        df.at[i, 'detalhe_itens'] = detalhe
                    
                    conn.update(data=df)
                    st.rerun()
                else:
                    st.error("Informe quem está operando!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: HISTÓRICO ---
with tab4:
    st.subheader("Relatório de Movimentação")
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Exportar Planilha", df.to_csv(index=False).encode('utf-8'), "lavanderia.csv", "text/csv")
import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# 1. Configuração de Página (DEVE SER A PRIMEIRA LINHA)
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

# Estilo Visual
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .status-card { border: 1px solid #ddd; padding: 20px; border-radius: 12px; background-color: #ffffff; margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🧺 SISTEMA LAVANDERIA - V26")

# 2. Conexão com Google Sheets
# IMPORTANTE: Verifique se este link é o que aparece na barra do navegador (terminando em /edit...)
URL_PLANILHA = "COLE_AQUI_O_LINK_DA_SUA_PLANILHA"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # Lendo os dados - Usamos ttl=0 para atualização em tempo real
    df = conn.read(spreadsheet=URL_PLANILHA, ttl=0)
    
    # Tratamento para o erro de 'Response [200]' ou DataFrame vazio
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        # Cria um DataFrame inicial se a planilha estiver vazia
        cols = ["id", "cli", "p_in", "status", "maquina", "resp", "detalhe_itens", "h_in", "etapa_inicio"]
        df = pd.DataFrame(columns=cols)
    else:
        # Garante que as colunas necessárias existam no DF carregado
        cols_necessarias = ["id", "cli", "p_in", "status", "maquina", "resp", "detalhe_itens", "h_in", "etapa_inicio"]
        for col in cols_necessarias:
            if col not in df.columns:
                df[col] = ""
    
    # Limpa linhas fantasmas (vazias) do Google Sheets
    df = df.dropna(subset=['id']) if 'id' in df.columns else df

    st.sidebar.success("✅ Conectado à Planilha")
except Exception as e:
    st.error(f"❌ Erro Crítico de Conexão: {e}")
    st.info("Verifique se as 'Secrets' estão corretas e se a Google Drive API está ativa.")
    st.stop()

# 3. Navegação
tab1, tab2, tab3, tab4 = st.tabs(["📥 Entrada", "🧼 Máquinas", "🚀 Produção", "📊 Histórico"])

# --- ABA 1: ENTRADA ---
with tab1:
    with st.form("entrada_lote", clear_on_submit=True):
        st.subheader("Novo Recebimento de Roupa")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Cliente / Hospital")
        peso = c2.number_input("Peso (kg)", 0.1, 500.0, step=0.1)
        obs = st.text_input("Observações de Entrada")
        
        if st.form_submit_button("REGISTRAR LOTE"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo_row = pd.DataFrame([{
                    "id": novo_id, 
                    "cli": cliente.upper(), 
                    "p_in": peso, 
                    "status": "Aguardando Lavagem",
                    "h_in": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(),
                    "detalhe_itens": obs
                }])
                df = pd.concat([df, novo_row], ignore_index=True)
                conn.update(data=df)
                st.toast(f"Lote {novo_id} registrado!", icon="✅")
                st.rerun()

# --- ABA 2: MÁQUINAS (LAVAGEM CONJUNTA) ---
with tab2:
    st.subheader("Processo de Lavagem")
    espera = df[df['status'] == "Aguardando Lavagem"]
    
    if not espera.empty:
        c1, c2 = st.columns([2, 1])
        lotes_lavar = c1.multiselect(
            "Selecione os lotes para a mesma máquina:", 
            espera['id'].tolist(),
            format_func=lambda x: f"Lote {x} - {df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)"
        )
        
        maq = c2.selectbox("Qual Máquina?", ["LAVADORA 01", "LAVADORA 02", "LAVADORA 03"])
        operador_lav = c2.text_input("Operador", key="op_lav")

        if st.button("🚀 INICIAR CICLO DE LAVAGEM"):
            if lotes_lavar and operador_lav:
                for lid in lotes_lavar:
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'] = "Secagem" # Próxima etapa automática
                    df.loc[idx, 'maquina'] = maq
                    df.loc[idx, 'resp'] = operador_lav.upper()
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                
                conn.update(data=df)
                st.success("Lavagem iniciada!")
                st.rerun()
    else:
        st.info("Nenhum lote na fila de espera.")

# --- ABA 3: PRODUÇÃO (FLUXO) ---
with tab3:
    st.subheader("Linha de Produção Ativa")
    # Mostra tudo que não é entrada nem entrega
    em_fluxo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue"])]
    
    etapas = ["Secagem", "Passadeira", "Dobragem", "Empacotamento", "Gaiola", "Entregue"]

    for i, row in em_fluxo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.5, 1, 2])
            
            # Coluna 1: Dados do Lote
            c1.markdown(f"### {row['cli']}\n**ID:** `{row['id']}` | **Peso:** {row['p_in']}kg")
            c1.caption(f"Máquina: {row.get('maquina', 'N/A')}")
            
            # Coluna 2: Tempo na Etapa
            try:
                inicio_etapa = datetime.fromisoformat(str(row['etapa_inicio']))
                minutos = int((datetime.now() - inicio_etapa).total_seconds() // 60)
                c2.metric("⏱️ Tempo", f"{minutos} min", help=f"Início: {inicio_etapa.strftime('%H:%M')}")
                c2.write(f"**Etapa:** {row['status']}")
            except:
                c2.write("Erro no tempo")

            # Coluna 3: Ação
            idx_atual = etapas.index(row['status']) if row['status'] in etapas else 0
            prox_etapa = etapas[idx_atual + 1]
            
            op_atual = c3.text_input("Operador Responsável", key=f"op_{row['id']}")
            
            # Campo extra para itens (Checklist)
            detalhe = ""
            if row['status'] in ["Passadeira", "Dobragem"]:
                detalhe = c3.text_input("Lista de Itens (ex: 20 Lençóis, 10 Fronhas)", key=f"det_{row['id']}")

            if c3.button(f"Concluir e Mover para {prox_etapa}", key=f"btn_{row['id']}"):
                if op_atual:
                    df.at[i, 'status'] = prox_etapa
                    df.at[i, 'resp'] = op_atual.upper()
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    if detalhe:
                        df.at[i, 'detalhe_itens'] = detalhe
                    
                    conn.update(data=df)
                    st.rerun()
                else:
                    st.error("Informe quem está operando!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: HISTÓRICO ---
with tab4:
    st.subheader("Relatório de Movimentação")
    st.dataframe(df, use_container_width=True)
    st.download_button("📥 Exportar Planilha", df.to_csv(index=False).encode('utf-8'), "lavanderia.csv", "text/csv")

# 1. Configuração de Página
st.set_page_config(page_title="Lavo e Levo V26", page_icon="🧺", layout="wide")

# Estilo Industrial
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .status-card { border: 1px solid #ddd; padding: 15px; border-radius: 10px; background-color: #f8f9fa; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🧺 SISTEMA LAVANDERIA - V26")

# 2. Conexão com Google Sheets
# Substitua o link abaixo pelo link da sua planilha se não estiver nas Secrets
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1omLRgifWEqgU9_EsQRAqKm9ZY0Lw2jeaxmLP-KkCVmQ/edit?pli=1&gid=0#gid=0"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=URL_PLANILHA, ttl="0")
    
    # Garantir que colunas essenciais existam
    cols_necessarias = ["id", "cli", "p_in", "status", "maquina", "resp", "detalhe_itens", "h_in", "etapa_inicio"]
    for col in cols_necessarias:
        if col not in df.columns:
            df[col] = None
            
    st.sidebar.success("✅ Sistema Online")
except Exception as e:
    st.error(f"❌ Erro de Conexão: {e}")
    st.stop()

# 3. Navegação por Abas
tab1, tab2, tab3, tab4 = st.tabs(["📥 Entrada", "🧼 Lavagem (Máquinas)", "🚀 Fluxo de Produção", "📊 Histórico"])

# --- ABA 1: RECEBIMENTO ---
with tab1:
    with st.form("novo_lote", clear_on_submit=True):
        st.subheader("Registrar Novo Lote")
        c1, c2 = st.columns(2)
        cliente = c1.text_input("Nome do Hospital / Cliente")
        peso = c2.number_input("Peso Total (kg)", 0.1)
        obs_ini = st.text_input("Observação de Entrada")
        
        if st.form_submit_button("GERAR LOTE"):
            if cliente:
                novo_id = datetime.now().strftime("%d%H%M%S")
                novo_lote = pd.DataFrame([{
                    "id": novo_id, 
                    "cli": cliente.upper(), 
                    "p_in": peso, 
                    "status": "Aguardando Lavagem",
                    "h_in": datetime.now().strftime("%H:%M"),
                    "etapa_inicio": datetime.now().isoformat(),
                    "detalhe_itens": obs_ini
                }])
                df = pd.concat([df, novo_lote], ignore_index=True)
                conn.update(data=df)
                st.success(f"Lote {novo_id} criado!")
                st.rerun()

# --- ABA 2: MÁQUINAS (LAVAGEM CONJUNTA) ---
with tab2:
    st.subheader("Gestão de Lavadoras")
    espera = df[df['status'] == "Aguardando Lavagem"]
    
    if not espera.empty:
        c1, c2 = st.columns([2, 1])
        lotes_selecionados = c1.multiselect(
            "Selecione os lotes para a mesma máquina:", 
            espera['id'].tolist(),
            format_func=lambda x: f"ID {x} - {df[df['id']==x]['cli'].values[0]} ({df[df['id']==x]['p_in'].values[0]}kg)"
        )
        
        maquina = c2.selectbox("Máquina:", ["MÁQUINA 01", "MÁQUINA 02", "MÁQUINA 03", "MÁQUINA 04"])
        operador = c2.text_input("Operador da Lavagem", key="op_lav")

        if st.button("🚀 INICIAR LAVAGEM CONJUNTA"):
            if lotes_selecionados and operador:
                for lid in lotes_selecionados:
                    idx = df[df['id'] == lid].index
                    df.loc[idx, 'status'] = "Secagem" # Move para a próxima etapa após lavagem
                    df.loc[idx, 'maquina'] = maquina
                    df.loc[idx, 'resp'] = operador.upper()
                    df.loc[idx, 'etapa_inicio'] = datetime.now().isoformat()
                
                conn.update(data=df)
                st.balloons()
                st.rerun()
            else:
                st.warning("Selecione os lotes e informe o operador!")
    else:
        st.info("Nenhum lote aguardando lavagem.")

# --- ABA 3: FLUXO DE PRODUÇÃO (TIME REAL) ---
with tab3:
    st.subheader("Acompanhamento de Etapas")
    # Filtra o que está em processo (exceto entrada e entregue)
    em_processo = df[~df['status'].isin(["Aguardando Lavagem", "Entregue"])]
    
    fluxo_etapas = ["Secagem", "Passadeira", "Dobragem", "Empacotamento", "Gaiola", "Entregue"]

    for i, row in em_processo.iterrows():
        with st.container():
            st.markdown(f"<div class='status-card'>", unsafe_allow_html=True)
            col_info, col_tempo, col_acao = st.columns([2, 1, 2])
            
            # Info do Lote
            col_info.markdown(f"**{row['cli']}** (ID: {row['id']})")
            col_info.caption(f"Status Atual: `{row['status']}` | Máquina: {row.get('maquina', 'N/A')}")
            
            # Cronômetro
            inicio = datetime.fromisoformat(str(row['etapa_inicio']))
            decorrido = (datetime.now() - inicio).total_seconds() // 60
            col_tempo.metric("⏱️ Tempo", f"{int(decorrido)} min")
            
            # Ação de Avanço
            idx_atual = fluxo_etapas.index(row['status']) if row['status'] in fluxo_etapas else 0
            proximo = fluxo_etapas[idx_atual + 1] if idx_atual + 1 < len(fluxo_etapas) else "Entregue"
            
            op_resp = col_acao.text_input("Operador", key=f"resp_{row['id']}")
            
            # Checklist Especial para Dobragem/Passadeira
            itens_contagem = ""
            if row['status'] in ["Passadeira", "Dobragem"]:
                itens_contagem = col_acao.text_input("Contagem (Ex: 10 Lençóis, 5 Fronhas)", key=f"itens_{row['id']}")

            if col_acao.button(f"➡️ Mover para {proximo}", key=f"btn_{row['id']}"):
                if op_resp:
                    df.at[i, 'status'] = proximo
                    df.at[i, 'resp'] = op_resp.upper()
                    df.at[i, 'etapa_inicio'] = datetime.now().isoformat()
                    if itens_contagem:
                        df.at[i, 'detalhe_itens'] = itens_contagem
                    
                    conn.update(data=df)
                    st.rerun()
                else:
                    st.error("Informe o Operador!")
            st.markdown("</div>", unsafe_allow_html=True)

# --- ABA 4: HISTÓRICO ---
with tab4:
    st.subheader("Histórico Geral")
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Relatório CSV", csv, "lavanderia_v26.csv", "text/csv")
