import streamlit as st
import pandas as pd
from datetime import date
import numpy as np
import os

st.set_page_config(layout="wide")
st.title("PCMA - PLANO DE AÇÃO 2025")

# Nome do arquivo onde os dados serão salvos
DATA_FILE = "planos_de_acao.csv"

# --- Lógica de Carregamento de Dados ---
if 'df_planos' not in st.session_state:
    if os.path.exists(DATA_FILE):
        try:
            st.session_state.df_planos = pd.read_csv(
                DATA_FILE,
                parse_dates=["Data Fato", "Início Previsto", "Término Previsto", "Início Real", "Término Real"],
                dtype={"Nº Sequência": int}
            )
            for col in ["Início Real", "Término Real"]:
                st.session_state.df_planos[col] = st.session_state.df_planos[col].replace({np.nan: pd.NaT})

        except Exception as e:
            st.error(f"Erro ao carregar dados do arquivo CSV: {e}")
            st.session_state.df_planos = pd.DataFrame(columns=[
                "Nº Sequência", "Data Fato", "Responsável", "Descreva sua tarefa", "Ação/Etapa", "Tipo Ação",
                "Início Previsto", "Término Previsto", "Início Real", "Término Real", "Status", "Observação"
            ])
            st.session_state.df_planos = st.session_state.df_planos.astype({
                "Nº Sequência": 'int',
                "Data Fato": 'datetime64[ns]',
                "Início Previsto": 'datetime64[ns]',
                "Término Previsto": 'datetime64[ns]',
                "Início Real": 'datetime64[ns]',
                "Término Real": 'datetime64[ns]'
            })
    else:
        initial_data = {
            "Nº Sequência": pd.Series(dtype='int'),
            "Data Fato": pd.Series(dtype='datetime64[ns]'),
            "Responsável": pd.Series(dtype='str'),
            "Descreva sua tarefa": pd.Series(dtype='str'),
            "Ação/Etapa": pd.Series(dtype='str'),
            "Tipo Ação": pd.Series(dtype='str'),
            "Início Previsto": pd.Series(dtype='datetime64[ns]'),
            "Término Previsto": pd.Series(dtype='datetime64[ns]'),
            "Início Real": pd.Series(dtype='datetime64[ns]'),
            "Término Real": pd.Series(dtype='datetime64[ns]'),
            "Status": pd.Series(dtype='str'),
            "Observação": pd.Series(dtype='str')
        }
        st.session_state.df_planos = pd.DataFrame(initial_data)

# --- Função para Salvar o DataFrame ---
def save_data():
    st.session_state.df_planos.to_csv(DATA_FILE, index=False)
    st.success("Dados salvos com sucesso no arquivo CSV!")
    st.balloons()

st.subheader("Adicionar Novo Plano de Ação")

with st.form("add_plano"):
    data_fato = st.date_input("Data Fato", format="DD/MM/YYYY", value=date.today())
    responsavel = st.text_input("Responsável", placeholder="Nome do responsável")
    tarefa = st.text_area("Descreva sua tarefa", placeholder="Detalhes da tarefa")
    acaoetapa = st.selectbox("Ação/Etapa", ["Ação", "Etapa"])
    tipoacao = st.selectbox("Tipo Ação", ["Ação de Melhoria", "Ação Imediata", "Ação Corretiva"])
    inicioprevisto = st.date_input("Início Previsto", format="DD/MM/YYYY", value=date.today())
    terminoprevisto = st.date_input("Término Previsto", format="DD/MM/YYYY", value=date.today())
    status = st.selectbox("Status", ["Sem Data", "Atrasada", "Planejada", "Cancelada", "Em Andamento", "Concluída"])
    observacao = st.text_area("Observação", placeholder="Adicione observações aqui (opcional)")

    submitted = st.form_submit_button("Adicionar Plano")

if submitted:
    next_sequence_num = 1
    if not st.session_state.df_planos.empty:
        next_sequence_num = st.session_state.df_planos["Nº Sequência"].fillna(0).max() + 1

    novo_registro = {
        "Nº Sequência": next_sequence_num,
        "Data Fato": data_fato,
        "Responsável": responsavel,
        "Descreva sua tarefa": tarefa,
        "Ação/Etapa": acaoetapa,
        "Tipo Ação": tipoacao,
        "Início Previsto": inicioprevisto,
        "Término Previsto": terminoprevisto,
        "Início Real": pd.NaT,
        "Término Real": pd.NaT,
        "Status": status,
        "Observação": observacao
    }

    st.session_state.df_planos = pd.concat(
        [st.session_state.df_planos, pd.DataFrame([novo_registro])],
        ignore_index=True
    )
    st.success("Novo plano de ação adicionado com sucesso!")
    save_data()

---

st.subheader("Plano de Ação")

if not st.session_state.df_planos.empty:
    df_exibicao = st.session_state.df_planos.sort_values(by="Nº Sequência", ascending=True)

    edited_df = st.data_editor(
        df_exibicao,
        num_rows="dynamic",
        column_config={
            "Nº Sequência": st.column_config.NumberColumn("Nº Sequência", disabled=True),
            "Data Fato": st.column_config.DateColumn("Data Fato", format="DD/MM/YYYY", disabled=True),
            "Responsável": st.column_config.TextColumn("Responsável", disabled=True),
            "Descreva sua tarefa": st.column_config.TextColumn("Descreva sua tarefa", disabled=True),
            "Ação/Etapa": st.column_config.TextColumn("Ação/Etapa", disabled=True),
            "Tipo Ação": st.column_config.TextColumn("Tipo Ação", disabled=True),
            "Início Previsto": st.column_config.DateColumn("Início Previsto", format="DD/MM/YYYY", disabled=True),
            "Término Previsto": st.column_config.DateColumn("Término Previsto", format="DD/MM/YYYY", disabled=True),
            "Início Real": st.column_config.DateColumn(
                "Início Real",
                format="DD/MM/YYYY",
                help="Data real de início da tarefa"
            ),
            "Término Real": st.column_config.DateColumn(
                "Término Real",
                format="DD/MM/YYYY",
                help="Data real de término da tarefa"
            ),
            # --- Alterações para Status e Observação ---
            "Status": st.column_config.SelectboxColumn( # Usando SelectboxColumn para Status
                "Status",
                options=["Sem Data", "Atrasada", "Planejada", "Cancelada", "Em Andamento", "Concluída"],
                required=True, # Torna a seleção obrigatória
                help="Status atual da tarefa"
            ),
            "Observação": st.column_config.TextColumn( # Usando TextColumn para Observação
                "Observação",
                help="Qualquer observação relevante sobre a tarefa",
                width="large" # Opcional: para dar mais espaço à observação
            ),
        },
        hide_index=True,
        use_container_width=True
    )

    if not edited_df.equals(df_exibicao):
        st.session_state.df_planos = edited_df
        save_data()
        st.success("Tabela atualizada!")
else:
    st.info("Nenhum plano de ação adicionado ainda. Use o formulário acima para começar!")
