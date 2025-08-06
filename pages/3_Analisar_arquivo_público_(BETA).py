import streamlit as st
import pandas as pd
import io
from datetime import datetime, timedelta
import plotly.express as px

# --- FUNÇÕES DE PROCESSAMENTO DE DADOS ---

def obterDados(data, posicao, tamanho):
    """
    Extrai uma porção de dados de uma string com base na posição e tamanho.
    A posição é baseada em 1 (e não em 0 como no índice de strings do Python).
    """
    posicao = posicao - 1
    return data[posicao:(posicao + tamanho)] if len(data) >= posicao + tamanho else ""

def processar_parametros_gerais(file_content):
    """
    Processa os parâmetros gerais do arquivo, ignorando quebras de linha.
    Retorna um DataFrame com os parâmetros e um dicionário de grandezas.
    """
    dados = file_content.replace('\n', '').replace('\r', '')

    colunas = [
        'medidor', 'data_hora_leitura', 'data_hora_mm', 'intervalo_mm', 'intervalo_demanda',
        'constante_canal_1', 'constante_canal_2', 'constante_canal_3',
        'estado_bateria', 'carga_md', 'versao_hardware', 'reservado_ativo', 'horario_reservado',
        'reservado_sabado', 'reservado_domingo', 'reservado_feriado',
        'horario_verao', 'horario_FP', 'horario_P', 'horario_indutivo', 'horario_capacitivo',
        'data_reposicao_demanda', 'hora_reposicao_demanda',
        'grandeza_1o_canal', 'grandeza_2o_canal', 'grandeza_3o_canal'
    ] + [f'feriado_{i}' for i in range(1, 16)] + [
        'data_inicio_conj1_segm_horarios', 'data_inicio_conj2_segm_horarios',
        'hora_inicio_posto_P_conj2', 'hora_inicio_posto_FP_conj2', 'hora_inicio_posto_reservado_conj2'
    ]
    
    # Extração dos dados
    medidor = obterDados(dados, 1, 8)
    data_hora_leitura = f"{obterDados(dados, 21, 2)}/{obterDados(dados, 23, 2)}/{obterDados(dados, 25, 2)} {obterDados(dados, 15, 2)}:{obterDados(dados, 17, 2)}:{obterDados(dados, 19, 2)}"
    data_hora_mm = f"{obterDados(dados, 21, 2)}/{obterDados(dados, 23, 2)}/{obterDados(dados, 25, 2)} {obterDados(dados, 29, 2)}:{obterDados(dados, 31, 2)}:{obterDados(dados, 33, 2)}"
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
    grandeza_1o_canal = obterDados(dados, 2309, 2)
    grandeza_2o_canal = obterDados(dados, 2311, 2)
    grandeza_3o_canal = obterDados(dados, 2313, 2)
    feriados = [f"{obterDados(dados, p, 2)}/{obterDados(dados, p+2, 2)}/{obterDados(dados, p+4, 2)}" for p in range(171, 171 + 15 * 6, 6)]
    data_inicio_conj1_segm_horarios = f"{obterDados(dados, 2239, 2)}/{obterDados(dados, 2241, 2)}"
    data_inicio_conj2_segm_horarios = f"{obterDados(dados, 2243, 2)}/{obterDados(dados, 2245, 2)}"
    hora_inicio_posto_P_conj2 = f"{obterDados(dados, 2255, 2)}:{obterDados(dados, 2257, 2)}"
    hora_inicio_posto_FP_conj2 = f"{obterDados(dados, 2271, 2)}:{obterDados(dados, 2273, 2)}"
    hora_inicio_posto_reservado_conj2 = f"{obterDados(dados, 2287, 2)}:{obterDados(dados, 2289, 2)}"

    linha_parametros = [
        medidor, data_hora_leitura, data_hora_mm, intervalo_mm, intervalo_demanda, constante_canal_1,
        constante_canal_2, constante_canal_3, estado_bateria, carga_md, versao_hardware,
        reservado_ativo, horario_reservado, reservado_sabado, reservado_domingo, reservado_feriado,
        horario_verao, horario_FP, horario_P, horario_indutivo, horario_capacitivo,
        data_reposicao_demanda, hora_reposicao_demanda, grandeza_1o_canal, grandeza_2o_canal,
        grandeza_3o_canal
    ] + feriados + [
        data_inicio_conj1_segm_horarios, data_inicio_conj2_segm_horarios,
        hora_inicio_posto_P_conj2, hora_inicio_posto_FP_conj2, hora_inicio_posto_reservado_conj2
    ]
    
    df_parametros = pd.DataFrame([linha_parametros], columns=colunas)
    
    # Dicionário de grandezas para uso posterior
    grandezas = {
        '01': 'Wh', '10': 'varind', '11': 'varcap', '14': '-Wh', '15': '-varind', '16': '-varcap',
        '17': 'v_a', '18': 'v_b', '19': 'v_c', '20': 'i_a', '21': 'i_b', '22': 'i_c'
    }
    
    return df_parametros, grandezas

def processar_memoria_massa(file_content_raw, params, grandezas_legend):
    """
    Processa as linhas de Memória de Massa (MM) do arquivo.
    """
    linhas_mm = [line for line in file_content_raw.splitlines() if line.startswith(('SALV', 'CONT'))]
    if not linhas_mm:
        return pd.DataFrame()

    # Extrai os valores dos canais de todas as linhas
    c1_vals, c2_vals, c3_vals = [], [], []
    for linha in linhas_mm:
        for i in range(24):
            base_pos = 13 + (i * 12)
            c1_vals.append(int(obterDados(linha, base_pos, 4)))
            c2_vals.append(int(obterDados(linha, base_pos + 4, 4)))
            c3_vals.append(int(obterDados(linha, base_pos + 8, 4)))
    
    # Calcula o range de datas
    try:
        last_timestamp = datetime.strptime(params['data_hora_mm'].iloc[0], '%d/%m/%y %H:%M:%S')
        num_records = len(c1_vals)
        intervalo = int(params['intervalo_mm'].iloc[0])
        start_timestamp = last_timestamp - timedelta(minutes=intervalo * (num_records - 1))
        timestamps = pd.date_range(start=start_timestamp, periods=num_records, freq=f'{intervalo}T')
    except (ValueError, IndexError):
        return pd.DataFrame()

    df = pd.DataFrame({
        'Timestamp': timestamps,
        'C1': c1_vals,
        'C2': c2_vals,
        'C3': c3_vals,
    })
    
    df['Data'] = df['Timestamp'].dt.strftime('%d/%m/%Y')
    df['Hora'] = df['Timestamp'].dt.strftime('%H:%M:%S')

    # Prepara lista de feriados para verificação
    feriados_str_list = [f for f in params.filter(like='feriado_').iloc[0].values if f and f != '00/00/00']
    feriados_dates = set()
    for f_str in feriados_str_list:
        try:
            feriados_dates.add(datetime.strptime(f_str, '%d/%m/%y').date())
        except ValueError:
            continue # Ignora feriados com formato inválido

    # Calcula o posto horário com validação
    time_p = datetime.strptime(params['horario_P'].iloc[0], '%H:%M').time()
    time_fp = datetime.strptime(params['horario_FP'].iloc[0], '%H:%M').time()
    reservado_ativo = params['reservado_ativo'].iloc[0] == 'Sim'
    time_res = None

    if reservado_ativo:
        try:
            time_res = datetime.strptime(params['horario_reservado'].iloc[0], '%H:%M').time()
        except ValueError:
            st.warning(f"Aviso: O horário reservado ('{params['horario_reservado'].iloc[0]}') é inválido e será ignorado.")
            reservado_ativo = False

    def get_posto(t):
        # Verifica se é sábado (5) ou domingo (6)
        if t.weekday() >= 5:
            return "Fora Ponta"
            
        # Verifica se é feriado
        if t.date() in feriados_dates:
            return "Fora Ponta"
        
        current_time = t.time()
        if reservado_ativo and current_time > time_res and current_time <= time_fp:
            return "Reservado"
        if current_time > time_p and current_time <= time_fp:
            return "Ponta"
        return "Fora Ponta"
    
    df['Posto Horário'] = df['Timestamp'].apply(get_posto)

    # Adiciona colunas de grandezas calculadas
    final_cols_order = ['Timestamp', 'Data', 'Hora'] # Mantém o Timestamp para o filtro
    grandezas_params = params.filter(like='grandeza_').iloc[0]

    for i, g_code in enumerate(grandezas_params):
        canal_num = i + 1
        g_name = grandezas_legend.get(g_code)
        
        if g_name and g_code in ['01', '10', '11', '14', '15', '16']:
            df[g_name] = df[f'C{canal_num}'] * 12
            final_cols_order.append(g_name)
        
        final_cols_order.append(f'C{canal_num}')

    final_cols_order.append('Posto Horário')
    
    # Filtra e reordena o DF para a exibição final
    existing_cols = [col for col in final_cols_order if col in df.columns]
    
    return df[existing_cols]

def processar_alteracoes_e_faltas(file_content):
    """Processa as seções de Faltas de Energia e Alterações."""
    dados = file_content.replace('\n', '').replace('\r', '')
    medidor = obterDados(dados, 1, 8)

    # Faltas de Energia
    faltas = []
    for i in range(15):
        pos = 329 + (i * 24)
        falta_str = obterDados(dados, pos, 24)
        if falta_str and falta_str != '000000000000000000000000':
            inicio = f"{falta_str[6:8]}/{falta_str[8:10]}/{falta_str[10:12]} {falta_str[0:2]}:{falta_str[2:4]}:{falta_str[4:6]}"
            fim = f"{falta_str[18:20]}/{falta_str[20:22]}/{falta_str[22:24]} {falta_str[12:14]}:{falta_str[14:16]}:{falta_str[16:18]}"
            faltas.append([medidor, inicio, fim])
    df_faltas = pd.DataFrame(faltas, columns=['medidor', 'data_inicio', 'data_fim']).drop_duplicates()

    # Alterações
    codigos_alteracoes = {
        11: 'Envio de senha', 12: 'Programação de código de cliente', 13: 'Pedido de string', 20: 'Leitura com reposição de demanda',
        21: 'Leitura s/ reposição atuais', 22: 'Leitura s/ reposição anteriores', 23: 'Leitura de regs. após última reposição',
        99: 'Comando para carga rápida de programa'
    }
    alteracoes = []
    for i in range(15):
        pos = 1927 + (i * 20)
        alt_str = obterDados(dados, pos, 20)
        if alt_str and alt_str != '00000000000000000000':
            try:
                codigo = int(alt_str[0:2])
                num_serie_leitor = alt_str[2:8]
                hora = f"{alt_str[8:10]}:{alt_str[10:12]}:{alt_str[12:14]}"
                data = f"{alt_str[14:16]}/{alt_str[16:18]}/{alt_str[18:20]}"
                descricao = codigos_alteracoes.get(codigo, f"Código desconhecido ({codigo})")
                alteracoes.append([medidor, num_serie_leitor, codigo, descricao, f"{data} {hora}"])
            except (ValueError, IndexError):
                continue
    df_alteracoes = pd.DataFrame(alteracoes, columns=['Medidor', 'Leitora', 'Código', 'Descrição', 'Data da alteração']).drop_duplicates()

    return df_faltas, df_alteracoes

# --- FUNÇÕES DE VISUALIZAÇÃO ---

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

def display_parametros_layout(df, grandezas_legend):
    """Cria o layout visual para a seção de parâmetros gerais."""
    params = df.iloc[0]
    st.markdown("---")

    # --- Primeira Linha ---
    col1, col2, col3, col4, col5, col6, col7 = st.columns([1.5, 3, 1, 1.5, 1, 1.5, 2])
    with col1:
        st.markdown(create_metric_card("Medidor", params['medidor']), unsafe_allow_html=True)
    with col2:
        st.markdown(create_metric_card("Data/Hora da Leitura", params['data_hora_leitura']), unsafe_allow_html=True)
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
        st.markdown(create_metric_card("Carga do MD", params['carga_md']), unsafe_allow_html=True)
    with col7:
        st.markdown(create_metric_card("Versão do Hardware", params['versao_hardware']), unsafe_allow_html=True)

    # --- Segunda Linha (Constantes) ---
    st.markdown("---")
    st.markdown("**Constantes**")
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

    # --- Nova Linha (Grandezas) ---
    st.markdown("---")
    st.markdown("**Grandezas dos Canais**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Canal 1", grandezas_legend.get(params['grandeza_1o_canal'], "N/A"))
    with col2:
        st.metric("Canal 2", grandezas_legend.get(params['grandeza_2o_canal'], "N/A"))
    with col3:
        st.metric("Canal 3", grandezas_legend.get(params['grandeza_3o_canal'], "N/A"))

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

def display_faltas_energia(df_faltas):
    """Cria o layout para a seção de faltas de energia."""
    st.markdown("---")
    st.subheader("Faltas de Energia Registradas")
    
    df_vis = df_faltas.drop(columns=['medidor'])
    if df_vis.empty:
        st.info("Nenhuma falta de energia registrada no arquivo.")
        return

    try:
        df_vis['data_inicio'] = pd.to_datetime(df_vis['data_inicio'], format='%d/%m/%y %H:%M:%S', errors='coerce')
        df_vis['data_fim'] = pd.to_datetime(df_vis['data_fim'], format='%d/%m/%y %H:%M:%S', errors='coerce')
        df_vis.dropna(subset=['data_inicio', 'data_fim'], inplace=True)
        
        event_points = []
        for _, row in df_vis.sort_values('data_inicio').iterrows():
            event_points.extend([
                {'Timestamp': row['data_inicio'], 'Estado': 'Ligado'},
                {'Timestamp': row['data_inicio'], 'Estado': 'Desligado'},
                {'Timestamp': row['data_fim'], 'Estado': 'Desligado'},
                {'Timestamp': row['data_fim'], 'Estado': 'Ligado'}
            ])
        
        if event_points:
            df_plot = pd.DataFrame(event_points).drop_duplicates().sort_values('Timestamp')
            fig = px.line(df_plot, x='Timestamp', y='Estado', title="Linha do Tempo de Status da Energia", line_shape='hv')
            fig.update_layout(yaxis=dict(categoryorder='array', categoryarray=['Desligado', 'Ligado']), template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

        delta = df_vis['data_fim'] - df_vis['data_inicio']
        df_vis['Duração'] = delta.apply(lambda td: f"{td.days}d {td.seconds//3600}h {(td.seconds//60)%60}m")
        df_vis['Início'] = df_vis['data_inicio'].dt.strftime('%d/%m/%Y %H:%M:%S')
        df_vis['Fim'] = df_vis['data_fim'].dt.strftime('%d/%m/%Y %H:%M:%S')
        st.markdown("**Detalhes das Interrupções**")
        st.dataframe(df_vis[['Início', 'Fim', 'Duração']], use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Não foi possível processar as datas de falta de energia: {e}")
        st.dataframe(df_faltas.drop(columns=['medidor']), use_container_width=True, hide_index=True)

# --- INTERFACE PRINCIPAL DO APLICATIVO ---

st.set_page_config(layout="wide", page_title="Analisador de Medidores ABNT")
st.title("Analisador de Arquivos ABNT")
st.markdown("Faça o upload de um arquivo de memória de massa (formato texto) para extrair os parâmetros.")

uploaded_file = st.file_uploader("Escolha um arquivo", label_visibility="collapsed")

if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if uploaded_file is not None:
    if st.button("Analisar Arquivo"):
        try:
            string_data = uploaded_file.getvalue().decode('latin-1')
            
            with st.spinner("Processando arquivo..."):
                st.session_state.df_parametros, st.session_state.grandezas_legend = processar_parametros_gerais(string_data)
                st.session_state.df_mm = processar_memoria_massa(string_data, st.session_state.df_parametros, st.session_state.grandezas_legend)
                st.session_state.df_faltas, st.session_state.df_alteracoes = processar_alteracoes_e_faltas(string_data)
                st.session_state.analysis_done = True

        except Exception as e:
            st.error(f"Ocorreu um erro geral ao processar o arquivo: {e}")
            st.error("Verifique se o arquivo está no formato ABNT correto e não está corrompido.")
            st.session_state.analysis_done = False

if st.session_state.analysis_done:
    tab1, tab2 = st.tabs(["Parâmetros Gerais", "Análise de MM"])

    with tab1:
        display_parametros_layout(st.session_state.df_parametros, st.session_state.grandezas_legend)
        display_faltas_energia(st.session_state.df_faltas)
        
        st.markdown("---")
        st.subheader("Alterações Registradas")
        df_alteracoes_vis = st.session_state.df_alteracoes.drop(columns=['Medidor'])
        if not df_alteracoes_vis.empty:
            st.dataframe(df_alteracoes_vis, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma alteração registrada no arquivo.")
    
    with tab2:
        st.subheader("Análise de Memória de Massa")
        if not st.session_state.df_mm.empty:
            
            # --- Slider de Data ---
            min_ts = st.session_state.df_mm['Timestamp'].min()
            max_ts = st.session_state.df_mm['Timestamp'].max()
            intervalo_minutos = int(st.session_state.df_parametros['intervalo_mm'].iloc[0])
            
            if min_ts != max_ts:
                selected_range = st.slider(
                    'Filtre o período para análise:',
                    min_value=min_ts.to_pydatetime(),
                    max_value=max_ts.to_pydatetime(),
                    value=(min_ts.to_pydatetime(), max_ts.to_pydatetime()),
                    format="DD/MM/YYYY - HH:mm",
                    step=timedelta(minutes=intervalo_minutos)
                )
                start_ts, end_ts = selected_range
            else:
                start_ts, end_ts = min_ts, max_ts

            df_mm_filtrado = st.session_state.df_mm[
                (st.session_state.df_mm['Timestamp'] >= start_ts) & 
                (st.session_state.df_mm['Timestamp'] <= end_ts)
            ]

            with st.expander("Ver dados detalhados da Memória de Massa (filtrado)"):
                st.dataframe(df_mm_filtrado.drop(columns=['Timestamp']), use_container_width=True)
            
            # Sumarização
            st.markdown("---")
            st.markdown("**Consumo Sumarizado por Posto Horário (filtrado)**")
            
            grandeza_c1_code = st.session_state.df_parametros['grandeza_1o_canal'].iloc[0]
            grandeza_c1_name = st.session_state.grandezas_legend.get(grandeza_c1_code)

            if grandeza_c1_name and grandeza_c1_name in df_mm_filtrado.columns:
                summary = df_mm_filtrado.groupby('Posto Horário')[grandeza_c1_name].sum().to_dict()
                
                ponta_val = (summary.get('Ponta', 0) / 12) / 1000
                fponta_val = (summary.get('Fora Ponta', 0) / 12) / 1000
                res_val = (summary.get('Reservado', 0) / 12) / 1000

                cols = st.columns(3)
                with cols[0]:
                    st.markdown(create_metric_card("Consumo Ponta (kWh)", f"{ponta_val:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")), unsafe_allow_html=True)
                with cols[1]:
                    st.markdown(create_metric_card("Consumo Fora Ponta (kWh)", f"{fponta_val:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")), unsafe_allow_html=True)
                if res_val > 0:
                    with cols[2]:
                        st.markdown(create_metric_card(f"Consumo Reservado (kWh)", f"{res_val:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")), unsafe_allow_html=True)

            else:
                st.info(f"A grandeza do Canal 1 ({grandeza_c1_name or 'N/A'}) não é apropriada para sumarização ou não foi encontrada.")

        else:
            st.warning("Não foi possível processar os dados da Memória de Massa (linhas 'SALV'/'CONT').")
