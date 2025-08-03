import streamlit as st
import pandas as pd
import re
from io import StringIO
import streamlit.components.v1 as components

# --- Configuração da Página ---
st.set_page_config(
    page_title="Cálculo da MM",
    page_icon="💡",
    layout="wide"
)

# --- FUNÇÃO PARA CONSUMO (MODIFICADA) ---
def processar_dados_consumo(texto_bruto):
    """
    Processa o texto bruto colado pelo usuário para extrair, limpar e somar os dados de consumo.
    Esta versão lê o cabeçalho para identificar dinamicamente as colunas de dados.
    """
    # Encontra a linha do cabeçalho que começa com "Data" e captura o resto da linha
    header_match = re.search(r"^Data\s+Dia\s+Postos horários\s+(.*)$", texto_bruto, re.MULTILINE)
    if not header_match:
        return None

    # Pega os nomes das colunas de dados (ex: "kWh fornecido	kWh recebido")
    header_string = header_match.group(1).strip()
    # Divide o cabeçalho por TAB para lidar corretamente com nomes de colunas com espaços
    colunas_dados = [col.strip() for col in header_string.split('\t')]
    num_colunas_dados = len(colunas_dados)

    # Constrói um padrão regex dinâmico com base no número de colunas encontradas
    valor_pattern = r"([\d.,-]+)" # Captura números, vírgulas, pontos e hífens
    regex_parts = [
        r"^(\d{2}/\d{2}/\d{4}\s\d{2}:\d{2})", # Data e Hora
        r"([A-Za-zçáéíóúãõâêôü]+)",          # Dia da semana
        r"(Fora Ponta|Ponta|Reservado)"     # Posto Horário
    ]
    regex_parts.extend([valor_pattern] * num_colunas_dados)
    
    padrao_dados_str = r"\s+".join(regex_parts) + r"$"
    padrao_dados = re.compile(padrao_dados_str, re.MULTILINE)
    
    dados_encontrados = padrao_dados.findall(texto_bruto)
    if not dados_encontrados:
        return None

    # Monta a lista completa de colunas para o DataFrame
    colunas_df = ['DataHora', 'Dia', 'Posto Horario'] + colunas_dados
    df = pd.DataFrame(dados_encontrados, columns=colunas_df)

    # Dicionário para armazenar os resultados finais
    resultados = {}

    # Itera sobre cada coluna de dados encontrada para processá-la
    for nome_coluna in colunas_dados:
        # Converte a coluna para numérico, tratando erros e hífens
        df[nome_coluna] = pd.to_numeric(
            df[nome_coluna].str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
            errors='coerce' # Transforma valores inválidos (como '-') em NaN (Not a Number)
        )

        # Para consumo, a operação é sempre SOMA
        operacao = 'soma'
        calculo = df.groupby('Posto Horario')[nome_coluna].sum()
        
        # Armazena o resultado
        resultados[nome_coluna] = {
            'operacao': operacao,
            'valores': {
                'Fora Ponta': calculo.get('Fora Ponta', 0.0),
                'Ponta': calculo.get('Ponta', 0.0),
                'Reservado': calculo.get('Reservado', 0.0)
            }
        }
        # Preenche valores NaN (se todos os valores de um grupo forem inválidos) com 0
        resultados[nome_coluna]['valores'] = {k: (v if pd.notna(v) else 0.0) for k, v in resultados[nome_coluna]['valores'].items()}

    return resultados


# --- FUNÇÃO PARA DEMANDA (NÃO MODIFICAR) ---
def processar_dados_demanda(texto_bruto):
    """
    Processa dados de demanda, identificando cabeçalhos e aplicando a lógica correta
    (soma ou máximo) para cada coluna de dados.
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
    return resultados

# --- Função que define o conteúdo do diálogo ---
@st.dialog("Resultados do Cálculo", width='large')
def show_results_dialog(df_resultados):
    """Exibe o DataFrame de resultados dentro de um diálogo com a opção de copiar como imagem."""
    
    # Converte o DataFrame para uma tabela HTML
    table_html = df_resultados.to_html(index=False, escape=False, na_rep='')

    # Cria o componente HTML com a tabela, o script do html2canvas e a função de cópia
    components.html(f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            #captureArea {{
                padding: 10px;
                background-color: #ffffff; /* Fundo branco para a imagem */
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-family: sans-serif;
                font-size: 14px;
            }}
            th, td {{
                border: 1px solid #e0e0e0;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f0f2f6;
            }}
            .button-container {{
                text-align: right;
                margin-top: 15px;
            }}
            .copy-button {{
                background-color: #0068c9;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 5px;
                cursor: pointer;
            }}
            .copy-button:hover {{
                background-color: #0055a3;
            }}
        </style>
        
        <div id="captureArea">
            {table_html}
        </div>
        
        <div class="button-container">
            <button id="copyButton" class="copy-button" onclick="copyTableAsImage()">Copiar como Imagem</button>
        </div>

        <script>
            function copyTableAsImage() {{
                const captureElement = document.getElementById('captureArea');
                const button = document.getElementById('copyButton');
                button.innerText = 'Copiando...';

                html2canvas(captureElement, {{ scale: 2 }}).then(canvas => {{
                    canvas.toBlob(function(blob) {{
                        navigator.clipboard.write([
                            new ClipboardItem({{ 'image/png': blob }})
                        ]).then(function() {{
                            button.innerText = 'Copiado!';
                            setTimeout(() => {{ button.innerText = 'Copiar como Imagem'; }}, 2000);
                        }}).catch(function(err) {{
                            console.error('Erro ao copiar imagem: ', err);
                            button.innerText = 'Falha ao copiar';
                            setTimeout(() => {{ button.innerText = 'Copiar como Imagem'; }}, 2000);
                        }});
                    }});
                }});
            }}
        </script>
    """, height=600, scrolling=True)

    if st.button("Fechar", key="close_dialog"):
        st.rerun()

# --- Interface do Aplicativo ---
st.title("💡 Cálculo da MM")
st.markdown("Copie o conteúdo da página de consumo/demanda e cole no campo abaixo para calcular.")

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

st.markdown("---")

# --- Seção de Cálculos ---
st.header("Parâmetros de Cálculo")
col_const, col_perdas = st.columns(2)

with col_const:
    constante = st.number_input(
        "Constante de faturamento:",
        min_value=0,
        value=1,
        step=1,
        format="%i"
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
    resultados_consumo = None
    resultados_demanda = None
    
    if consumo_injecao:
        with st.spinner("Processando dados de Consumo/Injeção..."):
            resultados_consumo = processar_dados_consumo(consumo_injecao)
            
    if kW_kwinj_dre_ere:
        with st.spinner("Processando dados de Demanda/DRE/ERE..."):
            resultados_demanda = processar_dados_demanda(kW_kwinj_dre_ere)

    # --- Lógica para criar a tabela de resultados ---
    table_data = []
    postos = ['Ponta', 'Fora Ponta', 'Reservado']
    
    perdas_multiplier = 1.025 if perdas_opcao == "Sim" else 1.0
    perdas_display_value = 2.5 if perdas_opcao == "Sim" else 0.0

    def create_separator(label):
        return {'Descrição': f"--- {label} ---", 'Valor': '', 'K': '', 'Perdas (%)': '', 'Valor Final': ''}

    def add_demanda_section(key, label):
        if resultados_demanda and key in resultados_demanda:
            table_data.append(create_separator(f"{label}"))
            dados = resultados_demanda[key]
            for posto in postos:
                valor = dados['valores'].get(posto, 0.0)
                table_data.append({
                    'Descrição': posto,
                    'Valor': valor,
                    'K': constante,
                    'Perdas (%)': perdas_display_value,
                    'Valor Final': valor * constante * perdas_multiplier
                })

    # 1. Soma do Consumo (kWh) - agora iterativo para todas as colunas encontradas
    if resultados_consumo:
        consumo_cols = list(resultados_consumo.keys())
        
        # Adiciona a primeira coluna de consumo
        if len(consumo_cols) > 0:
            col_name = consumo_cols[0]
            dados = resultados_consumo[col_name]
            table_data.append(create_separator(f"{col_name} acumulado"))
            for posto in postos:
                valor = dados['valores'].get(posto, 0.0)
                table_data.append({
                    'Descrição': posto,
                    'Valor': valor,
                    'K': constante,
                    'Perdas (%)': perdas_display_value,
                    'Valor Final': valor * constante * perdas_multiplier
                })

    # 2. Máximo kW fornecido
    add_demanda_section('kW fornecido', 'kW fornecido máximo')
    
    # 3. Soma UFER
    add_demanda_section('UFER', 'UFER (ERE) acumulado')
    
    # 4. Máximo DMCR
    add_demanda_section('DMCR', 'DMCR (DRE) máximo')

    # 5. "Coluna 2" e outras colunas de consumo (se existirem)
    if resultados_consumo and len(resultados_consumo.keys()) > 1:
        outras_cols_consumo = list(resultados_consumo.keys())[1:]
        for col_name in outras_cols_consumo:
            dados = resultados_consumo[col_name]
            if any(v > 0 for v in dados['valores'].values()):
                table_data.append(create_separator(f"{col_name} acumulado"))
                for posto in postos:
                    valor = dados['valores'].get(posto, 0.0)
                    table_data.append({
                        'Descrição': posto,
                        'Valor': valor,
                        'K': constante,
                        'Perdas (%)': perdas_display_value,
                        'Valor Final': valor * constante * perdas_multiplier
                    })

    # 6. Máximo kW recebido
    add_demanda_section('kW recebido', 'kW recebido máximo')

    # --- Chama o diálogo se houver resultados ---
    if table_data:
        df_resultados = pd.DataFrame(table_data)
        
        # Formatação das colunas numéricas para exibição
        df_resultados['Valor'] = df_resultados['Valor'].apply(lambda x: f"{x:,.4f}" if isinstance(x, (int, float)) else x)
        df_resultados['K'] = df_resultados['K'].apply(lambda x: f"{x}" if isinstance(x, (int, float)) else x)
        df_resultados['Perdas (%)'] = df_resultados['Perdas (%)'].apply(lambda x: f"{x:,.1f}" if isinstance(x, (int, float)) else x)
        df_resultados['Valor Final'] = df_resultados['Valor Final'].apply(lambda x: f"{x:,.4f}" if isinstance(x, (int, float)) else x)
        
        show_results_dialog(df_resultados)
        
    # Lógica de erro e aviso
    elif consumo_injecao and not resultados_consumo:
        st.error("Não foi possível encontrar dados de consumo/injeção válidos no primeiro campo.")
    elif kW_kwinj_dre_ere and not resultados_demanda:
        st.error("Não foi possível encontrar dados de demanda/DRE/ERE válidos no segundo campo.")
    elif not consumo_injecao and not kW_kwinj_dre_ere:
        st.warning("Por favor, cole o conteúdo em um ou ambos os campos de texto antes de calcular.")

