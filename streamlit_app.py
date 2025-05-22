import streamlit as st
import pandas as pd
from datetime import date
import numpy as np
import os

st.set_page_config(layout="wide")
st.title("PCMA - PLANO DE AÇÃO 2025")

# Nome do arquivo onde os dados serão salvos
DATA_FILE = "planos_de_acao.csv"

# Definir a estrutura e os dtypes esperados para o DataFrame
expected_dtypes = {
    "Nº Sequência": 'Int64', # Usar 'Int64' para permitir NaN em inteiros
    "Data Fato": 'datetime64[ns]',
    "Responsável": 'str',
    "Descreva sua tarefa": 'str',
    "Ação/Etapa": 'str',
    "Tipo Ação": 'str',
    "Início Previsto": 'datetime64[ns]',
    "Término Previsto": 'datetime64[ns]',
    "Início Real": 'datetime64[ns]',
    "Término Real": 'datetime64[ns]',
    "Status": 'str',
    "Observação": 'str'
}

# --- Lógica de Carregamento de Dados ---
if 'df_planos' not in st.session_state:
    if os.path.exists(DATA_FILE):
        try:
            # Carregar o CSV e, em seguida, aplicar os dtypes esperados
            temp_df = pd.read_csv(
                DATA_FILE,
                parse_dates=["Data Fato", "Início Previsto", "Término Previsto", "Início Real", "Término Real"]
            )
            # Converter para os dtypes esperados
            for col, dtype in expected_dtypes.items():
                if col in temp_df.columns:
                    if 'datetime' in str(dtype):
                        # Use errors='coerce' para converter valores inválidos para NaT
                        temp_df[col] = pd.to_datetime(temp_df[col], errors='coerce', dayfirst=True) # dayfirst para DD/MM/YYYY
                    elif 'Int64' in str(dtype):
                        # Convert to nullable integer (Int64)
                        temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce').astype('Int64')
                    else:
                        temp_df[col] = temp_df[col].astype(dtype)
                else: # Se a coluna não existir no CSV, adicione-a com o dtype correto
                    temp_df[col] = pd.Series(dtype=dtype)

            st.session_state.df_planos = temp_df

        except Exception as e:
            st.error(f"Erro ao carregar dados do arquivo CSV. Criando DataFrame vazio: {e}")
            # Se der erro ao carregar, inicializa um DataFrame vazio com dtypes definidos
            initial_data_empty = {col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()}
            st.session_state.df_planos = pd.DataFrame(initial_data_empty)
    else:
        # Se o arquivo não existir, cria um DataFrame vazio com os dtypes definidos
        initial_data_empty = {col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()}
        st.session_state.df_planos = pd.DataFrame(initial_data_empty)

# --- Função para Salvar o DataFrame ---
def save_data():
    # Antes de salvar, certifique-se de que os dtypes estão consistentes (especialmente para Int64)
    # Por exemplo, converter Int64 para int se não houver NaNs para evitar problemas de compatibilidade no CSV
    # Mas to_csv já lida bem com Int64 em geral
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
    # As opções para Status e Observação aqui devem ser as mesmas do st.selectbox no formulário
    status = st.selectbox("Status", ["Sem Data", "Atrasada", "Planejada", "Cancelada", "Em Andamento", "Concluída"])
    observacao = st.text_area("Observação", placeholder="Adicione observações aqui (opcional)")

    submitted = st.form_submit_button("Adicionar Plano")

if submitted:
    next_sequence_num = 1
    if not st.session_state.df_planos.empty:
        # Pega o maior número de sequência (Int64, que lida com NaN) e converte para int
        # Se houver NaN, fillna(0) para garantir que max() funcione
        next_sequence_num = st.session_state.df_planos["Nº Sequência"].fillna(0).max() + 1
    
    # Criar um dicionário com os dados do novo registro
    novo_registro = {
        "Nº Sequência": next_sequence_num,
        "Data Fato": data_fato,
        "Responsável": responsavel,
        "Descreva sua tarefa": tarefa,
        "Ação/Etapa": acaoetapa,
        "Tipo Ação": tipoacao,
        "Início Previsto": pd.NaT,
        "Término Previsto": pd.NaT,
        "Início Real": pd.NaT,
        "Término Real": pd.NaT,
        "Status": status, # Este é o valor vindo do st.selectbox do formulário
        "Observação": observacao # Este é o valor vindo do st.text_area do formulário
    }

    # Adicionar o novo registro ao DataFrame
    # pd.concat vai tentar manter os dtypes se forem consistentes
    st.session_state.df_planos = pd.concat(
        [st.session_state.df_planos, pd.DataFrame([novo_registro])],
        ignore_index=True
    ).astype(expected_dtypes) # Força os dtypes novamente após o concat para garantir

    st.success("Novo plano de ação adicionado com sucesso!")
    save_data()

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
            "Início Previsto": st.column_config.DateColumn("Início Previsto", format="DD/MM/YYYY", help="Data prevista de início da tarefa"),
            "Término Previsto": st.column_config.DateColumn("Término Previsto", format="DD/MM/YYYY", help="Data prevista de término da tarefa"),
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
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=["Sem Data", "Atrasada", "Planejada", "Cancelada", "Em Andamento", "Concluída"],
                required=True,
                help="Status atual da tarefa"
            ),
            "Observação": st.column_config.TextColumn(
                "Observação",
                help="Qualquer observação relevante sobre a tarefa",
                width="large"
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
