import streamlit as st
import pandas as pd
import io
from datetime import datetime
import plotly.express as px

def obterDados(data, posicao, tamanho):
    """
    Extrai uma porção de dados de uma string com base na posição e tamanho.
    A posição é baseada em 1 (e não em 0 como no índice de strings do Python).
    """
    posicao = posicao - 1
    # Garante que não haverá erro se a string for menor que o esperado
    return data[posicao:(posicao + tamanho)] if len(data) >= posicao + tamanho else ""

def processar_arquivo_abnt(file_content):
    """
    Função principal que pega o conteúdo de um arquivo e retorna os DataFrames processados.
    """
    # Limpa o conteúdo do arquivo
    dados = file_content.replace('\n', '').replace('\r', '')

    # --- Construindo o relatório de Parâmetros Gerais ---
    colunas = [
        'medidor', 'data_hora_leitura', 'intervalo_mm', 'intervalo_demanda',
        'constante_canal_1', 'constante_canal_2', 'constante_canal_3',
        'estado_bateria', 'carga_md', 'versao_hardware', 'reservado_ativo', 'horario_reservado',
        'reservado_sabado', 'reservado_domingo', 'reservado_feriado',
        'horario_verao', 'horario_FP', 'horario_P', 'horario_indutivo', 'horario_capacitivo',
        'data_reposicao_demanda', 'hora_reposicao_demanda', 'feriado_1', 'feriado_2',
        'feriado_3', 'feriado_4', 'feriado_5', 'feriado_6', 'feriado_7', 'feriado_8',
        'feriado_9', 'feriado_10', 'feriado_11', 'feriado_12', 'feriado_13', 'feriado_14',
        'feriado_15', 'data_inicio_conj1_segm_horarios', 'data_inicio_conj2_segm_horarios',
        'hora_inicio_posto_P_conj2', 'hora_inicio_posto_FP_conj2', 'hora_inicio_posto_reservado_conj2'
    ]
    
    medidor = obterDados(dados, 1, 8)
    data_hora_leitura = f"{obterDados(dados, 21, 2)}/{obterDados(dados, 23, 2)}/{obterDados(dados, 25, 2)} {obterDados(dados, 15, 2)}:{obterDados(dados, 17, 2)}:{obterDados(dados, 19, 2)}"
    intervalo_mm = obterDados(dados, 2317, 2)
    intervalo_demanda = obterDados(dados, 167, 2)
    constante_canal_1 = f"{obterDados(dados, 261, 6)}/{obterDados(dados, 267, 6)}"
    constante_canal_2 = f"{obterDados(dados, 273, 6)}/{obterDados(dados, 279, 6)}"
    constante_canal_3 = f"{obterDados(dados, 285, 6)}/{obterDados(dados, 291, 6)}"
    estado_bateria = 'Bom' if obterDados(dados, 297, 2) == '00' else 'Ruim'
    carga_md = obterDados(dados, 1741, 4)
    versao_hardware = obterDados(dados, 1751, 4)
    reservado_ativo = 'Sim' if obterDados(dados, 303, 2) != '00' else 'Não'
    reservado_sabado = obterDados(dados, 2323, 2)
    reservado_domingo = obterDados(dados, 2325, 2)
    reservado_feriado = obterDados(dados, 2327, 2)
    horario_verao_val = f"{obterDados(dados, 2233, 2)}/{obterDados(dados, 2235, 2)}"
    horario_verao = 'Desativado' if horario_verao_val == '00/00' else horario_verao_val
    horario_FP = f"{obterDados(dados, 121, 2)}:{obterDados(dados, 123, 2)}"
    horario_P = f"{obterDados(dados, 113, 2)}:{obterDados(dados, 115, 2)}"
    horario_reservado = f"{obterDados(dados, 141, 2)}:{obterDados(dados, 143, 2)}"
    horario_indutivo = f"{obterDados(dados, 2341, 2)}:{obterDados(dados, 2343, 2)}"
    horario_capacitivo = f"{obterDados(dados, 2349, 2)}:{obterDados(dados, 2351, 2)}"
    data_reposicao_demanda = f"{obterDados(dados, 47, 2)}/{obterDados(dados, 49, 2)}/{obterDados(dados, 51, 2)}"
    hora_reposicao_demanda = f"{obterDados(dados, 41, 2)}:{obterDados(dados, 43, 2)}:{obterDados(dados, 55, 2)}"
    feriados = [f"{obterDados(dados, p, 2)}/{obterDados(dados, p+2, 2)}/{obterDados(dados, p+4, 2)}" for p in range(171, 171 + 15 * 6, 6)]
    data_inicio_conj1_segm_horarios = f"{obterDados(dados, 2239, 2)}/{obterDados(dados, 2241, 2)}"
    data_inicio_conj2_segm_horarios = f"{obterDados(dados, 2243, 2)}/{obterDados(dados, 2245, 2)}"
    hora_inicio_posto_P_conj2 = f"{obterDados(dados, 2255, 2)}:{obterDados(dados, 2257, 2)}"
    hora_inicio_posto_FP_conj2 = f"{obterDados(dados, 2271, 2)}:{obterDados(dados, 2273, 2)}"
    hora_inicio_posto_reservado_conj2 = f"{obterDados(dados, 2287, 2)}:{obterDados(dados, 2289, 2)}"

    linha_parametros = [
        medidor, data_hora_leitura, intervalo_mm, intervalo_demanda, constante_canal_1,
        constante_canal_2, constante_canal_3, estado_bateria,
        carga_md, versao_hardware, reservado_ativo, horario_reservado, reservado_sabado,
        reservado_domingo, reservado_feriado, horario_verao,
        horario_FP, horario_P, horario_indutivo, horario_capacitivo, data_reposicao_demanda,
        hora_reposicao_demanda] + feriados + [
        data_inicio_conj1_segm_horarios, data_inicio_conj2_segm_horarios,
        hora_inicio_posto_P_conj2, hora_inicio_posto_FP_conj2, hora_inicio_posto_reservado_conj2
    ]
    
    df_parametros = pd.DataFrame([linha_parametros], columns=colunas)

    # --- Tratando Faltas de Energia ---
    faltas_de_energia = []
    for i in range(15):
        pos = 329 + (i * 24)
        falta = obterDados(dados, pos, 24)
        if falta and falta != '000000000000000000000000':
            inicio = f"{falta[6:8]}/{falta[8:10]}/{falta[10:12]} {falta[0:2]}:{falta[2:4]}:{falta[4:6]}"
            fim = f"{falta[18:20]}/{falta[20:22]}/{falta[22:24]} {falta[12:14]}:{falta[14:16]}:{falta[16:18]}"
            faltas_de_energia.append([medidor, inicio, fim])
    
    df_faltas = pd.DataFrame(faltas_de_energia, columns=['medidor', 'data_inicio', 'data_fim']).drop_duplicates()

    # --- Tratando Alterações ---
    codigos_alteracoes = {
        11: 'Envio de senha', 12: 'Programação de código de cliente', 13: 'Pedido de string', 20: 'Leitura com reposição de demanda',
        21: 'Leitura s/ reposição atuais', 22: 'Leitura s/ reposição anteriores', 23: 'Leitura de regs. após última reposição',
        # ... (restante dos códigos omitido por brevidade)
        99: 'Comando para carga rápida de programa'
    }
    
    alteracoes = []
    for i in range(15):
        pos = 1927 + (i * 20)
        alteracao = obterDados(dados, pos, 20)
        if alteracao and alteracao != '00000000000000000000':
            try:
                codigo = int(alteracao[0:2])
                num_serie_leitor = alteracao[2:8]
                hora_alteracao = f"{alteracao[8:10]}:{alteracao[10:12]}:{alteracao[12:14]}"
                data_alteracao = f"{alteracao[14:16]}/{alteracao[16:18]}/{alteracao[18:20]}"
                descricao = codigos_alteracoes.get(codigo, f"Código desconhecido ({codigo})")
                alteracoes.append([medidor, num_serie_leitor, codigo, descricao, f"{data_alteracao} {hora_alteracao}"])
            except (ValueError, IndexError):
                continue
    
    df_alteracoes = pd.DataFrame(alteracoes, columns=['Medidor', 'Leitora', 'Código', 'Descrição', 'Data da alteração']).drop_duplicates()

    return df_parametros, df_faltas, df_alteracoes

def create_metric_card(title, value, title_color="#4f555e", value_color="black", bg_color="#f0f2f6"):
    """Função auxiliar para criar um card de métrica estilizado com HTML."""
    return f"""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: {bg_color}; height: 100%; display: flex; flex-direction: column; justify-content: center;">
        <p style="margin:0; font-size: 0.875rem; color: {title_color};">{title}</p>
        <p style="margin:0; font-size: 1.5rem; color: {value_color};">
            <b>{value}</b>
        </p>
    </div>
    """

def display_parametros_layout(df):
    """Cria o layout visual para a seção de parâmetros gerais."""
    params = df.iloc[0]

    st.markdown("**Parâmetros Gerais**")
    # --- Primeira Linha ---
    # Define as proporções de largura para as colunas
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 2, 1, 1.5, 1, 1.5, 1.5])
    with col1:
        bg_md = '#F8D7DA' if params['medidor'] == '' else '#f0f2f6'
        val_md = 'red' if params['medidor'] == '' else 'black'
        st.markdown(create_metric_card("Medidor", params['medidor'], value_color=val_md, bg_color=bg_md), unsafe_allow_html=True)
    with col2:
        bg_hora = '#F8D7DA' if params['data_hora_leitura'] == '' else '#f0f2f6'
        val_hora = 'red' if params['data_hora_leitura'] == '' else 'black'
        st.markdown(create_metric_card("Data/Hora da Leitura", params['data_hora_leitura'], value_color=val_hora, bg_color=bg_hora), unsafe_allow_html=True)
    with col3:
        bg_mm = '#F8D7DA' if params['intervalo_mm'] != '05' else '#D4EDDA'
        val_mm = '#721C24' if params['intervalo_mm'] != '05' else '#155724'
        st.markdown(create_metric_card("MM (min)", params['intervalo_mm'], value_color=val_mm, bg_color=bg_mm), unsafe_allow_html=True)
    with col4:
        bg_dem = '#F8D7DA' if params['intervalo_demanda'] != '15' else '#D4EDDA'
        val_dem = '#721C24' if params['intervalo_demanda'] != '15' else '#155724'
        st.markdown(create_metric_card("Demanda (min)", params['intervalo_demanda'], value_color=val_dem, bg_color=bg_dem), unsafe_allow_html=True)
    with col5:
        bg_bat = '#D4EDDA' if params['estado_bateria'] == 'Bom' else '#F8D7DA'
        val_bat = '#155724' if params['estado_bateria'] == 'Bom' else '#721C24'
        st.markdown(create_metric_card("Bateria", params['estado_bateria'], value_color=val_bat, bg_color=bg_bat), unsafe_allow_html=True)
    with col6:
        bg_carga = '#F8D7DA' if params['carga_md'] != '0111' and params['versao_hardware'] == '6803' else '#f0f2f6'
        val_carga = 'red' if params['carga_md'] != '0111' and params['versao_hardware'] == '6803' else 'black'
        st.markdown(create_metric_card("Carga do MD", params['carga_md'], value_color=val_carga, bg_color=bg_carga), unsafe_allow_html=True)
    with col7:
        bg_hw = '#F8D7DA' if params['versao_hardware'] == '' else '#f0f2f6'
        val_hw = 'red' if params['versao_hardware'] == '' else 'black'
        st.markdown(create_metric_card("Versão do Hardware", params['versao_hardware'], value_color=val_hw, bg_color=bg_hw), unsafe_allow_html=True)
    
    # --- Segunda Linha (Constantes) ---
    st.markdown("---")
    st.markdown("**Constantes Internas**")
    col1, col2, col3 = st.columns(3)
    c1, c2, c3 = params['constante_canal_1'], params['constante_canal_2'], params['constante_canal_3']
    
    cor_c1, cor_c2, cor_c3 = ('#155724', '#155724', '#155724') if c1 == c2 == c3 else ('#721C24', '#721C24', '#721C24')
    bg_c1, bg_c2, bg_c3 = ('#D4EDDA', '#D4EDDA', '#D4EDDA') if c1 == c2 == c3 else ('#F8D7DA', '#F8D7DA', '#F8D7DA')
    
    if c1 != c2 or c1 != c3 or c2 != c3:
        counts = pd.Series([c1, c2, c3]).value_counts()
        if counts.max() > 1:
            majority_val = counts.idxmax()
            cor_c1, bg_c1 = ('#155724', '#D4EDDA') if c1 == majority_val else ('#721C24', '#F8D7DA')
            cor_c2, bg_c2 = ('#155724', '#D4EDDA') if c2 == majority_val else ('#721C24', '#F8D7DA')
            cor_c3, bg_c3 = ('#155724', '#D4EDDA') if c3 == majority_val else ('#721C24', '#F8D7DA')
    
    with col1:
        st.markdown(create_metric_card("Canal 1", c1, value_color=cor_c1, bg_color=bg_c1), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("Canal 2", c2, value_color=cor_c2, bg_color=bg_c2), unsafe_allow_html=True)
    with col3:
        st.markdown(create_metric_card("Canal 3", c3, value_color=cor_c3, bg_color=bg_c3), unsafe_allow_html=True)

    # --- Terceira Linha (Reservado) ---
    st.markdown("---")
    st.markdown("**Horário Reservado**")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    val_sab, val_dom, val_fer = ('black', 'black', 'black')
    if params['reservado_ativo'] == 'Sim':
        if params['reservado_sabado'] != '06': val_sab = 'red'
        if params['reservado_domingo'] != '06': val_dom = 'red'
        if params['reservado_feriado'] != '06': val_fer = 'red'

    with col1:
        bg_md = '#F8D7DA' if params['reservado_ativo'] == '' else '#f0f2f6'
        val_md = 'red' if params['reservado_ativo'] == '' else 'black'
        st.markdown(create_metric_card("Ativo?", params['reservado_ativo'], value_color=val_md, bg_color=bg_md), unsafe_allow_html=True)
    with col2:
        bg_md = '#F8D7DA' if params['horario_reservado'] == '' else '#f0f2f6'
        val_md = 'red' if params['horario_reservado'] == '' else 'black'
        st.markdown(create_metric_card("Horário", params['horario_reservado'], value_color=val_md, bg_color=bg_md), unsafe_allow_html=True)
    with col3:
        st.markdown(create_metric_card("Sábado", params['reservado_sabado'], value_color=val_sab), unsafe_allow_html=True)
    with col4:
        st.markdown(create_metric_card("Domingo", params['reservado_domingo'], value_color=val_dom), unsafe_allow_html=True)
    with col5:
        st.markdown(create_metric_card("Feriado", params['reservado_feriado'], value_color=val_fer), unsafe_allow_html=True)
        
    # --- Quarta Linha (Outros Horários) ---

    st.markdown("---")
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    c1, c2, c3, c4, c5, c6, c7 = params['horario_verao'], params['horario_P'], params['horario_FP'], params['horario_capacitivo'], params['horario_indutivo'], params['data_reposicao_demanda'], params['hora_reposicao_demanda']
    
    cor_value = 'black'
    cor_bg = '#f0f2f6'

    with col1:
        st.markdown(create_metric_card("Horário Verão", c1, value_color=cor_value, bg_color=cor_bg), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("Horário Ponta", c2, value_color=cor_value, bg_color=cor_bg), unsafe_allow_html=True)
    with col3:
        st.markdown(create_metric_card("Horário Fora Ponta", c3, value_color=cor_value, bg_color=cor_bg), unsafe_allow_html=True)
    with col4:
        st.markdown(create_metric_card("Horário Capacitivo", c4, value_color=cor_value, bg_color=cor_bg), unsafe_allow_html=True)
    with col5:
        st.markdown(create_metric_card("Horário Indutivo", c5, value_color=cor_value, bg_color=cor_bg), unsafe_allow_html=True)
    with col6:
        st.markdown(create_metric_card("Data Reposição", c6, value_color=cor_value, bg_color=cor_bg), unsafe_allow_html=True)
    with col7:
        st.markdown(create_metric_card("Hora Reposição", c7, value_color=cor_value, bg_color=cor_bg), unsafe_allow_html=True)

    # --- Feriados ---
    st.markdown("---")
    st.markdown("**Feriados Cadastrados**")
    feriados_list = [f for f in params.filter(like='feriado_').values if f and f != '00/00/00']
    today = datetime.now()

    if not feriados_list:
        st.info("Nenhum feriado cadastrado.")
    else:
        for i in range(0, 15, 5):
            cols = st.columns(5)
            for j in range(5):
                if i + j < len(feriados_list):
                    feriado_str = feriados_list[i+j]
                    try:
                        feriado_date = datetime.strptime(feriado_str, '%d/%m/%y')
                        bg_color = '#FFEBCD' if feriado_date < today else '#D4EDDA'
                        with cols[j]:
                            st.markdown(f'<div style="padding: 0.8rem; border-radius: 0.5rem; background-color: {bg_color}; text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;"><b style="color: #333;">{feriado_str}</b></div>', unsafe_allow_html=True)
                    except ValueError:
                        with cols[j]:
                            st.markdown(f'<div style="padding: 0.8rem; border-radius: 0.5rem; background-color: #f0f2f6; text-align: center; height: 100%; display: flex; align-items: center; justify-content: center;"><b style="color: #333;">{feriado_str}</b></div>', unsafe_allow_html=True)

def display_faltas_energia(df_faltas, df_params):
    """Cria o layout para a seção de faltas de energia."""
    st.markdown("---")
    st.subheader("Faltas de Energia Registradas")
    
    df_vis = df_faltas.drop(columns=['medidor'])
    if df_vis.empty:
        st.info("Nenhuma falta de energia registrada no arquivo.")
        return

    try:
        # Converte datas e horas para objetos datetime
        df_vis['data_inicio'] = pd.to_datetime(df_vis['data_inicio'], format='%d/%m/%y %H:%M:%S', errors='coerce')
        df_vis['data_fim'] = pd.to_datetime(df_vis['data_fim'], format='%d/%m/%y %H:%M:%S', errors='coerce')
        df_vis.dropna(subset=['data_inicio', 'data_fim'], inplace=True)
        
        # Cria a lista de eventos para o gráfico
        event_points = []
        for index, row in df_vis.sort_values('data_inicio').iterrows():
            event_points.append({'Timestamp': row['data_inicio'], 'Estado': 'Ligado'})
            event_points.append({'Timestamp': row['data_inicio'], 'Estado': 'Desligado'})
            event_points.append({'Timestamp': row['data_fim'], 'Estado': 'Desligado'})
            event_points.append({'Timestamp': row['data_fim'], 'Estado': 'Ligado'})
        
        if event_points:
            df_plot = pd.DataFrame(event_points).drop_duplicates().sort_values('Timestamp')
            
            fig = px.line(
                df_plot, 
                x='Timestamp', 
                y='Estado',
                title="Linha do Tempo de Status da Energia",
                line_shape='hv' # Cria o efeito de degrau (step chart)
            )
            fig.update_layout(
                yaxis=dict(categoryorder='array', categoryarray=['Desligado', 'Ligado']),
                template="plotly_white"
            )
            st.plotly_chart(fig, use_container_width=True)

        # Calcula a duração para a tabela
        delta = df_vis['data_fim'] - df_vis['data_inicio']
        df_vis['Duração'] = delta.apply(
            lambda td: f"{td.days}d {td.seconds//3600}h {(td.seconds//60)%60}m"
        )
        df_vis['Início'] = df_vis['data_inicio'].dt.strftime('%d/%m/%Y %H:%M:%S')
        df_vis['Fim'] = df_vis['data_fim'].dt.strftime('%d/%m/%Y %H:%M:%S')

        st.markdown("**Detalhes das Interrupções**")
        st.dataframe(df_vis[['Início', 'Fim', 'Duração']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Não foi possível processar as datas de falta de energia. Exibindo dados brutos. Erro: {e}")
        st.dataframe(df_faltas.drop(columns=['medidor']), use_container_width=True, hide_index=True)

# --- Interface do Aplicativo ---
st.set_page_config(layout="wide", page_title="Analisador de Medidores ABNT")
st.title("Analisador de Arquivos ABNT")
st.markdown("Faça o upload de um arquivo de memória de massa (formato texto) para extrair os parâmetros.")

uploaded_file = st.file_uploader("Escolha um arquivo")

if uploaded_file is not None:
    if st.button("Analisar Arquivo"):
        try:
            string_data = uploaded_file.getvalue().decode('latin-1')
            
            with st.spinner("Processando arquivo..."):
                df_parametros, df_faltas, df_alteracoes = processar_arquivo_abnt(string_data)

            st.success("Arquivo processado com sucesso!")
            
            display_parametros_layout(df_parametros)
            
            display_faltas_energia(df_faltas, df_parametros)
            
            st.markdown("---")
            st.subheader("Alterações Registradas")
            df_alteracoes_vis = df_alteracoes.drop(columns=['Medidor'])
            if not df_alteracoes_vis.empty:
                st.dataframe(df_alteracoes_vis, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma alteração registrada no arquivo.")

        except Exception as e:
            st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
            st.error("Verifique se o arquivo está no formato ABNT correto e não está corrompido.")
