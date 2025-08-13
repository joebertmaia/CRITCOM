import streamlit as st
import pandas as pd
import re
from io import StringIO
import streamlit.components.v1 as components
import json

# --- Configuração da Página ---
st.set_page_config(
    page_title="Um medidor",
    page_icon="https://www.energisa.com.br/sites/energisa/files/Energisa120%20%281%29.ico",
    layout="wide",
    menu_items={
        'About': "Versão 1.2.0. Bugs ou sugestões, enviar um e-mail para joebert.oliveira@energisa.com.br"}
)

st.logo(
    "CRITCOM.svg",
    icon_image="CRITCOM.svg",
)

# --- FUNÇÕES DE PROCESSAMENTO (NÃO MODIFICAR) ---

def processar_dados_consumo(texto_bruto):
    """
    Processa o texto bruto colado pelo usuário para extrair, limpar e somar os dados de consumo.
    Esta versão lê o cabeçalho e retorna tanto os resultados agregados quanto o DataFrame bruto.
    """
    header_match = re.search(r"^Data\s+Dia\s+Postos horários\s+(.*)$", texto_bruto, re.MULTILINE)
    if not header_match:
        return None
    header_string = header_match.group(1).strip()
    colunas_dados = [col.strip() for col in header_string.split('\t')]
    num_colunas_dados = len(colunas_dados)
    valor_pattern = r"([\d.,-]+)"
    regex_parts = [
        r"^(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2})",
        r"([A-Za-zçáéíóúãõâêôü]+)",
        r"(Fora Ponta|Ponta|Reservado)"
    ]
    regex_parts.extend([valor_pattern] * num_colunas_dados)
    padrao_dados_str = r"\s+".join(regex_parts) + r"$"
    padrao_dados = re.compile(padrao_dados_str, re.MULTILINE)
    dados_encontrados = padrao_dados.findall(texto_bruto)
    if not dados_encontrados:
        return None
    colunas_df = ['DataHora', 'Dia', 'Posto Horario'] + colunas_dados
    df = pd.DataFrame(dados_encontrados, columns=colunas_df)
    df['DataHora'] = pd.to_datetime(df['DataHora'], format='%d/%m/%Y %H:%M')
    
    for nome_coluna in colunas_dados:
        df[nome_coluna] = pd.to_numeric(
            df[nome_coluna].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
            errors='coerce'
        )
    
    # A agregação será feita depois, se necessário
    return df

def processar_dados_demanda(texto_bruto):
    """
    Processa dados de demanda, identificando cabeçalhos e retornando o DataFrame bruto.
    A lógica de cálculo (soma ou máximo) foi movida para uma função separada.
    """
    header_match = re.search(r"^Data\s+Dia\s+Postos horários\s+(.*)$", texto_bruto, re.MULTILINE)
    if not header_match:
        return None
    header_string = header_match.group(1).strip()
    colunas_dados = [col.strip() for col in header_string.split('\t')]
    num_colunas_dados = len(colunas_dados)
    valor_pattern = r"([\d.,-]+)"
    regex_parts = [
        r"^(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2})",
        r"([A-Za-zçáéíóúãõâêôü]+)",
        r"(Fora Ponta|Ponta|Reservado)"
    ]
    regex_parts.extend([valor_pattern] * num_colunas_dados)
    padrao_dados_str = r"\s+".join(regex_parts) + r"$"
    padrao_dados = re.compile(padrao_dados_str, re.MULTILINE)
    dados_encontrados = padrao_dados.findall(texto_bruto)
    if not dados_encontrados:
        return None
    colunas_df = ['DataHora', 'Dia', 'Posto Horario'] + colunas_dados
    df = pd.DataFrame(dados_encontrados, columns=colunas_df)
    df['DataHora'] = pd.to_datetime(df['DataHora'], format='%d/%m/%Y %H:%M')
    
    for nome_coluna in colunas_dados:
        df[nome_coluna] = pd.to_numeric(
            df[nome_coluna].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
            errors='coerce'
        )
    return df

def recalcular_resultados(df, tipo_calculo='consumo'):
    """
    Calcula os resultados agregados (soma ou máximo) a partir de um DataFrame.
    """
    if df is None:
        return None

    resultados = {}
    colunas_dados = [col for col in df.columns if col not in ['DataHora', 'Dia', 'Posto Horario']]

    for nome_coluna in colunas_dados:
        if tipo_calculo == 'demanda':
            if nome_coluna.strip().upper() == "UFER":
                operacao = 'soma'
                calculo = df.groupby('Posto Horario')[nome_coluna].sum()
            else:
                operacao = 'máximo'
                calculo = df.groupby('Posto Horario')[nome_coluna].max()
        else: # Consumo
            operacao = 'soma'
            calculo = df.groupby('Posto Horario')[nome_coluna].sum()

        resultados[nome_coluna] = {
            'operacao': operacao,
            'valores': {
                'Fora Ponta': calculo.get('Fora Ponta', 0.0),
                'Ponta': calculo.get('Ponta', 0.0),
                'Reservado': calculo.get('Reservado', 0.0)
            }
        }
        resultados[nome_coluna]['valores'] = {k: (v if pd.notna(v) else 0.0) for k, v in resultados[nome_coluna]['valores'].items()}
    return resultados


# --- FUNÇÃO PARA EXTRAIR INFORMAÇÕES DO CLIENTE ---
def extrair_info_cliente(texto_bruto):
    info = {"contrato": "Não encontrado", "serial": "Não encontrado"}
    if not texto_bruto:
        return info

    contrato_match = re.search(r"Cliente \(contrato\)\s+(\d+)", texto_bruto)
    if contrato_match:
        info["contrato"] = contrato_match.group(1)

    serial_match = re.search(r"Medidor \(serial\)\s+(\d+)", texto_bruto)
    if not serial_match: # Tenta um padrão alternativo
        serial_match = re.search(r"Medidor\s+(\d+)", texto_bruto)

    if serial_match:
        info["serial"] = serial_match.group(1)
        
    return info

# --- Função que define o conteúdo do diálogo ---
@st.dialog("Resultados do Cálculo", width='large')
def show_results_dialog(df_resultados, df_consumo_raw, df_demanda_raw):
    """Exibe o DataFrame de resultados e gráficos dentro de um diálogo."""
    
    # --- Geração Manual da Tabela HTML ---
    header_html = "<thead><tr>"
    for col_name in df_resultados.columns:
        header_html += f'<th>{col_name}</th>'
    header_html += "</tr></thead>"

    body_html = "<tbody>"
    for _, row in df_resultados.iterrows():
        if str(row.iloc[0]).startswith('---'):
            body_html += f'<tr class="separator-row"><td colspan="{len(df_resultados.columns)}">{row.iloc[0]}</td></tr>'
        else:
            body_html += "<tr>"
            for cell_value in row:
                body_html += f'<td>{cell_value}</td>'
            body_html += "</tr>"
    body_html += "</tbody>"

    table_html = f"<table>{header_html}{body_html}</table>"
    
    # Prepara dados para os gráficos
    chart_data_consumo_fornecido = None
    if df_consumo_raw is not None and 'kWh fornecido' in df_consumo_raw.columns:
        df_fornecido = df_consumo_raw[['DataHora', 'kWh fornecido']].dropna()
        df_fornecido['DataHora'] = df_fornecido['DataHora'].apply(lambda x: x.isoformat())
        chart_data_consumo_fornecido = df_fornecido.to_dict(orient='records')

    chart_data_consumo_recebido = None
    if df_consumo_raw is not None and 'kWh recebido' in df_consumo_raw.columns:
        df_recebido = df_consumo_raw[['DataHora', 'kWh recebido']].dropna()
        df_recebido['DataHora'] = df_recebido['DataHora'].apply(lambda x: x.isoformat())
        chart_data_consumo_recebido = df_recebido.to_dict(orient='records')

    chart_data_demanda_fornecido = None
    if df_demanda_raw is not None and 'kW fornecido' in df_demanda_raw.columns:
        df_dem_fornecido = df_demanda_raw[['DataHora', 'kW fornecido']].dropna()
        df_dem_fornecido['DataHora'] = df_dem_fornecido['DataHora'].apply(lambda x: x.isoformat())
        chart_data_demanda_fornecido = df_dem_fornecido.to_dict(orient='records')

    chart_data_demanda_recebido = None
    if df_demanda_raw is not None and 'kW recebido' in df_demanda_raw.columns:
        df_dem_recebido = df_demanda_raw[['DataHora', 'kW recebido']].dropna()
        df_dem_recebido['DataHora'] = df_dem_recebido['DataHora'].apply(lambda x: x.isoformat())
        chart_data_demanda_recebido = df_dem_recebido.to_dict(orient='records')
        
    chart_data_dmcr = None
    if df_demanda_raw is not None and 'DMCR' in df_demanda_raw.columns:
        df_dmcr = df_demanda_raw[['DataHora', 'DMCR']].dropna()
        df_dmcr['DataHora'] = df_dmcr['DataHora'].apply(lambda x: x.isoformat())
        chart_data_dmcr = df_dmcr.to_dict(orient='records')

    chart_data_ufer = None
    if df_demanda_raw is not None and 'UFER' in df_demanda_raw.columns:
        df_ufer = df_demanda_raw[['DataHora', 'UFER']].dropna()
        df_ufer['DataHora'] = df_ufer['DataHora'].apply(lambda x: x.isoformat())
        chart_data_ufer = df_ufer.to_dict(orient='records')

    # Cria o componente HTML com a tabela, os gráficos e a função de cópia
    components.html(f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom/dist/chartjs-plugin-zoom.min.js"></script>

        <style>
            .capture-area {{ padding: 10px; background-color: #ffffff; }}
            table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #e0e0e0; padding: 8px; text-align: center; }}
            th {{ background-color: #f0f2f6; }}
            .button-container {{ text-align: right; margin-top: 10px; margin-bottom: 20px; }}
            .copy-button {{ background-color: #0068c9; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer; }}
            .copy-button:hover {{ background-color: #0055a3; }}
            h3 {{ font-family: sans-serif; }}
            tr.separator-row td {{
                text-align: center;
                font-weight: bold;
                background-color: #e8e8e8;
                border-left: 1px solid #e0e0e0;
                border-right: 1px solid #e0e0e0;
            }}
        </style>
        
        <div id="captureTable" class="capture-area">
            {table_html}
        </div>
        <div class="button-container">
            <button class="copy-button" onclick="copyElementAsImage('captureTable', this)">Copiar Tabela como Imagem</button>
        </div>

        <div id="consumoChartContainer"></div>
        <div id="demandaChartContainer"></div>

        <script>
            let consumoChart = null;
            let demandaChart = null;
            const chartDataConsumoFornecido = {json.dumps(chart_data_consumo_fornecido)};
            const chartDataConsumoRecebido = {json.dumps(chart_data_consumo_recebido)};
            const chartDataDemandaFornecido = {json.dumps(chart_data_demanda_fornecido)};
            const chartDataDemandaRecebido = {json.dumps(chart_data_demanda_recebido)};
            const chartDataDmcr = {json.dumps(chart_data_dmcr)};
            const chartDataUfer = {json.dumps(chart_data_ufer)};

            function createChart(containerId, chartInstanceVar, chartTitle, datasets) {{
                if (datasets.length === 0) return;

                const container = document.getElementById(containerId);
                container.innerHTML = `
                    <div id="capture-${{containerId}}" class="capture-area">
                        <h3>${{chartTitle}}</h3>
                        <canvas id="canvas-${{containerId}}"></canvas>
                    </div>
                    <div class="button-container">
                        <button class="copy-button" onclick="copyChartAsImage('${{chartInstanceVar}}', this)">Copiar Gráfico como Imagem</button>
                    </div>
                `;

                const ctx = document.getElementById(`canvas-${{containerId}}`).getContext('2d');
                window[chartInstanceVar] = new Chart(ctx, {{
                    type: 'line',
                    data: {{ datasets: datasets }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {{ zoom: {{ zoom: {{ wheel: {{ enabled: true }}, pinch: {{ enabled: true }}, mode: 'x' }} }} }},
                        scales: {{ x: {{ type: 'time', time: {{ unit: 'day' }} }} }}
                    }}
                }});
            }}

            // Cria gráfico de consumo
            const consumoDatasets = [];
            if (chartDataConsumoFornecido) consumoDatasets.push({{ label: 'kWh fornecido', data: chartDataConsumoFornecido.map(item => ({{x: new Date(item.DataHora), y: item['kWh fornecido']}})), borderColor: 'rgb(75, 192, 192)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartDataConsumoRecebido) consumoDatasets.push({{ label: 'kWh recebido', data: chartDataConsumoRecebido.map(item => ({{x: new Date(item.DataHora), y: item['kWh recebido']}})), borderColor: 'rgb(255, 99, 132)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            createChart('consumoChartContainer', 'consumoChart', 'Gráfico - Consumo', consumoDatasets);

            // Cria gráfico de demanda
            const demandaDatasets = [];
            if (chartDataDemandaFornecido) demandaDatasets.push({{ label: 'kW fornecido', data: chartDataDemandaFornecido.map(item => ({{x: new Date(item.DataHora), y: item['kW fornecido']}})), borderColor: 'rgb(54, 162, 235)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartDataDemandaRecebido) demandaDatasets.push({{ label: 'kW recebido', data: chartDataDemandaRecebido.map(item => ({{x: new Date(item.DataHora), y: item['kW recebido']}})), borderColor: 'rgb(255, 159, 64)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartDataDmcr) demandaDatasets.push({{ label: 'DMCR', data: chartDataDmcr.map(item => ({{x: new Date(item.DataHora), y: item['DMCR']}})), borderColor: 'rgb(153, 102, 255)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartDataUfer) demandaDatasets.push({{ label: 'UFER', data: chartDataUfer.map(item => ({{x: new Date(item.DataHora), y: item['UFER']}})), borderColor: 'rgb(75, 192, 75)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            createChart('demandaChartContainer', 'demandaChart', 'Gráfico - Demanda', demandaDatasets);

            function copyChartAsImage(chartInstanceVar, button) {{
                const chartInstance = window[chartInstanceVar];
                if (!chartInstance) return;
                const originalText = button.innerText;
                button.innerText = 'Copiando...';

                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = 2000;
                tempCanvas.height = 750;
                const tempCtx = tempCanvas.getContext('2d');
                
                const whiteBackgroundPlugin = {{
                    id: 'whiteBackground',
                    beforeDraw: (chart) => {{
                        const ctx = chart.canvas.getContext('2d');
                        ctx.save();
                        ctx.globalCompositeOperation = 'destination-over';
                        ctx.fillStyle = 'white';
                        ctx.fillRect(0, 0, chart.width, chart.height);
                        ctx.restore();
                    }}
                }};
                
                const visibleDatasets = chartInstance.config.data.datasets.filter((_, index) => chartInstance.isDatasetVisible(index));

                const tempConfig = {{
                    type: 'line',
                    data: {{ ...chartInstance.config.data, datasets: visibleDatasets }},
                    options: {{
                        ...chartInstance.config.options,
                        responsive: false,
                        maintainAspectRatio: false,
                        animation: false,
                        plugins: {{
                            ...chartInstance.config.options.plugins,
                            legend: {{
                                labels: {{
                                    font: {{
                                        size: 24 // Aumenta a fonte da legenda
                                    }}
                                }}
                            }}
                        }},
                        scales: {{
                            ...chartInstance.config.options.scales,
                            x: {{ 
                                ...chartInstance.config.options.scales.x, 
                                min: chartInstance.scales.x.min, 
                                max: chartInstance.scales.x.max,
                                ticks: {{
                                    font: {{
                                        size: 20 // Aumenta a fonte do eixo X
                                    }}
                                }}
                            }},
                            y: {{
                                ...chartInstance.config.options.scales.y,
                                ticks: {{
                                    font: {{
                                        size: 20 // Aumenta a fonte do eixo Y
                                    }}
                                }}
                            }}
                        }}
                    }},
                    plugins: [whiteBackgroundPlugin]
                }};

                new Chart(tempCtx, tempConfig);

                setTimeout(() => {{
                    tempCanvas.toBlob(function(blob) {{
                        navigator.clipboard.write([
                            new ClipboardItem({{ 'image/png': blob }})
                        ]).then(() => {{
                            button.innerText = 'Copiado!';
                            setTimeout(() => {{ button.innerText = originalText; }}, 2000);
                        }}).catch(err => {{
                            console.error('Erro ao copiar: ', err);
                            button.innerText = 'Falha ao copiar';
                            setTimeout(() => {{ button.innerText = originalText; }}, 2000);
                        }});
                    }});
                }}, 250);
            }}

            function copyElementAsImage(elementId, button) {{
                const captureElement = document.getElementById(elementId);
                const originalText = button.innerText;
                button.innerText = 'Copiando...';

                html2canvas(captureElement, {{ scale: 4 }}).then(canvas => {{
                    canvas.toBlob(function(blob) {{
                        navigator.clipboard.write([
                            new ClipboardItem({{ 'image/png': blob }})
                        ]).then(() => {{
                            button.innerText = 'Copiado!';
                            setTimeout(() => {{ button.innerText = originalText; }}, 2000);
                        }}).catch(err => {{
                            console.error('Erro ao copiar: ', err);
                            button.innerText = 'Falha ao copiar';
                            setTimeout(() => {{ button.innerText = originalText; }}, 2000);
                        }});
                    }});
                }});
            }}
        </script>
    """, width=1000, height=700, scrolling=True)

    if st.button("Fechar", key="close_dialog"):
        st.rerun()

# --- Interface do Aplicativo ---
st.title("Confirmação para 1 MD")
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 400px !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    dados1, dados2 = st.columns(2)
    with dados1:
        consumo_injecao = st.text_area("kWh/kWh Inj:", height=200, placeholder="Dê um Ctrl+A no relatório de consumo, Ctrl+C e cole aqui.", key="consumo_injecao")
    with dados2:
        kW_kwinj_dre_ere = st.text_area("kW/DRE/ERE:", height=200, placeholder="Dê um Ctrl+A no relatório de demanda, Ctrl+C e cole aqui.", key="kW_kwinj_dre_ere")

# --- Seção de Parâmetros de Cálculo ---
constante = st.number_input("Constante:",min_value=0.0,value=1.0,step=0.01,format="%.4f")
col_tipo, col_perdas = st.columns(2)
with col_tipo:
    tipo_opcao = st.radio("Tipo:",("Grandeza", "Grandeza EAC", "Pulso"),horizontal=False,key="tipo",captions=["","Comum em medidores SL7000 da EAC.", "Maioria dos pontos da ERO."])
with col_perdas:
    perdas_opcao = st.radio("Perdas? :warning: **Não adicionar quando digitar no SILCO** :warning:",("Não", "Sim"),horizontal=False,key="perdas", captions=["Se o cliente possuir TP e TC.","Para medições diretas ou em baixa tensão (apenas TC)."])

# --- Botões de Ação ---
st.markdown("")
col_btn1, col_btn2 = st.columns([1, 2])

# --- Função de limpeza atualizada ---
def clear_all_text():
    st.session_state.consumo_injecao = ""
    st.session_state.kW_kwinj_dre_ere = ""
    # Limpa os dados processados e os DataFrames do estado da sessão
    keys_to_clear = ['dados_processados', 'df_consumo', 'df_demanda_original', 'df_demanda_filtrado', 'demanda_range_slider']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

with col_btn1:
    calculate_button = st.button("CALCULAR")

with col_btn2:
    st.button("LIMPAR DADOS", key="clear", on_click=clear_all_text, type="primary")

# --- Estilos dos Botões ---
st.markdown("""
<style>
    /* Botão Verde para 'Calcular' */
    div[data-testid="stButton"] > button:not([kind="primary"]) {
        background-color: #28a745 !important;
        color: white !important;
        border-color: #28a745 !important;
    }
    /* Botão Vermelho para 'Limpar' */
    button[kind="primary"] {
        background-color: #D9534F !important;
        color: white !important;
        border-color: #D43F3A !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Lógica de Processamento Inicial ---
if calculate_button:
    if consumo_injecao:
        with st.spinner("Processando dados de Consumo/Injeção..."):
            st.session_state.df_consumo = processar_dados_consumo(consumo_injecao)
    else:
        st.session_state.df_consumo = None

    if kW_kwinj_dre_ere:
        with st.spinner("Processando dados de Demanda/DRE/ERE..."):
            df_demanda_temp = processar_dados_demanda(kW_kwinj_dre_ere)
            st.session_state.df_demanda_original = df_demanda_temp
            st.session_state.df_demanda_filtrado = df_demanda_temp # Inicializa o filtrado como o original
    else:
        st.session_state.df_demanda_original = None
        st.session_state.df_demanda_filtrado = None
    
    if st.session_state.get('df_consumo') is not None or st.session_state.get('df_demanda_original') is not None:
        st.session_state.dados_processados = True
    else:
        st.session_state.dados_processados = False
        if consumo_injecao:
            st.error("Não foi possível encontrar dados de consumo/injeção válidos.")
        if kW_kwinj_dre_ere:
            st.error("Não foi possível encontrar dados de demanda/DRE/ERE válidos.")
        if not consumo_injecao and not kW_kwinj_dre_ere:
            st.warning("Por favor, cole o conteúdo em um ou ambos os campos de texto.")

# --- Interface de Filtragem e Exibição de Resultados ---
if st.session_state.get('dados_processados', False):
    
    # --- NOVA SEÇÃO: Ferramenta para suprimir picos ---
    if st.session_state.get('df_demanda_original') is not None and 'kW fornecido' in st.session_state.df_demanda_original.columns:
        with st.expander("✔️ Ferramenta para Suprimir Picos de Demanda", expanded=False):
            df_original = st.session_state.df_demanda_original.dropna(subset=['kW fornecido'])
            
            # Evita erro se a coluna estiver vazia após dropar NaNs
            if not df_original.empty:
                min_val = float(df_original['kW fornecido'].min())
                max_val = float(df_original['kW fornecido'].max())

                st.info("Use o slider abaixo para selecionar o intervalo de 'kW fornecido' que deseja **MANTER**.")

                # Verifica se min e max são diferentes para evitar erro no slider
                if min_val < max_val:
                    selected_range = st.slider(
                        "Selecione o intervalo de demanda (kW fornecido):",
                        min_value=min_val,
                        max_value=max_val,
                        value=(min_val, max_val), # Default é o intervalo completo
                        key="demanda_range_slider"
                    )
                    
                    # Filtra o DataFrame original com base no intervalo selecionado
                    st.session_state.df_demanda_filtrado = df_original[
                        (df_original['kW fornecido'] >= selected_range[0]) & 
                        (df_original['kW fornecido'] <= selected_range[1])
                    ]
                else:
                    # Se todos os valores forem iguais, apenas exibe a informação e não filtra
                    st.write(f"Todos os valores de demanda são iguais a {min_val:.4f}. Nenhum filtro aplicado.")
                    st.session_state.df_demanda_filtrado = df_original
            else:
                # Caso o dataframe fique vazio
                st.warning("Não há dados de 'kW fornecido' para filtrar.")
                st.session_state.df_demanda_filtrado = df_original

    # Recalcula os resultados com base nos DataFrames (potencialmente filtrados)
    resultados_consumo = recalcular_resultados(st.session_state.get('df_consumo'), tipo_calculo='consumo')
    resultados_demanda = recalcular_resultados(st.session_state.get('df_demanda_filtrado'), tipo_calculo='demanda')

    # --- Lógica para criar a tabela de resultados (adaptada) ---
    table_data = []
    postos = ['Ponta', 'Reservado', 'Fora Ponta']
    
    perdas_multiplier = 1.025 if perdas_opcao == "Sim" else 1.0
    perdas_display_value = 2.5 if perdas_opcao == "Sim" else 0.0

    constante_kw = constante
    if tipo_opcao == "Grandeza EAC":
        constante_kw = constante / 4
    elif tipo_opcao == "Pulso":
        constante_kw = constante * 4
    constante_outros = constante

    def create_separator(label):
        return {'Posto Horário': f"--- {label} ---", 'Valor': '', 'K': '', 'Perdas (%)': '', 'Valor Final': ''}

    def add_demanda_section(key, label, k_value_to_use):
        if resultados_demanda and key in resultados_demanda:
            table_data.append(create_separator(f"{label}"))
            dados = resultados_demanda[key]
            for posto in postos:
                valor = dados['valores'].get(posto, 0.0)
                table_data.append({
                    'Posto Horário': posto,
                    'Valor': valor,
                    'K': k_value_to_use,
                    'Perdas (%)': perdas_display_value,
                    'Valor Final': valor * k_value_to_use * perdas_multiplier
                })

    if resultados_consumo:
        consumo_cols = list(resultados_consumo.keys())
        if consumo_cols:
            primeira_col_consumo = consumo_cols[0]
            dados = resultados_consumo[primeira_col_consumo]
            table_data.append(create_separator(f"{primeira_col_consumo} acumulado"))
            for posto in postos:
                valor = dados['valores'].get(posto, 0.0)
                table_data.append({
                    'Posto Horário': posto,
                    'Valor': valor,
                    'K': constante_outros,
                    'Perdas (%)': perdas_display_value,
                    'Valor Final': valor * constante_outros * perdas_multiplier
                })

    add_demanda_section('kW fornecido', 'kW fornecido máximo', constante_kw)
    add_demanda_section('UFER', 'UFER (ERE) acumulado', constante_outros)
    add_demanda_section('DMCR', 'DMCR (DRE) máximo', constante_outros)

    if resultados_consumo and len(resultados_consumo) > 1:
        outras_cols_consumo = list(resultados_consumo.keys())[1:]
        for col_name in outras_cols_consumo:
            dados = resultados_consumo[col_name]
            if any(v > 0 for v in dados['valores'].values()):
                table_data.append(create_separator(f"{col_name} acumulado"))
                for posto in postos:
                    valor = dados['valores'].get(posto, 0.0)
                    table_data.append({
                        'Posto Horário': posto,
                        'Valor': valor,
                        'K': constante_outros,
                        'Perdas (%)': perdas_display_value,
                        'Valor Final': valor * constante_outros * perdas_multiplier
                    })

    add_demanda_section('kW recebido', 'kW recebido máximo', constante_kw)

    # --- Chama o diálogo se houver resultados ---
    if table_data:
        df_resultados = pd.DataFrame(table_data)
        
        def format_br(value, precision):
            if isinstance(value, (int, float)):
                return f"{value:,.{precision}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            return value

        df_resultados['Valor'] = df_resultados['Valor'].apply(lambda x: format_br(x, 4) if isinstance(x, (int, float)) else x)
        df_resultados['K'] = df_resultados['K'].apply(lambda x: format_br(x, 4) if isinstance(x, (int, float)) else x)
        df_resultados['Perdas (%)'] = df_resultados['Perdas (%)'].apply(lambda x: format_br(x, 1) if isinstance(x, (int, float)) else x)
        df_resultados['Valor Final'] = df_resultados['Valor Final'].apply(lambda x: format_br(x, 4) if isinstance(x, (int, float)) else x)
        
        # O diálogo agora usa os dataframes do st.session_state
        show_results_dialog(df_resultados, st.session_state.get('df_consumo'), st.session_state.get('df_demanda_filtrado'))
