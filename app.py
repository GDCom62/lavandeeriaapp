elif menu == "3. Acabamento":
    st.header("🧺 Dobra e Passadeira")
    
    # Busca lotes que saíram da secagem
    df_acab = consultar_db_safe("SELECT id, hospital, status FROM lotes WHERE status IN ('Secando', 'Pronto')")
    
    if not df_acab.empty:
        sel = st.selectbox("Lote para acabamento", df_acab['id'].astype(str) + " - " + df_acab['hospital'])
        id_lote = int(sel.split(" - "))
        status_atual = df_acab[df_acab['id'] == id_lote]['status'].values[0]

        if status_atual == 'Secando':
            st.subheader("📝 Contagem de Peças")
            st.info("Altere as quantidades na tabela abaixo:")

            # Criamos uma lista base de itens
            itens_padrao = [
                {"Item": "Lençóis", "Quantidade": 0},
                {"Item": "Fronhas", "Quantidade": 0},
                {"Item": "Oleados", "Quantidade": 0},
                {"Item": "Pijamas", "Quantidade": 0},
                {"Item": "Camisolas", "Quantidade": 0},
                {"Item": "Campos", "Quantidade": 0},
                {"Item": "Colchas", "Quantidade": 0}
            ]
            df_itens = pd.DataFrame(itens_padrao)

            # O Data Editor permite editar a tabela como no Excel
            edicao = st.data_editor(
                df_itens, 
                column_config={
                    "Quantidade": st.column_config.NumberColumn(min_value=0, step=1)
                },
                disabled=["Item"], # Bloqueia o nome do item, permite editar só a quantidade
                hide_index=True,
                use_container_width=True,
                key=f"editor_{id_lote}"
            )

            if st.button("✅ Finalizar e Salvar Contagem", type="primary"):
                dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 1. Atualiza o status do lote
                executar_query("""UPDATE lotes SET status='Pronto', fim_secagem=:dt, 
                               inicio_acabamento=:dt, operador_acabamento=:op WHERE id=:id""",
                               {"dt": dt, "op": st.session_state['operador'], "id": id_lote})
                
                # 2. Salva apenas os itens que tiveram quantidade maior que zero
                for _, linha in edicao.iterrows():
                    if linha['Quantidade'] > 0:
                        executar_query("INSERT INTO contagem_itens (lote_id, item, quantidade) VALUES (:id, :it, :q)",
                                       {"id": id_lote, "it": linha['Item'], "q": linha['Quantidade']})
                
                st.success("Contagem registrada com sucesso!")
                st.rerun()

        else:
            # Opção de Estorno se o colaborador errou a contagem
            st.warning("Este lote já foi contado.")
            if st.button("⏪ Estornar (Refazer Contagem)"):
                executar_query("UPDATE lotes SET status='Secando', fim_secagem=NULL, inicio_acabamento=NULL WHERE id=:id", {"id": id_lote})
                executar_query("DELETE FROM contagem_itens WHERE lote_id=:id", {"id": id_lote})
                st.rerun()
    else:
        st.info("Nenhum lote vindo da secagem.")
