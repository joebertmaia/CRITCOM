import streamlit as st
import pandas as pd
import re
from io import StringIO
import streamlit.components.v1 as components
import json

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dois medidores",
    page_icon="https://www.energisa.com.br/sites/energisa/files/Energisa120%20%281%29.ico",
    layout="wide",
    menu_items={
        'About': "Versão 1.0.0. Bugs ou sugestões, enviar um e-mail para joebert.oliveira@energisa.com.br"}
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
@st.dialog("Resultados do Cálculo")
def show_results_dialog(df_resultados, df_consumo_antigo, df_demanda_antigo, df_consumo_novo, df_demanda_novo, contrato, serial_antigo, serial_novo):
    """Exibe o DataFrame de resultados e gráficos dentro de um diálogo."""
    
    # --- Geração Manual da Tabela HTML ---
    title_html = f"<h3>Resultados para o Contrato: {contrato}</h3>"
    header_html = "<thead>"
    header_html += f'<tr><th rowspan="2">Posto Horário</th><th colspan="4" style="text-align: center;">Medidor Anterior ({serial_antigo})</th><th colspan="4" style="text-align: center;">Medidor Novo ({serial_novo})</th><th rowspan="2">Sumarização</th></tr>'
    header_html += "<tr>"
    col_names = ['Valor', 'K', 'Perdas (%)', 'Valor Final']
    header_html += "".join(f'<th>{name}</th>' for name in col_names)
    header_html += "".join(f'<th>{name}</th>' for name in col_names)
    header_html += "</tr></thead>"

    body_html = "<tbody>"
    for _, row in df_resultados.iterrows():
        if str(row.iloc[0]).startswith('---'):
            body_html += f'<tr class="separator-row"><td colspan="{len(df_resultados.columns)}">{row.iloc[0]}</td></tr>'
        else:
            body_html += "<tr>"
            for i, cell_value in enumerate(row):
                class_attr = ""
                if i == 4 or i == 8:
                    class_attr = ' class="thick-border-right"'
                body_html += f'<td{class_attr}>{cell_value}</td>'
            body_html += "</tr>"
    body_html += "</tbody>"

    table_html = f"<table>{header_html}{body_html}</table>"
    
    # Prepara dados para os gráficos
    def get_chart_data(df_raw, column_name):
        if df_raw is not None and column_name in df_raw.columns:
            df_filtered = df_raw[['DataHora', column_name]].dropna()
            df_filtered['DataHora'] = df_filtered['DataHora'].apply(lambda x: x.isoformat())
            return df_filtered.to_dict(orient='records')
        return None

    chart_data = {
        'consumo_fornecido_antigo': get_chart_data(df_consumo_antigo, 'kWh fornecido'),
        'consumo_recebido_antigo': get_chart_data(df_consumo_antigo, 'kWh recebido'),
        'demanda_fornecido_antigo': get_chart_data(df_demanda_antigo, 'kW fornecido'),
        'demanda_recebido_antigo': get_chart_data(df_demanda_antigo, 'kW recebido'),
        'dmcr_antigo': get_chart_data(df_demanda_antigo, 'DMCR'),
        'ufer_antigo': get_chart_data(df_demanda_antigo, 'UFER'),
        'consumo_fornecido_novo': get_chart_data(df_consumo_novo, 'kWh fornecido'),
        'consumo_recebido_novo': get_chart_data(df_consumo_novo, 'kWh recebido'),
        'demanda_fornecido_novo': get_chart_data(df_demanda_novo, 'kW fornecido'),
        'demanda_recebido_novo': get_chart_data(df_demanda_novo, 'kW recebido'),
        'dmcr_novo': get_chart_data(df_demanda_novo, 'DMCR'),
        'ufer_novo': get_chart_data(df_demanda_novo, 'UFER'),
    }

    components.html(f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom/dist/chartjs-plugin-zoom.min.js"></script>

        <style>
            .capture-area {{ padding: 10px; background-color: #ffffff; }}
            table {{ width: 600px; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #e0e0e0; padding: 8px; text-align: center; }} /* Centralizado */
            th {{ background-color: #f0f2f6; }}
            .button-container {{ text-align: right; margin-top: 10px; margin-bottom: 20px; }}
            .copy-button {{ background-color: #0068c9; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer; }}
            .copy-button:hover {{ background-color: #0055a3; }}
            h3 {{ font-family: sans-serif; text-align: center;}}
            
            /* Estilos para a tabela */
            th.thick-border-right, td.thick-border-right {{
                border-right: 2px solid #888;
            }}
            tr.separator-row td {{
                text-align: center;
                font-weight: bold;
                background-color: #e8e8e8;
                border-left: 1px solid #e0e0e0;
                border-right: 1px solid #e0e0e0;
            }}
        </style>
        
        <div id="captureTable" class="capture-area">
            {title_html}
            {table_html}
        </div>
        <div class="button-container">
            <button class="copy-button" onclick="copyElementAsImage('captureTable', this)">Copiar Tabela como Imagem</button>
        </div>

        <div id="consumoChartContainerAnterior"></div>
        <div id="demandaChartContainerAnterior"></div>
        <div id="consumoChartContainerNovo"></div>
        <div id="demandaChartContainerNovo"></div>

        <script>
            const chartData = {json.dumps(chart_data)};
            
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
                    type: 'line', data: {{ datasets: datasets }},
                    options: {{ responsive: true, maintainAspectRatio: true, plugins: {{ zoom: {{ zoom: {{ wheel: {{ enabled: true }}, pinch: {{ enabled: true }}, mode: 'x' }} }} }}, scales: {{ x: {{ type: 'time', time: {{ unit: 'day' }} }} }} }}
                }});
            }}

            // Cria gráficos
            const consumoDatasetsAnterior = [];
            if (chartData.consumo_fornecido_antigo) consumoDatasetsAnterior.push({{ label: 'kWh fornecido', data: chartData.consumo_fornecido_antigo.map(item => ({{x: new Date(item.DataHora), y: item['kWh fornecido']}})), borderColor: 'rgb(75, 192, 192)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.consumo_recebido_antigo) consumoDatasetsAnterior.push({{ label: 'kWh recebido', data: chartData.consumo_recebido_antigo.map(item => ({{x: new Date(item.DataHora), y: item['kWh recebido']}})), borderColor: 'rgb(255, 99, 132)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            createChart('consumoChartContainerAnterior', 'consumoChartAnterior', 'Gráfico - Consumo (Medidor Anterior)', consumoDatasetsAnterior);

            const demandaDatasetsAnterior = [];
            if (chartData.demanda_fornecido_antigo) demandaDatasetsAnterior.push({{ label: 'kW fornecido', data: chartData.demanda_fornecido_antigo.map(item => ({{x: new Date(item.DataHora), y: item['kW fornecido']}})), borderColor: 'rgb(54, 162, 235)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.demanda_recebido_antigo) demandaDatasetsAnterior.push({{ label: 'kW recebido', data: chartData.demanda_recebido_antigo.map(item => ({{x: new Date(item.DataHora), y: item['kW recebido']}})), borderColor: 'rgb(255, 159, 64)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.dmcr_antigo) demandaDatasetsAnterior.push({{ label: 'DMCR', data: chartData.dmcr_antigo.map(item => ({{x: new Date(item.DataHora), y: item['DMCR']}})), borderColor: 'rgb(153, 102, 255)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.ufer_antigo) demandaDatasetsAnterior.push({{ label: 'UFER', data: chartData.ufer_antigo.map(item => ({{x: new Date(item.DataHora), y: item['UFER']}})), borderColor: 'rgb(75, 192, 75)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            createChart('demandaChartContainerAnterior', 'demandaChartAnterior', 'Gráfico - Demanda (Medidor Anterior)', demandaDatasetsAnterior);

            const consumoDatasetsNovo = [];
            if (chartData.consumo_fornecido_novo) consumoDatasetsNovo.push({{ label: 'kWh fornecido', data: chartData.consumo_fornecido_novo.map(item => ({{x: new Date(item.DataHora), y: item['kWh fornecido']}})), borderColor: 'rgb(75, 192, 192)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.consumo_recebido_novo) consumoDatasetsNovo.push({{ label: 'kWh recebido', data: chartData.consumo_recebido_novo.map(item => ({{x: new Date(item.DataHora), y: item['kWh recebido']}})), borderColor: 'rgb(255, 99, 132)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            createChart('consumoChartContainerNovo', 'consumoChartNovo', 'Gráfico - Consumo (Medidor Novo)', consumoDatasetsNovo);

            const demandaDatasetsNovo = [];
            if (chartData.demanda_fornecido_novo) demandaDatasetsNovo.push({{ label: 'kW fornecido', data: chartData.demanda_fornecido_novo.map(item => ({{x: new Date(item.DataHora), y: item['kW fornecido']}})), borderColor: 'rgb(54, 162, 235)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.demanda_recebido_novo) demandaDatasetsNovo.push({{ label: 'kW recebido', data: chartData.demanda_recebido_novo.map(item => ({{x: new Date(item.DataHora), y: item['kW recebido']}})), borderColor: 'rgb(255, 159, 64)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.dmcr_novo) demandaDatasetsNovo.push({{ label: 'DMCR', data: chartData.dmcr_novo.map(item => ({{x: new Date(item.DataHora), y: item['DMCR']}})), borderColor: 'rgb(153, 102, 255)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            if (chartData.ufer_novo) demandaDatasetsNovo.push({{ label: 'UFER', data: chartData.ufer_novo.map(item => ({{x: new Date(item.DataHora), y: item['UFER']}})), borderColor: 'rgb(75, 192, 75)', tension: 0.1, pointRadius: 0, borderWidth: 2 }});
            createChart('demandaChartContainerNovo', 'demandaChartNovo', 'Gráfico - Demanda (Medidor Novo)', demandaDatasetsNovo);

            function copyChartAsImage(chartInstanceVar, button) {{
                const chartInstance = window[chartInstanceVar];
                if (!chartInstance) return;
                const originalText = button.innerText;
                button.innerText = 'Copiando...';

                const tempCanvas = document.createElement('canvas');
                tempCanvas.width = 2000;
                tempCanvas.height = 1250;
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
                            legend: {{ labels: {{ font: {{ size: 24 }} }} }}
                        }},
                        scales: {{
                            ...chartInstance.config.options.scales,
                            x: {{ ...chartInstance.config.options.scales.x, min: chartInstance.scales.x.min, max: chartInstance.scales.x.max, ticks: {{ font: {{ size: 20 }} }} }},
                            y: {{ ...chartInstance.config.options.scales.y, ticks: {{ font: {{ size: 20 }} }} }}
                        }}
                    }},
                    plugins: [whiteBackgroundPlugin]
                }};

                new Chart(tempCtx, tempConfig);

                setTimeout(() => {{
                    tempCanvas.toBlob(function(blob) {{
                        navigator.clipboard.write([ new ClipboardItem({{ 'image/png': blob }}) ])
                        .then(() => {{ button.innerText = 'Copiado!'; setTimeout(() => {{ button.innerText = originalText; }}, 2000); }})
                        .catch(err => {{ console.error('Erro: ', err); button.innerText = 'Falha'; setTimeout(() => {{ button.innerText = originalText; }}, 2000); }});
                    }});
                }}, 250);
            }}

            function copyElementAsImage(elementId, button) {{
                const captureElement = document.getElementById(elementId);
                const originalText = button.innerText;
                button.innerText = 'Copiando...';

                html2canvas(captureElement, {{ scale: 1.5 }}).then(canvas => {{
                    canvas.toBlob(function(blob) {{
                        navigator.clipboard.write([ new ClipboardItem({{ 'image/png': blob }}) ])
                        .then(() => {{ button.innerText = 'Copiado!'; setTimeout(() => {{ button.innerText = originalText; }}, 2000); }})
                        .catch(err => {{ console.error('Erro: ', err); button.innerText = 'Falha'; setTimeout(() => {{ button.innerText = originalText; }}, 2000); }});
                    }});
                }});
            }}
        </script>
    """, width=800, height=700, scrolling=True)

    if st.button("Fechar", key="close_dialog"):
        st.rerun()

# --- Interface do Aplicativo ---
st.title("Confirmação para 2 MDs")
st.markdown("""<style>[aria-label="dialog"]{width: 850px;}</style>""", unsafe_allow_html=True)
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

# --- Seção de Parâmetros de Cálculo ---
param1, param2 = st.columns(2)
with param1:
    st.subheader("Medidor Anterior")
    constante_antigo = st.number_input("Constante:", min_value=0.0, value=1.0, step=0.01, format="%.4f", key="const_antigo")
    colum1, colum2 = st.columns(2)
    with colum1:
        tipo_opcao_antigo = st.radio("Tipo:", ("Grandeza", "Grandeza EAC", "Pulso"), horizontal=False, key="tipo_antigo", captions=["","Comum em medidores SL7000 da EAC.", "Maioria dos pontos da ERO."])
    with colum2:
        perdas_opcao_antigo = st.radio("Perdas? :warning: **Não adicionar quando digitar no SILCO** :warning:", ("Não", "Sim"), horizontal=True, key="perdas_antigo", captions=["Se o cliente possuir TP e TC.","Para medições diretas ou em baixa tensão (apenas TC)."])
with param2:
    st.subheader("Medidor Novo")
    constante_novo = st.number_input("Constante:", min_value=0.0, value=1.0, step=0.01, format="%.4f", key="const_novo")
    colum1, colum2 = st.columns(2)
    with colum1:
        tipo_opcao_novo = st.radio("Tipo:", ("Grandeza", "Grandeza EAC", "Pulso"), horizontal=False, key="tipo_novo", captions=["","Comum em medidores SL7000 da EAC.", "Maioria dos pontos da ERO."])
    with colum2:
        perdas_opcao_novo = st.radio("Perdas? :warning: **Não adicionar quando digitar no SILCO** :warning:", ("Não", "Sim"), horizontal=True, key="perdas_novo", captions=["Se o cliente possuir TP e TC.","Para medições diretas ou em baixa tensão (apenas TC)."])

# --- Botões de Ação ---
st.markdown("")
col_btn1, col_btn2, _ = st.columns([1, 1, 4]) # Cria colunas para os botões

with col_btn1:
    calculate_button = st.button("CALCULAR")

with col_btn2:
    def clear_all_text():
        st.session_state.consumo_antigo = ""
        st.session_state.demanda_antigo = ""
        st.session_state.consumo_novo = ""
        st.session_state.demanda_novo = ""
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

# Placeholder para mensagens de aviso/erro
message_placeholder = st.empty()

with st.sidebar:
    # --- Seção de Inserção de Dados ---
    st.subheader("Medidor Anterior")
    col1, col2 = st.columns(2)
    with col1:
        consumo_antigo = st.text_area("kWh/kWh Inj:", height=150, placeholder="Dê um Ctrl+A no relatório de consumo, Ctrl+C e cole aqui.", key="consumo_antigo")
    with col2:
        demanda_antigo = st.text_area("kW/DRE/ERE:", height=150, placeholder="Dê um Ctrl+A no relatório de demanda, Ctrl+C e cole aqui.", key="demanda_antigo")

    st.subheader("Medidor Novo")
    col3, col4 = st.columns(2)
    with col3:
        consumo_novo = st.text_area("kWh/kWh Inj:", height=150, placeholder="Dê um Ctrl+A no relatório de consumo, Ctrl+C e cole aqui.", key="consumo_novo")
    with col4:
        demanda_novo = st.text_area("kW/DRE/ERE:", height=150, placeholder="Dê um Ctrl+A no relatório de demanda, Ctrl+C e cole aqui.", key="demanda_novo")

# --- Seção de Informações do Cliente ---
info_consumo_antigo = extrair_info_cliente(consumo_antigo)
info_demanda_antigo = extrair_info_cliente(demanda_antigo)
info_consumo_novo = extrair_info_cliente(consumo_novo)
info_demanda_novo = extrair_info_cliente(demanda_novo)

warnings_list = []

if consumo_antigo or demanda_antigo:
    if consumo_antigo:
        if re.search(r"Postos horários\s+Cadastro de opção tarifária", consumo_antigo):
            warnings_list.append(":warning: Atenção: Medidor anterior está com postos horários via 'Cadastro de opção tarifária'. Verifique se os postos estão corretos.")
        if re.search(r"Postos horários\s+Cadastro de opção tarifária", demanda_antigo):
            warnings_list.append(":warning: Atenção: Medidor anterior está com postos horários via 'Cadastro de opção tarifária'. Verifique se os postos estão corretos.")

if any([consumo_antigo, demanda_antigo, consumo_novo, demanda_novo]):
    st.markdown("---")
    st.subheader("Informações de Medição Extraídas")
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.markdown("<h6>Medidor Anterior</h6>", unsafe_allow_html=True)
        st.text(f"Contrato: {info_consumo_antigo['contrato']} (Consumo) / {info_demanda_antigo['contrato']} (Demanda)")
        st.text(f"Serial: {info_consumo_antigo['serial']} (Consumo) / {info_demanda_antigo['serial']} (Demanda)")
        if consumo_antigo and demanda_antigo:
            if info_consumo_antigo['contrato'] != "Não encontrado" and info_demanda_antigo['contrato'] != "Não encontrado" and info_consumo_antigo['contrato'] != info_demanda_antigo['contrato']:
                warnings_list.append(":x: Atenção: Contratos do medidor antigo são diferentes.")
            if info_consumo_antigo['serial'] != "Não encontrado" and info_demanda_antigo['serial'] != "Não encontrado" and info_consumo_antigo['serial'] != info_demanda_antigo['serial']:
                warnings_list.append(":x: Atenção: Seriais do medidor antigo são diferentes.")
    with col_info2:
        st.markdown("<h6>Medidor Novo</h6>", unsafe_allow_html=True)
        st.text(f"Contrato: {info_consumo_novo['contrato']} (Consumo) / {info_demanda_novo['contrato']} (Demanda)")
        st.text(f"Serial: {info_consumo_novo['serial']} (Consumo) / {info_demanda_novo['serial']} (Demanda)")
        if consumo_novo and demanda_novo:
            if info_consumo_novo['contrato'] != "Não encontrado" and info_demanda_novo['contrato'] != "Não encontrado" and info_consumo_novo['contrato'] != info_demanda_novo['contrato']:
                warnings_list.append(":x: Atenção: Contratos do medidor novo são diferentes.")
            if info_consumo_novo['serial'] != "Não encontrado" and info_demanda_novo['serial'] != "Não encontrado" and info_consumo_novo['serial'] != info_demanda_novo['serial']:
                warnings_list.append(":x: Atenção: Seriais do medidor novo são diferentes.")

    # Adiciona a verificação entre medidores
    contrato_antigo_final = info_consumo_antigo['contrato'] if info_consumo_antigo['contrato'] != "Não encontrado" else info_demanda_antigo['contrato']
    contrato_novo_final = info_consumo_novo['contrato'] if info_consumo_novo['contrato'] != "Não encontrado" else info_demanda_novo['contrato']

    if contrato_antigo_final != "Não encontrado" and contrato_novo_final != "Não encontrado" and contrato_antigo_final != contrato_novo_final:
        warnings_list.append(":x: Atenção: Contratos do medidor antigo e novo são diferentes.")

# --- Lógica de Cálculo ---
if calculate_button:
    res_con_antigo, df_con_antigo = processar_dados_consumo(consumo_antigo) if consumo_antigo else (None, None)
    res_dem_antigo, df_dem_antigo = processar_dados_demanda(demanda_antigo) if demanda_antigo else (None, None)
    res_con_novo, df_con_novo = processar_dados_consumo(consumo_novo) if consumo_novo else (None, None)
    res_dem_novo, df_dem_novo = processar_dados_demanda(demanda_novo) if demanda_novo else (None, None)
    
    table_data = []
    postos = ['Ponta', 'Reservado', 'Fora Ponta']
    
    grandezas_a_processar = [
        {'key': 'kWh fornecido', 'type': 'consumo', 'label': 'kWh fornecido acumulado'},
        {'key': 'kW fornecido', 'type': 'demanda', 'label': 'kW fornecido máximo'},
        {'key': 'UFER', 'type': 'demanda', 'label': 'UFER (ERE) acumulado'},
        {'key': 'DMCR', 'type': 'demanda', 'label': 'DMCR (DRE) máximo'},
        {'key': 'kWh recebido', 'type': 'consumo', 'label': 'kWh recebido acumulado'},
        {'key': 'kW recebido', 'type': 'demanda', 'label': 'kW recebido máximo'}
    ]

    def get_params(medidor_type, grandeza):
        if medidor_type == 'antigo':
            constante, tipo_opcao, perdas_opcao = constante_antigo, tipo_opcao_antigo, perdas_opcao_antigo
        else:
            constante, tipo_opcao, perdas_opcao = constante_novo, tipo_opcao_novo, perdas_opcao_novo
        
        perdas_multiplier = 1.025 if perdas_opcao == "Sim" else 1.0
        perdas_display = 2.5 if perdas_opcao == "Sim" else 0.0

        k_value = constante
        if grandeza.startswith("kW "):
            if tipo_opcao == "Grandeza EAC": k_value = constante / 4
            elif tipo_opcao == "Pulso": k_value = constante * 4
        
        return k_value, perdas_display, perdas_multiplier

    def get_sumarizacao(grandeza, val_antigo, val_novo):
        if grandeza.startswith("kW ") or grandeza == "DMCR":
            return max(val_antigo, val_novo)
        else:
            return val_antigo + val_novo

    for item in grandezas_a_processar:
        grandeza, tipo_dado, label = item['key'], item['type'], item['label']
        res_antigo = res_con_antigo if tipo_dado == 'consumo' else res_dem_antigo
        res_novo = res_con_novo if tipo_dado == 'consumo' else res_dem_novo
        existe_antigo = res_antigo and grandeza in res_antigo
        existe_novo = res_novo and grandeza in res_novo
        
        if existe_antigo or existe_novo:
            table_data.append({'Posto Horário': f"--- {label} ---"})
            for posto in postos:
                val_antigo = res_antigo[grandeza]['valores'].get(posto, 0.0) if existe_antigo else 0.0
                k_antigo, perdas_antigo_display, perdas_antigo_mult = get_params('antigo', grandeza)
                final_antigo = val_antigo * k_antigo * perdas_antigo_mult

                val_novo = res_novo[grandeza]['valores'].get(posto, 0.0) if existe_novo else 0.0
                k_novo, perdas_novo_display, perdas_novo_mult = get_params('novo', grandeza)
                final_novo = val_novo * k_novo * perdas_novo_mult
                
                sumarizacao = get_sumarizacao(grandeza, final_antigo, final_novo)

                table_data.append({
                    'Posto Horário': posto,
                    'Valor calculado (antigo)': val_antigo, 'K (antigo)': k_antigo, 'Perdas (%) (antigo)': perdas_antigo_display, 'Valor final (antigo)': final_antigo,
                    'Valor calculado (novo)': val_novo, 'K (novo)': k_novo, 'Perdas (%) (novo)': perdas_novo_display, 'Valor final (novo)': final_novo,
                    'Sumarização': sumarizacao
                })

    if table_data:
        df_resultados = pd.DataFrame(table_data)
        
        def format_br(value, precision):
            if pd.isna(value) or value == '': return ''
            if isinstance(value, (int, float)): return f"{{:,.{precision}f}}".format(value).replace(',', 'X').replace('.', ',').replace('X', '.')
            return value

        col_format = {
            'Valor calculado (antigo)': 4, 'K (antigo)': 4, 'Perdas (%) (antigo)': 1, 'Valor final (antigo)': 4,
            'Valor calculado (novo)': 4, 'K (novo)': 4, 'Perdas (%) (novo)': 1, 'Valor final (novo)': 4,
            'Sumarização': 4
        }
        for col, p in col_format.items():
            if col in df_resultados.columns:
                df_resultados[col] = df_resultados[col].apply(lambda x: format_br(x, p))
        
        contrato_final = contrato_novo_final if contrato_novo_final != "Não encontrado" else contrato_antigo_final
        serial_antigo_final = info_consumo_antigo['serial'] if info_consumo_antigo['serial'] != "Não encontrado" else info_demanda_antigo['serial']
        serial_novo_final = info_consumo_novo['serial'] if info_consumo_novo['serial'] != "Não encontrado" else info_demanda_novo['serial']

        show_results_dialog(df_resultados, df_con_antigo, df_dem_antigo, df_con_novo, df_dem_novo, contrato_final, serial_antigo_final, serial_novo_final)
        
    elif any([consumo_antigo, demanda_antigo, consumo_novo, demanda_novo]):
        message_placeholder.error("Não foi possível encontrar dados válidos nos textos informados. Verifique o conteúdo colado.")
    else:
        message_placeholder.warning("Por favor, cole o conteúdo em um ou ambos os campos de texto antes de calcular.")
else:
    # Mostra os avisos de contrato/serial se houver texto, mas o botão de calcular ainda não foi pressionado
    if warnings_list:
        message_placeholder.warning("\n\n".join(warnings_list))