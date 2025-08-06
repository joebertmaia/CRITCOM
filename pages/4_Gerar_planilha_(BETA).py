import streamlit as st
import pandas as pd
import datetime as dt
from io import StringIO, BytesIO
import math
import warnings

# --- Configuração da Página ---
st.set_page_config(
    page_title="Analisador de Arquivos ABNT",
    page_icon="📄",
    layout="wide"
)

# --- Funções do Script Original (Adaptadas) ---

def obterDados(data, posicao, tamanho):
    """Extrai uma fatia de dados da string principal com base na posição e tamanho."""
    posicao = posicao - 1
    return data[posicao:(posicao+tamanho)]

def iDiaSemana(datestring):
    """Retorna o dia da semana em português a partir de uma string de data."""
    DIAS = [
        'Segunda-feira', 'Terça-feira', 'Quarta-feira',
        'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo'
    ]
    try:
        data = dt.datetime.strptime(datestring, '%Y-%m-%d').date()
        return DIAS[data.weekday()]
    except:
        return ""

def processar_arquivos(abnt_content, bi_dataframe, empresa, livro, horario_p, horario_fp, horario_capacitivo, horario_indutivo, progress_callback=None):
    """
    Função principal que adapta a lógica do script original para processar os dados
    e retornar um DataFrame com os resultados.
    """
    # --- 1. Processamento do Arquivo ABNT ---
    dados_abnt = abnt_content.replace('\n', '').replace('\r', '')
    
    # --- 2. Processamento do Arquivo do Power BI ---
    dados_bi = bi_dataframe
    dados_bi = dados_bi[['EMPRESA', 'SITUAÇÃO', 'LIVRO', 'CDC', 'MEDIDOR HEMERA']]
    dados_bi = dados_bi[dados_bi['EMPRESA'] == empresa]
    dados_bi = dados_bi[dados_bi['SITUAÇÃO'] == 'LIGADO']
    dados_bi = dados_bi[dados_bi['LIVRO'] == int(livro)]
    dados_bi = dados_bi[['CDC', 'MEDIDOR HEMERA']]
    dados_bi = dados_bi[~dados_bi['MEDIDOR HEMERA'].isna()]

    # --- 3. Leitura do Arquivo de Tarefa (agora a partir do conteúdo) ---
    dados = pd.read_csv(StringIO(abnt_content), sep=";")
    colunas = dados.columns
    dados = dados.iloc[:-1] # Remove a linha de totais
    dados['DATA/Hora'] = pd.to_datetime(dados['DATA/Hora'])

    # --- 4. Lista de Feriados (agora interna) ---
    feriados_list = [
        '01/01/2025', '04/03/2025', '18/04/2025', '21/04/2025', '01/05/2025', '19/06/2025',
        '07/09/2025', '12/10/2025', '02/11/2025', '15/11/2025', '25/12/2025', '01/01/2026',
        '17/02/2026', '03/04/2026', '21/04/2026', '01/05/2026', '04/06/2026', '07/09/2026',
        '12/10/2026', '02/11/2026', '15/11/2026', '25/12/2026'
    ]
    feriados_convertido = [dt.datetime.strptime(d, "%d/%m/%Y").date() for d in feriados_list]

    # --- 5. Criação de Flags ---
    flag_fds_feriado = []
    for k in range(len(dados)):
        data_atual = dados['DATA/Hora'].dt.date.iloc[k]
        if data_atual.weekday() >= 5 or data_atual in feriados_convertido:
            flag_fds_feriado.append(1)
        else:
            flag_fds_feriado.append(0)
    
    dados['flag_fds_feriado'] = flag_fds_feriado

    # --- 6. Limpeza e Classificação de Postos Horários ---
    dados.loc[:, dados.columns != 'DATA/Hora'] = dados.loc[:, dados.columns != 'DATA/Hora'].replace({',': '.'}, regex=True)
    
    tipo_horario = []
    for k in range(len(dados)):
        hora_atual = dados['DATA/Hora'].dt.time.iloc[k]
        if horario_p < hora_atual <= horario_fp and dados['flag_fds_feriado'].iloc[k] == 0:
            tipo_horario.append('P')
        else:
            tipo_horario.append('FP')
    dados['tipo_horario'] = tipo_horario

    # --- 7. Loop Principal de Cálculos ---
    colunas_finais = ['medidor', 'tipo_horario', 'kwh', 'kwh_injetado', 'ufer', 'kw', 'dmcr', 'disponibilidade']
    dados_finais = []
    num_medidor = 0
    total_medidores = math.floor((len(colunas) - 1) / 4)

    for n_coluna in range(1, len(colunas), 4):
        num_medidor += 1
        if progress_callback:
            progress_callback.text(f"Processando medidor {num_medidor} de {total_medidores}...")

        coluna_eae = n_coluna
        coluna_ear = n_coluna + 1
        coluna_ere = n_coluna + 2
        coluna_err = n_coluna + 3
        
        if coluna_err >= len(colunas):
            break

        dados_temp = pd.concat([
            dados.iloc[:, 0], 
            dados.iloc[:, coluna_eae:coluna_err+1],
            dados['flag_fds_feriado'], 
            dados['tipo_horario']
        ], axis=1)

        dados_temp.iloc[:, 1:] = dados_temp.iloc[:, 1:].replace([' ', '-'], ['0', '0'], regex=True)
        
        # Lógica de cálculo de UFER, DMCR, etc. (adaptada do original)
        calculos = []
        for k in range(len(dados_temp)):
            kw = float(dados_temp.iloc[k, 1]) * 4
            kw_reativo = float(dados_temp.iloc[k, 3]) * 4
            ufer = 0
            dmcr = 0
            fp = 0
            
            if k >= 4:
                k_3 = k - 3
                soma_kwh = sum(pd.to_numeric(dados_temp.iloc[k_3:k+1, 1]))
                soma_reativo = sum(pd.to_numeric(dados_temp.iloc[k_3:k+1, 3])) - sum(pd.to_numeric(dados_temp.iloc[k_3:k+1, 4]))
                
                if soma_kwh != 0 or soma_reativo != 0:
                    try:
                        fp = soma_kwh / math.sqrt((soma_kwh ** 2) + (soma_reativo ** 2))
                    except ZeroDivisionError:
                        fp = 0
                    
                    if fp > 0 and fp < 0.92:
                        fator = 0.92 / fp
                        ufer = (fator - 1) * soma_kwh
                        kw_medio = sum(pd.to_numeric(dados_temp.iloc[k_3:k+1, 1])) * 4 / 4
                        dmcr = kw_medio * fator
            
            calculos.append([fp, ufer, kw, kw_reativo, dmcr])
        
        df_calculos = pd.DataFrame(calculos, columns=['fator_potencia', 'UFER', 'KW', 'KW_reativo', 'DMCR'])
        dados_temp = pd.concat([dados_temp, df_calculos], axis=1)

        medidor = dados_temp.columns[1].split(' ')[0]
        
        kwh_p = dados_temp[dados_temp['tipo_horario'] == 'P'].iloc[:,1].astype('float').sum()
        kwh_fp = dados_temp[dados_temp['tipo_horario'] == 'FP'].iloc[:,1].astype('float').sum()
        kwh_injetado_p = dados_temp[dados_temp['tipo_horario'] == 'P'].iloc[:,2].astype('float').sum()
        kwh_injetado_fp = dados_temp[dados_temp['tipo_horario'] == 'FP'].iloc[:,2].astype('float').sum()
        kw_p = dados_temp[dados_temp['tipo_horario'] == 'P']['KW'].astype('float').max()
        kw_fp = dados_temp[dados_temp['tipo_horario'] == 'FP']['KW'].astype('float').max()
        dmcr_p = dados_temp[dados_temp['tipo_horario'] == 'P']['DMCR'].astype('float').max()
        dmcr_fp = dados_temp[dados_temp['tipo_horario'] == 'FP']['DMCR'].astype('float').max()
        ufer_p = dados_temp[dados_temp['tipo_horario'] == 'P']['UFER'].astype('float').sum()
        ufer_fp = dados_temp[dados_temp['tipo_horario'] == 'FP']['UFER'].astype('float').sum()
        
        # Disponibilidade (simplificada)
        disp = 100.0

        dados_finais.append([medidor, 'P', round(kwh_p, 6), round(kwh_injetado_p, 6), round(ufer_p, 6), round(kw_p, 6), round(dmcr_p, 6), disp])
        dados_finais.append([medidor, 'FP', round(kwh_fp, 6), round(kwh_injetado_fp, 6), round(ufer_fp, 6), round(kw_fp, 6), round(dmcr_fp, 6), disp])
        
    df_final = pd.DataFrame(dados_finais, columns=colunas_finais)
    df_final = df_final.sort_values(['medidor', 'tipo_horario'], ascending=[True, False]).reset_index(drop=True)
    
    return df_final

# --- Interface do Aplicativo ---
st.title("Gerador de Planilha de Confirmação")

with st.sidebar:
    st.header("1. Carregar Arquivos")
    uploaded_abnt = st.file_uploader("Tarefa Hemera (.txt)", type=['txt'])
    uploaded_bi = st.file_uploader("Arquivo Power BI (.xlsx)", type=['xlsx'])

    st.header("2. Parâmetros")
    empresa = st.selectbox("Empresa", [
        'ENERGISAMR', 'ENERGISAPB', 'ENERGISASE', 'ENERGISATO', 'ENERGISASS', 
        'ENERGISAMS', 'ENERGISAMT', 'ENERGISAAC', 'ENERGISARO'
    ])
    livro = st.text_input("Livro", "1")
    horario_p = st.time_input("Horário de Ponta", dt.time(17, 30))
    horario_fp = st.time_input("Horário Fora Ponta", dt.time(20, 30))
    horario_capacitivo = st.time_input("Horário Capacitivo", dt.time(23, 30))
    horario_indutivo = st.time_input("Horário Indutivo", dt.time(6, 0))

if st.sidebar.button("Analisar"):
    if uploaded_abnt is not None and uploaded_bi is not None:
        try:
            abnt_content = uploaded_abnt.getvalue().decode('latin-1')
            df_bi = pd.read_excel(uploaded_bi, skiprows=2)
            
            progress_text = st.empty()
            with st.spinner("Preparando análise..."):
                dados_consolidados = processar_arquivos(
                    abnt_content, df_bi, empresa, livro,
                    horario_p, horario_fp, horario_capacitivo, horario_indutivo,
                    progress_callback=progress_text
                )
            
            progress_text.empty() # Limpa o texto de progresso
            st.success("Análise concluída com sucesso!")
            st.subheader("Dados Consolidados")
            st.dataframe(dados_consolidados, use_container_width=True)
            
            # --- Botão de Download ---
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                dados_consolidados.to_excel(writer, index=False, sheet_name='Resultados')
            
            st.download_button(
                label="Baixar Relatório em Excel",
                data=output.getvalue(),
                file_name=f'relatorio_confirmacoes_{empresa}_livro_{livro}.xlsx',
                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )

        except Exception as e:
            st.error(f"Ocorreu um erro durante o processamento: {e}")
            st.error("Verifique se os arquivos estão corretos e se os parâmetros foram preenchidos.")
    else:
        st.warning("Por favor, carregue os dois arquivos necessários antes de analisar.")
else:
    st.info("Preencha os parâmetros na barra lateral e clique em 'Analisar' para iniciar.")