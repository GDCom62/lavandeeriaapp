import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Configuração Profissional
st.set_page_config(page_title="Lavo e Levo Cloud", page_icon="🧺", layout="wide")

# Conectando à Planilha Google (Configurada nos Secrets)
conn = st.connection("gsheets", type=GSheetsConnection)

# Lendo os dados atuais da Planilha (ttl=0 para ler em tempo real)
df = conn.read(ttl="0")

# Se a planilha estiver vazia, cria a estrutura inicial
if df.empty:
    df = pd.DataFrame(columns=["id", "cli", "p_in", "p_out", "tipo", "status", "resp", "itens", "gaiola", "mot", "h_in"])

st.title("🧺 LAVANDERIA LAVO E LEVO - GESTÃO TOTAL")

# Função para salvar na nuvem
def atualizar_nuvem(dados_atualizados):
    conn.update(data=dados_atualizados)
    st.cache_data.clear()

# --- 1. RECEBIMENTO (LAVAGEM) ---
with st.expander("➕ NOVO LOTE / LAVAGEM", expanded=True):
    with st.form("entrada", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cli = col1.text_input("Cliente:")
        p_in = col2.number_input("Peso Entrada (kg):", 0.1)
        tipo = col1.selectbox("Tipo:", ["Processo Novo", "Relave"])
        r1 = col2.text_input("Responsável Lavagem:")
        
        if st.form_submit_button("INICIAR PROCESSO"):
            if cli and r1:
                novo_lote = pd.DataFrame([{
                    "id": len(df) + 1, "cli": cli.upper(), "p_in": p_in, "p_out": 0.0,
                    "tipo": tipo, "status": "Lavagem", "resp": r1, "itens": "", 
                    "gaiola": "", "mot": "", "h_in": datetime.now().strftime("%H:%M")
                }])
                df = pd.concat([df, novo_lote], ignore_index=True)
                atualizar_nuvem(df)
                st.rerun()

st.write("---")
st.subheader("📋 Fila de Trabalho Ativa")

# Filtrar apenas o que não foi entregue
df_ativos = df[df['status'] != "Entregue"]

for i, row in df_ativos.iterrows():
    with st.container(border=True):
        st.write(f"**Lote #{row['id']} - {row['cli']}** ({row['p_in']}kg)")
        st.caption(f"📍 Etapa: {row['status']} | Equipe: {row['resp']}")

        # --- FLUXO DAS 7 ETAPAS ---
        
        # 2. LAVAGEM -> SECAGEM
        if row['status'] == "Lavagem":
            r2 = st.text_input("Equipe p/ Transporte Secagem:", key=f"r2_{row['id']}")
            if st.button("➡️ Enviar para Secadora", key=f"b2_{row['id']}"):
                if r2:
                    df.at[i, 'status'], df.at[i, 'resp'] = "Secagem", r2
                    atualizar_nuvem(df) ; st.rerun()

        # 3. OPERAÇÃO SECADORA -> ESCOLHA DESTINO
        elif row['status'] == "Secagem":
            r3 = st.text_input("Equipe Operação Secadora:", key=f"r3_{row['id']}")
            c_p, c_d = st.columns(2)
            if c_p.button("👔 Ir p/ Passadeira", key=f"bp_{row['id']}"):
                if r3:
                    df.at[i, 'status'], df.at[i, 'resp'] = "Passadeira", r3
                    atualizar_nuvem(df) ; st.rerun()
            if c_d.button("📦 Ir p/ Dobragem", key=f"bd_{row['id']}"):
                if r3:
                    df.at[i, 'status'], df.at[i, 'resp'] = "Dobragem", r3
                    atualizar_nuvem(df) ; st.rerun()

        # 4. PROCESSAMENTO -> CONTAGEM
        elif row['status'] in ["Passadeira", "Dobragem"]:
            r4 = st.text_input("Equipe Acabamento/Contagem:", key=f"r4_{row['id']}")
            if st.button("🔢 Ir para Contagem", key=f"bc_{row['id']}"):
                if r4:
                    df.at[i, 'status'], df.at[i, 'resp'] = "Contagem", r4
                    atualizar_nuvem(df) ; st.rerun()

        # 5. CONTAGEM E LISTA DE PEÇAS
        elif row['status'] == "Contagem":
            st.write(f"Itens já contados: {row['itens']}")
            t_p = st.text_input("Tipo (ex: Fronha):", key=f"tp_{row['id']}")
            q_p = st.number_input("Qtd:", 1, key=f"qp_{row['id']}")
            if st.button("➕ Adicionar Item", key=f"ba_{row['id']}"):
                nova_lista = f"{row['itens']}, {t_p}({q_p}un)" if row['itens'] else f"{t_p}({q_p}un)"
                df.at[i, 'itens'] = nova_lista
                atualizar_nuvem(df) ; st.rerun()
            
            if st.button("🎁 Finalizar e Pesar Gaiola", key=f"bf_{row['id']}"):
                df.at[i, 'status'] = "Gaiola"
                atualizar_nuvem(df) ; st.rerun()

        # 6. GAIOLA, PESAGEM E MOTORISTA
        elif row['status'] == "Gaiola":
            st.write("**⚖️ Saída e Logística**")
            p_out = st.number_input("Peso Saída (kg):", 0.1, key=f"po_{row['id']}")
            gaiola = st.text_input("Nº da Gaiola:", key=f"g_{row['id']}")
            mot = st.selectbox("Motorista:", ["Selecione...", "Carlos", "Ricardo", "Fábio"], key=f"m_{row['id']}")
            
            # Alerta de Perda (Limite 5%)
            if p_out > 0:
                perda = ((row['p_in'] - p_out) / row['p_in']) * 100
                if perda > 5.0: st.error(f"⚠️ PERDA ALTA: {perda:.1f}%")
                else: st.success(f"✅ Perda: {perda:.1f}%")

            if st.button("🚚 LIBERAR PARA ENTREGA", key=f"be_{row['id']}"):
                if p_out > 0 and mot != "Selecione...":
                    df.at[i, 'p_out'] = p_out
                    df.at[i, 'status'] = "Entregue"
                    df.at[i, 'mot'] = mot
                    df.at[i, 'gaiola'] = gaiola
                    atualizar_nuvem(df) ; st.rerun()

# --- RELATÓRIO FINAL ---
st.write("---")
if st.checkbox("📊 Ver Relatório Completo (Planilha Cloud)"):
    st.dataframe(df)
