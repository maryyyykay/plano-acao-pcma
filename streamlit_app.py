import streamlit as st
import pandas as pd
from datetime import date
import json
import numpy as np

# Importações para gspread
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe

st.set_page_config(layout="wide")
st.title("🎍 PCMA - PLANO DE AÇÃO 2025")

# --- Variáveis de Configuração do Google Sheets ---
GOOGLE_SHEET_ID = "1Ju6-V7bAXa-dnvWlZRcTyRMq4L48NQf07MCdoJLeRwQ"
WORKSHEET_NAME = "Planos"

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

# --- Funções de Leitura/Escrita do Google Sheets (AGORA USANDO gspread) ---

# Crie um objeto de autenticação gspread
# Use os segredos do Streamlit para autenticação da conta de serviço
@st.cache_resource(ttl=3600) # Cache para o objeto de autenticação
def get_gspread_client():
    try:
        # Acessa os segredos do Streamlit
        creds = st.secrets["gsheets_service_account"]
        # Converte o dicionário de credenciais para uma string JSON
        json_creds = json.dumps(creds)
        gc = gspread.service_account_from_dict(json.loads(json_creds))
        return gc
    except Exception as e:
        st.error(f"Erro de autenticação com o Google Sheets: {e}")
        st.info("Verifique se suas credenciais de serviço estão configuradas corretamente nos segredos do Streamlit.")
        return None

gc = get_gspread_client()

@st.cache_data(ttl=600) # Recarrega a cada 10 minutos
def load_data_from_gsheets(client):
    if not client:
        return pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()})
    try:
        sh = client.open_by_id(GOOGLE_SHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)
        
        # Lê os dados da planilha como DataFrame
        df = get_as_dataframe(worksheet, header=1, usecols=list(expected_dtypes.keys()))
        
        # Converte tipos de dados
        for col, dtype in expected_dtypes.items():
            if col in df.columns:
                if 'datetime' in str(dtype):
                    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                elif 'Int64' in str(dtype):
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                else:
                    df[col] = df[col].astype(dtype)
            else:
                df[col] = pd.Series(dtype=dtype) # Adiciona colunas ausentes
        
        # Remove linhas completamente vazias
        df.dropna(how='all', inplace=True)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        # Retorna um DataFrame vazio com as colunas esperadas em caso de erro
        return pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()})

def save_data_to_gsheets(client, df_to_save):
    if not client:
        st.error("Não foi possível salvar os dados: cliente Google Sheets não autenticado.")
        return

    try:
        sh = client.open_by_id(GOOGLE_SHEET_ID)
        worksheet = sh.worksheet(WORKSHEET_NAME)

        df_for_gsheets = df_to_save.copy()
        
        # Pré-processa para gspread
        for col in df_for_gsheets.select_dtypes(include=['datetime64[ns]']).columns:
            df_for_gsheets[col] = df_for_gsheets[col].dt.strftime('%d/%m/%Y').replace({pd.NA: ''})
        
        for col in df_for_gsheets.select_dtypes(include=['Int64']).columns:
            df_for_gsheets[col] = df_for_gsheets[col].apply(lambda x: int(x) if pd.notna(x) else '')
            
        df_for_gsheets = df_for_gsheets.fillna('') # Garante que todos os NaNs/NAs sejam vazios

        # Escreve o DataFrame de volta na planilha
        set_with_dataframe(worksheet, df_for_gsheets, include_index=False, include_column_header=True)
        
        st.success("Dados salvos com sucesso no Google Sheets!")
        st.balloons()
    except Exception as e:
        st.error(f"Erro ao salvar dados no Google Sheets: {e}")

# --- Lógica de Carregamento de Dados (Agora do Google Sheets) ---
if 'df_planos' not in st.session_state:
    if gc: # Carrega dados apenas se o cliente gspread foi inicializado com sucesso
        st.session_state.df_planos = load_data_from_gsheets(gc)
    else:
        st.session_state.df_planos = pd.DataFrame({col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()})

# --- Função para Salvar o DataFrame (Agora para o Google Sheets) ---
def save_data():
    load_data_from_gsheets.clear() # Limpa o cache para forçar a releitura
    if gc: # Salva dados apenas se o cliente gspread foi inicializado com sucesso
        save_data_to_gsheets(gc, st.session_state.df_planos)

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
    st.session_state.current_view = "Plano de Ação"

if 'selected_responsavel' not in st.session_state:
    st.session_state.selected_responsavel = None

# Mova a inicialização das chaves do formulário para fora do bloco 'Adicionar Tarefa'
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

if st.sidebar.button("Plano de Ação", key="view_all_plans_button"):
    st.session_state.current_view = "Plano de Ação"
    st.session_state.selected_responsavel = None
    st.rerun()

if st.sidebar.button("Adicionar Nova Tarefa", key="add_new_plan_button"):
    st.session_state.current_view = "Adicionar Tarefa"
    st.session_state.selected_responsavel = None
    clear_form()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("Planos por Responsável")

if not st.session_state.df_planos.empty:
    responsaveis = st.session_state.df_planos["Responsável"].dropna().unique().tolist()
    responsaveis.sort()
    
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
            st.session_state.df_planos["Nº Sequência"] = pd.to_numeric(st.session_state.df_planos["Nº Sequência"], errors='coerce')
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

        novo_df_temp = pd.DataFrame([novo_registro])
        novo_df_temp = novo_df_temp.astype({col: dtype for col, dtype in expected_dtypes.items() if col in novo_df_temp.columns})
        
        st.session_state.df_planos = pd.concat(
            [st.session_state.df_planos, novo_df_temp],
            ignore_index=True
        ).astype(expected_dtypes)

        st.success("Novo plano de ação adicionado com sucesso!")
        save_data()
        st.rerun()

elif st.session_state.current_view == "Plano de Ação":
    st.subheader("- Visão Geral do Plano de Ação")

    if not st.session_state.df_planos.empty:
        st.caption("Detalhes do Plano de Ação")
        df_exibicao = st.session_state.df_planos.sort_values(by="Nº Sequência", ascending=True)

        df_for_editor = df_exibicao.copy()
        for col in ["Início Previsto", "Término Previsto", "Início Real", "Término Real"]:
            if col in df_for_editor.columns:
                df_for_editor[col] = df_for_editor[col].dt.strftime('%d/%m/%Y').replace({pd.NA: ''})

        edited_df = st.data_editor(
            df_for_editor,
            num_rows="fixed",
            column_config={
                "Nº Sequência": st.column_config.NumberColumn("Nº Sequência", disabled=True),
                "Data Fato": st.column_config.TextColumn("Data Fato", disabled=True),
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

        df_after_edit = edited_df.copy()
        for col, dtype in expected_dtypes.items():
            if col in df_after_edit.columns:
                if 'datetime' in str(dtype):
                    df_after_edit[col] = pd.to_datetime(df_after_edit[col], errors='coerce', dayfirst=True)
                elif 'Int64' in str(dtype):
                    df_after_edit[col] = pd.to_numeric(df_after_edit[col], errors='coerce').astype('Int64')
                else:
                    df_after_edit[col] = df_after_edit[col].astype(dtype)
            
        if not df_after_edit.equals(st.session_state.df_planos):
            st.session_state.df_planos = df_after_edit
            save_data()
            st.success("Tabela atualizada!")
            
        st.markdown("---")

        st.caption("🌱 Quantidade de Tarefas por Status")
        if "Status" in st.session_state.df_planos.columns:
            df_tasks_by_status = st.session_state.df_planos["Status"].astype(str).value_counts().reset_index()
            df_tasks_by_status.columns = ["Status", "Quantidade de Tarefas"]
            st.dataframe(df_tasks_by_status, use_container_width=True, hide_index=True)
        else:
            st.info("Colunas de status não encontradas.")

        st.markdown("---")

        st.caption("🌳 Quantidade de Tarefas por Responsável")
        if "Responsável" in st.session_state.df_planos.columns:
            df_tasks_by_responsavel = st.session_state.df_planos["Responsável"].astype(str).value_counts().reset_index()
            df_tasks_by_responsavel.columns = ["Responsável", "Quantidade de Tarefas"]
            st.bar_chart(df_tasks_by_responsavel.set_index("Responsavel"))
        else:
            st.info("Colunas de responsável não encontradas.")

    else:
        st.info("Nenhum plano de ação adicionado ainda. Adicione tarefas para ver os dados.")

elif st.session_state.current_view == "Filtrado por Responsável":
    if st.session_state.selected_responsavel:
        st.subheader(f"- Tarefas de: {st.session_state.selected_responsavel}")
        df_filtrado = st.session_state.df_planos[st.session_state.df_planos["Responsável"] == st.session_state.selected_responsavel].copy()
        
        if not df_filtrado.empty:
            df_exibicao_filtrada = df_filtrado.sort_values(by="Nº Sequência", ascending=True)

            df_for_editor_filtered = df_exibicao_filtrada.copy()
            for col in ["Início Previsto", "Término Previsto", "Início Real", "Término Real"]:
                if col in df_for_editor_filtered.columns:
                    df_for_editor_filtered[col] = df_for_editor_filtered[col].dt.strftime('%d/%m/%Y').replace({pd.NA: ''})

            edited_df_filtered = st.data_editor(
                df_for_editor_filtered,
                num_rows="fixed",
                column_config={
                    "Nº Sequência": st.column_config.NumberColumn("Nº Sequência", disabled=True),
                    "Data Fato": st.column_config.TextColumn("Data Fato", disabled=True),
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

            df_after_edit_filtered = edited_df_filtered.copy()
            for col, dtype in expected_dtypes.items():
                if col in df_after_edit_filtered.columns:
                    if 'datetime' in str(dtype):
                        df_after_edit_filtered[col] = pd.to_datetime(df_after_edit_filtered[col], errors='coerce', dayfirst=True)
                    elif 'Int64' in str(dtype):
                        df_after_edit_filtered[col] = pd.to_numeric(df_after_edit_filtered[col], errors='coerce').astype('Int64')
                    else:
                        df_after_edit_filtered[col] = df_after_edit_filtered[col].astype(dtype)

            df_restante = st.session_state.df_planos[st.session_state.df_planos["Responsável"] != st.session_state.selected_responsavel]
            st.session_state.df_planos = pd.concat([df_restante, df_after_edit_filtered], ignore_index=True).astype(expected_dtypes)

            if not edited_df_filtered.equals(df_exibicao_filtrada):
                save_data()
                st.success("Tabela atualizada!")
        else:
            st.info(f"Nenhum plano de ação encontrado para {st.session_state.selected_responsavel}.")
    else:
        st.info("Selecione um responsável na barra lateral para filtrar.")
else:
    st.info("Selecione uma opção na barra lateral para começar.")
