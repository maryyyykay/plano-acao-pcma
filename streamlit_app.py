import streamlit as st
import pandas as pd
from datetime import date
import numpy as np
import os

st.set_page_config(layout="wide")
st.title("🎍 PCMA - PLANO DE AÇÃO 2025")

# Nome do arquivo onde os dados serão salvos
DATA_FILE = "planos_de_acao.csv"

# Definir a estrutura e os dtypes esperados para o DataFrame

expected_dtypes = {
    "Nº Sequência": 'Int64',
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
            temp_df = pd.read_csv(
                DATA_FILE,
                parse_dates=["Data Fato", "Início Previsto", "Término Previsto", "Início Real", "Término Real"]
            )
            for col, dtype in expected_dtypes.items():
                if col in temp_df.columns:
                    if 'datetime' in str(dtype):
                        temp_df[col] = pd.to_datetime(temp_df[col], errors='coerce', dayfirst=True)
                    elif 'Int64' in str(dtype):
                        temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce').astype('Int64')
                    else:
                        temp_df[col] = temp_df[col].astype(dtype)
                else:
                    temp_df[col] = pd.Series(dtype=dtype)
            st.session_state.df_planos = temp_df
        except Exception as e:
            st.error(f"Erro ao carregar dados do arquivo CSV. Criando DataFrame vazio: {e}")
            initial_data_empty = {col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()}
            st.session_state.df_planos = pd.DataFrame(initial_data_empty)
    else:
        initial_data_empty = {col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()}
        st.session_state.df_planos = pd.DataFrame(initial_data_empty)

# --- Função para Salvar o DataFrame ---
def save_data():
    st.session_state.df_planos.to_csv(DATA_FILE, index=False)
    st.success("Dados salvos com sucesso no arquivo CSV!")
    st.balloons()

# --- Função para limpar os inputs do formulário ---
def clear_form():
    st.session_state.data_fato_key = date.today()
    st.session_state.responsavel_key = ""
    st.session_state.tarefa_key = ""
    st.session_state.acaoetapa_key = "Ação"
    st.session_state.tipoacao_key = "Ação de Melhoria"
    st.session_state.status_key = "Sem Data"
    st.session_state.observacao_key = ""

# --- Controle de navegação na barra lateral ---
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Plano de Ação" # Página inicial padrão

if 'selected_responsavel' not in st.session_state:
    st.session_state.selected_responsavel = None

# Mova a inicialização das chaves do formulário para fora do bloco 'Adicionar Tarefa'
# Isso garante que elas sejam definidas apenas uma vez na inicialização do script
# ou quando o formulário é limpo (via clear_form()).
if 'data_fato_key' not in st.session_state:
    st.session_state.data_fato_key = date.today()
if 'responsavel_key' not in st.session_state:
    st.session_state.responsavel_key = ""
if 'tarefa_key' not in st.session_state:
    st.session_state.tarefa_key = ""
if 'acaoetapa_key' not in st.session_state:
    st.session_state.acaoetapa_key = "Ação"
if 'tipoacao_key' not in st.session_state:
    st.session_state.tipoacao_key = "Ação de Melhoria"
if 'status_key' not in st.session_state:
    st.session_state.status_key = "Sem Data"
if 'observacao_key' not in st.session_state:
    st.session_state.observacao_key = ""


# --- Barra Lateral ---
st.sidebar.title("Navegação")

# Botão para ver todos os planos
if st.sidebar.button("Plano de Ação", key="view_all_plans_button"):
    st.session_state.current_view = "Plano de Ação"
    st.session_state.selected_responsavel = None
    st.rerun()

# Botão para adicionar novo plano
if st.sidebar.button("Adicionar Nova Tarefa", key="add_new_plan_button"):
    st.session_state.current_view = "Adicionar Tarefa"
    st.session_state.selected_responsavel = None
    clear_form() # Limpa o formulário ao ir para a tela de adicionar nova tarefa
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Planos por Responsável")

# Obtém a lista única de responsáveis do DataFrame
if not st.session_state.df_planos.empty:
    responsaveis = st.session_state.df_planos["Responsável"].dropna().unique().tolist()
    responsaveis.sort() # Opcional: ordenar por nome
    
    for responsavel in responsaveis:
        if st.sidebar.button(responsavel, key=f"responsavel_{responsavel.replace(' ', '_')}"):
            st.session_state.current_view = "Filtrado por Responsável"
            st.session_state.selected_responsavel = responsavel
            st.rerun()
else:
    st.sidebar.info("Nenhum responsável encontrado ainda.")

# --- Conteúdo Principal ---
if st.session_state.current_view == "Adicionar Tarefa":
    st.subheader("Adicionar Nova Tarefa")

    with st.form("add_plano"):
        # Agora as chaves da session_state já estarão inicializadas
        data_fato = st.date_input("Data Fato", format="DD/MM/YYYY", value=st.session_state.data_fato_key, key="data_fato_key")
        responsavel = st.text_input("Responsável", placeholder="Nome do responsável", value=st.session_state.responsavel_key, key="responsavel_key")
        tarefa = st.text_area("Descreva sua tarefa", placeholder="Detalhes da tarefa", value=st.session_state.tarefa_key, key="tarefa_key")
        acaoetapa = st.selectbox("Ação/Etapa", ["Ação", "Etapa"], index=["Ação", "Etapa"].index(st.session_state.acaoetapa_key), key="acaoetapa_key")
        tipoacao = st.selectbox("Tipo Ação", ["Ação de Melhoria", "Ação Imediata", "Ação Corretiva"], index=["Ação de Melhoria", "Ação Imediata", "Ação Corretiva"].index(st.session_state.tipoacao_key), key="tipoacao_key")
        status = st.selectbox("Status", ["Sem Data", "Atrasada", "Planejada", "Cancelada", "Em Andamento", "Concluída"], index=["Sem Data", "Atrasada", "Planejada", "Cancelada", "Em Andamento", "Concluída"].index(st.session_state.status_key), key="status_key")
        observacao = st.text_area("Observação", placeholder="Adicione observações aqui (opcional)", value=st.session_state.observacao_key, key="observacao_key")

        submitted = st.form_submit_button("Adicionar Tarefa")

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
            "Início Previsto": pd.NaT,
            "Término Previsto": pd.NaT,
            "Início Real": pd.NaT,
            "Término Real": pd.NaT,
            "Status": status,
            "Observação": observacao
        }

        st.session_state.df_planos = pd.concat(
            [st.session_state.df_planos, pd.DataFrame([novo_registro])],
            ignore_index=True
        ).astype(expected_dtypes)

        st.success("Novo plano de ação adicionado com sucesso!")
        save_data()
        
        clear_form() # Limpa o formulário após a submissão
        st.rerun()

elif st.session_state.current_view == "Plano de Ação":
   ## st.subheader("- Visão Geral do Plano de Ação") # Título mais descritivo

    if not st.session_state.df_planos.empty:
        # --- 1. Tabela de Planos de Ação Editável ---
        st.caption("Detalhes do Plano de Ação")
        df_exibicao = st.session_state.df_planos.sort_values(by="Nº Sequência", ascending=True)

        edited_df = st.data_editor(
            df_exibicao,
            num_rows="fixed", # Agora fixo para não adicionar por aqui
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
        
        st.markdown("---") # Separador visual

        # --- 2. Tabela de Quantidade por Status ---
        st.caption("🌱 Quantidade de Tarefas por Status")
        df_tasks_by_status = st.session_state.df_planos["Status"].value_counts().reset_index()
        df_tasks_by_status.columns = ["Status", "Quantidade de Tarefas"]
        st.dataframe(df_tasks_by_status, use_container_width=True, hide_index=True)

        st.markdown("---") # Separador visual

        # --- 3. Gráfico de Tarefas por Responsável ---
        st.caption("🌳 Quantidade de Tarefas por Responsável")
        df_tasks_by_responsavel = st.session_state.df_planos["Responsável"].value_counts().reset_index()
        df_tasks_by_responsavel.columns = ["Responsável", "Quantidade de Tarefas"]
        
        st.bar_chart(df_tasks_by_responsavel.set_index("Responsável"))

    else:
        st.info("Nenhum plano de ação adicionado ainda. Adicione tarefas para ver os dados.")

elif st.session_state.current_view == "Filtrado por Responsável":
    if st.session_state.selected_responsavel:
        st.subheader(f"- Tarefas de: {st.session_state.selected_responsavel}")
        df_filtrado = st.session_state.df_planos[st.session_state.df_planos["Responsável"] == st.session_state.selected_responsavel].copy()
        
        if not df_filtrado.empty:
            df_exibicao_filtrada = df_filtrado.sort_values(by="Nº Sequência", ascending=True) # Certifique-se de ter um df_exibicao_filtrada aqui antes de passá-lo para st.data_editor

            edited_df_filtered = st.data_editor(
                df_exibicao_filtrada,
                num_rows="fixed", # Agora fixo para não adicionar por aqui
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

            if not edited_df_filtered.equals(df_exibicao_filtrada):
                df_restante = st.session_state.df_planos[st.session_state.df_planos["Responsável"] != st.session_state.selected_responsavel]
                st.session_state.df_planos = pd.concat([df_restante, edited_df_filtered], ignore_index=True).astype(expected_dtypes)
                save_data()
                st.success("Tabela atualizada!")
        else:
            st.info(f"Nenhum plano de ação encontrado para {st.session_state.selected_responsavel}.")
    else:
        st.info("Selecione um responsável na barra lateral para filtrar.")
else:
    st.info("Selecione uma opção na barra lateral para começar.")

