import streamlit as st
import pandas as pd
from datetime import date
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
import json
import numpy as np # Importar numpy para pd.NaT

st.set_page_config(layout="wide")
st.title("🎍 PCMA - PLANO DE AÇÃO 2025")

# --- Variáveis de Configuração do Google Sheets ---
# ID da sua planilha Google (você encontra na URL da planilha, entre /d/ e /edit)
GOOGLE_SHEET_ID = "1Ju6-V7bAXa-dnvWlZRcTyRMq4L48NQf07MCdoJLeRwQ" # Substitua pelo ID da sua planilha
WORKSHEET_NAME = "Planos" # O nome da aba (sheet) onde os dados estão, ex: "Planos"

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

# --- Funções de Leitura/Escrita do Google Sheets ---

# Cache a função para evitar leituras repetidas e lentidão
@st.cache_data(ttl=600) # Recarrega a cada 10 minutos
def load_data_from_gsheets():
    try:
        # Autentica com a Service Account (usando o segredo do Streamlit Cloud)
        gs_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
        gc = gspread.service_account_from_dict(gs_account_info)
        # Abre a planilha pelo ID e seleciona a aba
        spreadsheet = gc.open_by_id(GOOGLE_SHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
        
        # Obtém todos os registros e converte para DataFrame
        df = get_as_dataframe(worksheet, header=1) # header=1 indica que a primeira linha é o cabeçalho
        
        # Converte tipos de dados
        for col, dtype in expected_dtypes.items():
            if col in df.columns:
                if 'datetime' in str(dtype):
                    # Força o formato de data para evitar problemas com valores nulos ou vazios
                    df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
                elif 'Int64' in str(dtype):
                    # Converte para Int64, coerce para NaN em caso de erro, depois preenche com pd.NA e converte
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('Int64')
                else:
                    df[col] = df[col].astype(dtype)
            else:
                # Adiciona colunas que podem estar faltando no Sheets, mas esperadas no DataFrame
                df[col] = pd.Series(dtype=dtype)
        
        # Remove linhas completamente vazias que gspread pode retornar
        df.dropna(how='all', inplace=True)

        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do Google Sheets: {e}")
        # Retorna um DataFrame vazio com as colunas esperadas em caso de erro
        initial_data_empty = {col: pd.Series(dtype=dtype) for col, dtype in expected_dtypes.items()}
        return pd.DataFrame(initial_data_empty)

def save_data_to_gsheets(df_to_save):
    try:
        gs_account_info = json.loads(st.secrets["GCP_SERVICE_ACCOUNT_JSON"])
        gc = gspread.service_account_from_dict(gs_account_info)
        spreadsheet = gc.open_by_id(GOOGLE_SHEET_ID)
        worksheet = spreadsheet.worksheet(WORKSHEET_NAME)

        # Preenche NaT/NaN com None para gspread lidar corretamente
        # Convertendo todos os datetimes para string no formato DD/MM/YYYY antes de salvar
        df_for_gsheets = df_to_save.copy()
        for col in df_for_gsheets.select_dtypes(include=['datetime64[ns]']).columns:
            df_for_gsheets[col] = df_for_gsheets[col].dt.strftime('%d/%m/%Y').replace({pd.NA: ''})
        
        # Converte Int64 (com pd.NA) para int normal ou None
        for col in df_for_gsheets.select_dtypes(include=['Int64']).columns:
            df_for_gsheets[col] = df_for_gsheets[col].apply(lambda x: int(x) if pd.notna(x) else '')
        
        # Preenche outros NaNs/NAs como strings vazias ou None
        df_for_gsheets = df_for_gsheets.fillna('') # Garante que todos os NaNs/NAs sejam vazios

        set_with_dataframe(worksheet, df_for_gsheets, include_index=False, row=1, col=1) # row=1, col=1 para começar na primeira célula (A1)
        st.success("Dados salvos com sucesso no Google Sheets!")
        st.balloons()
    except Exception as e:
        st.error(f"Erro ao salvar dados no Google Sheets: {e}")


# --- Lógica de Carregamento de Dados (Agora do Google Sheets) ---
if 'df_planos' not in st.session_state:
    st.session_state.df_planos = load_data_from_gsheets()


# --- Função para Salvar o DataFrame (Agora para o Google Sheets) ---
def save_data():
    # Remover cache para forçar a releitura após salvar
    load_data_from_gsheets.clear()
    save_data_to_gsheets(st.session_state.df_planos)


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
# Atualizado para buscar do df_planos da session_state
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
            # Garante que a coluna 'Nº Sequência' seja numérica antes de buscar o máximo
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

        # Concatenação e ajuste de dtypes
        novo_df_temp = pd.DataFrame([novo_registro])
        novo_df_temp = novo_df_temp.astype({col: dtype for col, dtype in expected_dtypes.items() if col in novo_df_temp.columns})
        
        st.session_state.df_planos = pd.concat(
            [st.session_state.df_planos, novo_df_temp],
            ignore_index=True
        ).astype(expected_dtypes) # Garante que todo o DF final tenha os dtypes corretos


        st.success("Novo plano de ação adicionado com sucesso!")
        save_data() # Chama a função que agora salva no Google Sheets
        
        clear_form() # Limpa o formulário após a submissão
        st.rerun()

elif st.session_state.current_view == "Plano de Ação":
    st.subheader("- Visão Geral do Plano de Ação") # Título mais descritivo

    if not st.session_state.df_planos.empty:
        # --- 1. Tabela de Planos de Ação Editável ---
        st.caption("Detalhes do Plano de Ação")
        df_exibicao = st.session_state.df_planos.sort_values(by="Nº Sequência", ascending=True)

        # Pré-processa as colunas de data para o data_editor
        df_for_editor = df_exibicao.copy()
        for col in ["Início Previsto", "Término Previsto", "Início Real", "Término Real"]:
            if col in df_for_editor.columns:
                # Converte pd.NaT para string vazia para exibição no editor
                df_for_editor[col] = df_for_editor[col].dt.strftime('%d/%m/%Y').replace({pd.NA: ''})


        edited_df = st.data_editor(
            df_for_editor,
            num_rows="fixed",
            column_config={
                "Nº Sequência": st.column_config.NumberColumn("Nº Sequência", disabled=True),
                "Data Fato": st.column_config.TextColumn("Data Fato", disabled=True), # Mudado para TextColumn para exibir string
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

        # Pós-processamento para converter de volta para os tipos de dados originais
        df_after_edit = edited_df.copy()
        for col, dtype in expected_dtypes.items():
            if col in df_after_edit.columns:
                if 'datetime' in str(dtype):
                    df_after_edit[col] = pd.to_datetime(df_after_edit[col], errors='coerce', dayfirst=True)
                elif 'Int64' in str(dtype):
                    df_after_edit[col] = pd.to_numeric(df_after_edit[col], errors='coerce').astype('Int64')
                else:
                    df_after_edit[col] = df_after_edit[col].astype(dtype)
        
        if not df_after_edit.equals(st.session_state.df_planos): # Compara com o DF original para evitar saves desnecessários
            st.session_state.df_planos = df_after_edit
            save_data()
            st.success("Tabela atualizada!")
        
        st.markdown("---") # Separador visual

        # --- 2. Tabela de Quantidade por Status ---
        st.caption("🌱 Quantidade de Tarefas por Status")
        # Garante que 'Status' é string para value_counts
        if "Status" in st.session_state.df_planos.columns:
             df_tasks_by_status = st.session_state.df_planos["Status"].astype(str).value_counts().reset_index()
             df_tasks_by_status.columns = ["Status", "Quantidade de Tarefas"]
             st.dataframe(df_tasks_by_status, use_container_width=True, hide_index=True)
        else:
            st.info("Colunas de status não encontradas.")


        st.markdown("---") # Separador visual

        # --- 3. Gráfico de Tarefas por Responsável ---
        st.caption("🌳 Quantidade de Tarefas por Responsável")
        # Garante que 'Responsável' é string para value_counts
        if "Responsável" in st.session_state.df_planos.columns:
            df_tasks_by_responsavel = st.session_state.df_planos["Responsável"].astype(str).value_counts().reset_index()
            df_tasks_by_responsavel.columns = ["Responsável", "Quantidade de Tarefas"]
            st.bar_chart(df_tasks_by_responsavel.set_index("Responsável"))
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

            # Pré-processa as colunas de data para o data_editor
            df_for_editor_filtered = df_exibicao_filtrada.copy()
            for col in ["Início Previsto", "Término Previsto", "Início Real", "Término Real"]:
                if col in df_for_editor_filtered.columns:
                    df_for_editor_filtered[col] = df_for_editor_filtered[col].dt.strftime('%d/%m/%Y').replace({pd.NA: ''})

            edited_df_filtered = st.data_editor(
                df_for_editor_filtered,
                num_rows="fixed",
                column_config={
                    "Nº Sequência": st.column_config.NumberColumn("Nº Sequência", disabled=True),
                    "Data Fato": st.column_config.TextColumn("Data Fato", disabled=True), # Mudado para TextColumn para exibir string
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

            # Pós-processamento para converter de volta para os tipos de dados originais
            df_after_edit_filtered = edited_df_filtered.copy()
            for col, dtype in expected_dtypes.items():
                if col in df_after_edit_filtered.columns:
                    if 'datetime' in str(dtype):
                        df_after_edit_filtered[col] = pd.to_datetime(df_after_edit_filtered[col], errors='coerce', dayfirst=True)
                    elif 'Int64' in str(dtype):
                        df_after_edit_filtered[col] = pd.to_numeric(df_after_edit_filtered[col], errors='coerce').astype('Int64')
                    else:
                        df_after_edit_filtered[col] = df_after_edit_filtered[col].astype(dtype)

            # Concatena o DataFrame filtrado editado de volta ao DataFrame completo
            # Primeiro, remove as linhas correspondentes ao responsável do df_planos
            df_restante = st.session_state.df_planos[st.session_state.df_planos["Responsável"] != st.session_state.selected_responsavel]
            # Em seguida, concatena as linhas editadas (do responsável selecionado)
            st.session_state.df_planos = pd.concat([df_restante, df_after_edit_filtered], ignore_index=True).astype(expected_dtypes)

            if not edited_df_filtered.equals(df_exibicao_filtrada): # Compara com o DF original filtrado
                save_data()
                st.success("Tabela atualizada!")
        else:
            st.info(f"Nenhum plano de ação encontrado para {st.session_state.selected_responsavel}.")
    else:
        st.info("Selecione um responsável na barra lateral para filtrar.")
else:
    st.info("Selecione uma opção na barra lateral para começar.")
