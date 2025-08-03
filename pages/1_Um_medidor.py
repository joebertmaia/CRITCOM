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
        'About': "Versão 1.0.0. Bugs ou sugestões, enviar um e-mail para joebert.oliveira@energisa.com.br"}
)

# --- FUNÇÕES DE PROCESSAMENTO (NÃO MODIFICAR) ---

def processar_dados_consumo(texto_bruto):
    """
    Processa o texto bruto colado pelo usuário para extrair, limpar e somar os dados de consumo.
    Esta versão lê o cabeçalho e retorna tanto os resultados agregados quanto o DataFrame bruto.
    """
    header_match = re.search(r"^Data\s+Dia\s+Postos horários\s+(.*)$", texto_bruto, re.MULTILINE)
    if not header_match:
        return None, None
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
        return None, None
    colunas_df = ['DataHora', 'Dia', 'Posto Horario'] + colunas_dados
    df = pd.DataFrame(dados_encontrados, columns=colunas_df)
    df['DataHora'] = pd.to_datetime(df['DataHora'], format='%d/%m/%Y %H:%M') # Converte para datetime
    resultados = {}
    for nome_coluna in colunas_dados:
        df[nome_coluna] = pd.to_numeric(
            df[nome_coluna].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
            errors='coerce'
        )
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
    return resultados, df

def processar_dados_demanda(texto_bruto):
    """
    Processa dados de demanda, identificando cabeçalhos e aplicando a lógica correta
    (soma ou máximo) para cada coluna de dados.
    """
    header_match = re.search(r"^Data\s+Dia\s+Postos horários\s+(.*)$", texto_bruto, re.MULTILINE)
    if not header_match:
        return None, None
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
        return None, None
    colunas_df = ['DataHora', 'Dia', 'Posto Horario'] + colunas_dados
    df = pd.DataFrame(dados_encontrados, columns=colunas_df)
    df['DataHora'] = pd.to_datetime(df['DataHora'], format='%d/%m/%Y %H:%M') # Converte para datetime
    resultados = {}
    for nome_coluna in colunas_dados:
        df[nome_coluna] = pd.to_numeric(
            df[nome_coluna].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
            errors='coerce'
        )
        if nome_coluna.strip().upper() == "UFER":
            operacao = 'soma'
            calculo = df.groupby('Posto Horario')[nome_coluna].sum()
        else:
            operacao = 'máximo'
            calculo = df.groupby('Posto Horario')[nome_coluna].max()
        resultados[nome_coluna] = {
            'operacao': operacao,
            'valores': {
                'Fora Ponta': calculo.get('Fora Ponta', 0.0),
                'Ponta': calculo.get('Ponta', 0.0),
                'Reservado': calculo.get('Reservado', 0.0)
            }
        }
        resultados[nome_coluna]['valores'] = {k: (v if pd.notna(v) else 0.0) for k, v in resultados[nome_coluna]['valores'].items()}
    return resultados, df

# --- NOVA FUNÇÃO PARA EXTRAIR INFORMAÇÕES DO CLIENTE ---
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
    
    table_html = df_resultados.to_html(index=False, escape=False, na_rep='')
    
    # Prepara dados para os gráficos de consumo
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

    # Prepara dados para os gráficos de demanda
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

    # Cria o componente HTML com a tabela, os gráficos e a função de cópia
    components.html(f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom/dist/chartjs-plugin-zoom.min.js"></script>

        <style>
            .capture-area {{ padding: 10px; background-color: #ffffff; }}
            table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #e0e0e0; padding: 8px; text-align: left; }}
            th {{ background-color: #f0f2f6; }}
            .button-container {{ text-align: right; margin-top: 10px; margin-bottom: 20px; }}
            .copy-button {{ background-color: #0068c9; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer; }}
            .copy-button:hover {{ background-color: #0055a3; }}
            h3 {{ font-family: sans-serif; }}
        </style>
        
        <div id="captureTable" class="capture-area">
            <h3>Tabela de Resultados</h3>
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
    """, height=800, scrolling=True)

    if st.button("Fechar", key="close_dialog"):
        st.rerun()

# --- Interface do Aplicativo ---
st.title("Confirmação para 1 medidor")

dados1, dados2 = st.columns(2)
with dados1:
    consumo_injecao = st.text_area(
        "Dê um Ctrl-A na página de consumo/injeção e cole aqui:",
        height=300,
        placeholder="Cole o texto aqui...",
        key="consumo_injecao"
    )
with dados2:
    kW_kwinj_dre_ere = st.text_area(
        "Dê um Ctrl-A na página de demanda/DRE/ERE e cole aqui:",
        height=300,
        placeholder="Cole o texto aqui...",
        key="kW_kwinj_dre_ere"
    )

# --- Seção de Informações do Cliente ---
info_consumo = extrair_info_cliente(consumo_injecao)
info_demanda = extrair_info_cliente(kW_kwinj_dre_ere)

if consumo_injecao or kW_kwinj_dre_ere:
    st.markdown("---")
    st.subheader("Informações de Medição Extraídas")
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("<h6>Consumo / Injeção</h6>", unsafe_allow_html=True)
        st.text(f"Contrato: {info_consumo['contrato']}")
        st.text(f"Serial: {info_consumo['serial']}")
    with col_info2:
        st.markdown("<h6>Demanda / DRE / ERE</h6>", unsafe_allow_html=True)
        st.text(f"Contrato: {info_demanda['contrato']}")
        st.text(f"Serial: {info_demanda['serial']}")

    if consumo_injecao and kW_kwinj_dre_ere:
        if info_consumo['contrato'] != "Não encontrado" and info_demanda['contrato'] != "Não encontrado" and info_consumo['contrato'] != info_demanda['contrato']:
            st.warning(f"Atenção: O número do contrato é diferente entre os dois relatórios ({info_consumo['contrato']} vs {info_demanda['contrato']}).")
        if info_consumo['serial'] != "Não encontrado" and info_demanda['serial'] != "Não encontrado" and info_consumo['serial'] != info_demanda['serial']:
            st.warning(f"Atenção: O número de série do medidor é diferente entre os dois relatórios ({info_consumo['serial']} vs {info_demanda['serial']}).")

st.markdown("---")

# --- Seção de Parâmetros de Cálculo ---
st.header("Parâmetros de Cálculo")
col_const, col_tipo, col_perdas = st.columns(3)

with col_const:
    constante = st.number_input(
        "Constante de faturamento:",
        min_value=0.0,
        value=1.0,
        step=0.01,
        format="%.4f"
    )
with col_tipo:
    tipo_opcao = st.radio(
        "Tipo:",
        ("Grandeza", "Grandeza EAC", "Pulso"),
        horizontal=True,
        key="tipo"
    )
with col_perdas:
    perdas_opcao = st.radio(
        "Adicionar Perdas?",
        ("Não", "Sim"),
        horizontal=True,
        key="perdas"
    )

# --- Botão e Lógica de Processamento ---
if st.button("Calcular Totais"):
    resultados_consumo, df_consumo = None, None
    resultados_demanda, df_demanda = None, None
    
    if consumo_injecao:
        with st.spinner("Processando dados de Consumo/Injeção..."):
            resultados_consumo, df_consumo = processar_dados_consumo(consumo_injecao)
            
    if kW_kwinj_dre_ere:
        with st.spinner("Processando dados de Demanda/DRE/ERE..."):
            resultados_demanda, df_demanda = processar_dados_demanda(kW_kwinj_dre_ere)

    # --- Lógica para criar a tabela de resultados ---
    table_data = []
    postos = ['Ponta', 'Fora Ponta', 'Reservado']
    
    perdas_multiplier = 1.025 if perdas_opcao == "Sim" else 1.0
    perdas_display_value = 2.5 if perdas_opcao == "Sim" else 0.0

    constante_kw = constante
    if tipo_opcao == "Grandeza EAC":
        constante_kw = constante / 4
    elif tipo_opcao == "Pulso":
        constante_kw = constante * 4
    constante_outros = constante

    def create_separator(label):
        return {'Descrição': f"--- {label} ---", 'Valor Calculado': '', 'K': '', 'Perdas (%)': '', 'Valor Final': ''}

    def add_demanda_section(key, label, k_value_to_use):
        if resultados_demanda and key in resultados_demanda:
            table_data.append(create_separator(f"{label}"))
            dados = resultados_demanda[key]
            for posto in postos:
                valor = dados['valores'].get(posto, 0.0)
                table_data.append({
                    'Descrição': posto,
                    'Valor Calculado': valor,
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
                    'Descrição': posto,
                    'Valor Calculado': valor,
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
                        'Descrição': posto,
                        'Valor Calculado': valor,
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

        df_resultados['Valor Calculado'] = df_resultados['Valor Calculado'].apply(lambda x: format_br(x, 4) if isinstance(x, (int, float)) else x)
        df_resultados['K'] = df_resultados['K'].apply(lambda x: format_br(x, 4) if isinstance(x, (int, float)) else x)
        df_resultados['Perdas (%)'] = df_resultados['Perdas (%)'].apply(lambda x: format_br(x, 1) if isinstance(x, (int, float)) else x)
        df_resultados['Valor Final'] = df_resultados['Valor Final'].apply(lambda x: format_br(x, 4) if isinstance(x, (int, float)) else x)
        
        show_results_dialog(df_resultados, df_consumo, df_demanda)
        
    elif consumo_injecao and not resultados_consumo:
        st.error("Não foi possível encontrar dados de consumo/injeção válidos no primeiro campo.")
    elif kW_kwinj_dre_ere and not resultados_demanda:
        st.error("Não foi possível encontrar dados de demanda/DRE/ERE válidos no segundo campo.")
    elif not consumo_injecao and not kW_kwinj_dre_ere:
        st.warning("Por favor, cole o conteúdo em um ou ambos os campos de texto antes de calcular.")

footer="""<style>

.footer {
position: absolute;
top:230px;
left: 0;
bottom: 0px;
width: 100%;
background-color: transparent;
color: filter: invert(1); black;
text-align: center;
}
</style>
<div class="footer">
<hr style='width:70%;text-align:center;margin:auto'>
<p>Centro de Operação da Medição (COM)<br>Grupo Energisa</p>
</div>
"""
st.markdown(footer,unsafe_allow_html=True)