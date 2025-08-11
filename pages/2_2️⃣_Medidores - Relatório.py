import streamlit as st
import pandas as pd
import re
from io import StringIO
import streamlit.components.v1 as components
import json

# --- Configuração da Página ---
st.set_page_config(
    page_title="Dois medidores - Faturamento",
    page_icon="https://www.energisa.com.br/sites/energisa/files/Energisa120%20%281%29.ico",
    layout="wide",
    menu_items={
        'About': "Versão 1.0.0. Bugs ou sugestões, enviar um e-mail para joebert.oliveira@energisa.com.br"}
)

st.logo(
    "CRITCOM.svg",
    icon_image="CRITCOM.svg",
)

# --- FUNÇÕES DE PROCESSAMENTO ---

def processar_dados_faturamento(texto_bruto):
    """Processa o relatório de faturamento para extrair os valores de consumo e demanda."""
    if not texto_bruto:
        return None, None

    resultados_consumo = {}
    resultados_demanda = {}
    
    # Mapeamento de nomes no relatório para chaves consistentes
    mapa_grandezas = {
        'kWh fornecido': 'kWh fornecido',
        'kWh recebido': 'kWh recebido',
        'kWh fornecido - Demanda máxima': 'kW fornecido',
        'kWh recebido - Demanda máxima': 'kW recebido',
        'UFER': 'UFER',
        'DMCR': 'DMCR'
    }

    postos_pattern = r"(Fora Ponta|Ponta|Reservado)\n([\s\S]*?)(?=\n\n|\Z|Dados gerais do faturamento|Fora Ponta|Ponta|Reservado)"
    
    for posto_match in re.finditer(postos_pattern, texto_bruto):
        posto = posto_match.group(1)
        bloco_dados = posto_match.group(2)
        
        for nome_relatorio, chave_interna in mapa_grandezas.items():
            valor_match = re.search(rf"^{re.escape(nome_relatorio)}\s+([\d.,-]+)", bloco_dados, re.MULTILINE)
            if valor_match:
                valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
                valor_num = pd.to_numeric(valor_str, errors='coerce')
                
                # Separa em consumo (soma) e demanda (máximo)
                if chave_interna in ['kWh fornecido', 'kWh recebido', 'UFER']:
                    if chave_interna not in resultados_consumo:
                        resultados_consumo[chave_interna] = {'operacao': 'soma', 'valores': {}}
                    resultados_consumo[chave_interna]['valores'][posto] = valor_num
                else: 
                    if chave_interna not in resultados_demanda:
                        op = 'soma' if chave_interna == 'UFER' else 'máximo'
                        resultados_demanda[chave_interna] = {'operacao': op, 'valores': {}}
                    resultados_demanda[chave_interna]['valores'][posto] = valor_num

    # Garante que todos os postos existam em todos os resultados para consistência
    postos_horarios = ['Fora Ponta', 'Ponta', 'Reservado']
    for res_dict in [resultados_consumo, resultados_demanda]:
        for grandeza in res_dict:
            for posto in postos_horarios:
                if posto not in res_dict[grandeza]['valores']:
                    res_dict[grandeza]['valores'][posto] = 0.0
    
    return resultados_consumo, resultados_demanda

def extrair_info_cliente(texto_bruto):
    """Extrai informações de Contrato e Serial de qualquer um dos textos."""
    info = {"contrato": "Não encontrado", "serial": "Não encontrado"}
    if not texto_bruto: return info
    
    # Padrões para MM Bruta e Faturamento
    contrato_match = re.search(r"Cliente \(contrato\)\s+(\d+)|Contrato\s+(\d+)", texto_bruto)
    serial_match = re.search(r"Medidor \(serial\)\s+(\d+)|Medidor\s+(\d+)|Serial do medidor\s+(\d+)", texto_bruto)
    
    if contrato_match:
        info["contrato"] = next((g for g in contrato_match.groups() if g is not None), "Não encontrado")
    if serial_match:
        info["serial"] = next((g for g in serial_match.groups() if g is not None), "Não encontrado")
        
    return info

# --- Diálogo de Resultados ---
@st.dialog("Resultados do Cálculo")
def show_results_dialog(df_resultados, contrato, serial_antigo, serial_novo):
    """Exibe o DataFrame de resultados em um diálogo."""
    
    # --- Geração Manual da Tabela HTML ---
    title_html = f"<h3>Resultados para o Contrato: {contrato}</h3>" if contrato else ""
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
                if i == 4 or i == 8: class_attr = ' class="thick-border-right"'
                body_html += f'<td{class_attr}>{cell_value}</td>'
            body_html += "</tr>"
    body_html += "</tbody>"

    table_html = f"<table>{header_html}{body_html}</table>"

    components.html(f"""
        <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
        <style>
            .capture-area {{ padding: 10px; background-color: #ffffff; }}
            table {{ width: 100%; border-collapse: collapse; font-family: sans-serif; font-size: 14px; margin-bottom: 20px; }}
            th, td {{ border: 1px solid #e0e0e0; padding: 8px; text-align: center; }}
            th {{ background-color: #f0f2f6; }}
            .button-container {{ text-align: right; margin-top: 10px; margin-bottom: 20px; }}
            .copy-button {{ background-color: #0068c9; color: white; border: none; padding: 8px 12px; border-radius: 5px; cursor: pointer; }}
            .copy-button:hover {{ background-color: #0055a3; }}
            h3 {{ font-family: sans-serif; text-align: center;}}
            th.thick-border-right, td.thick-border-right {{ border-right: 2px solid #888; }}
            tr.separator-row td {{ text-align: center; font-weight: bold; background-color: #e8e8e8; border-left: 1px solid #e0e0e0; border-right: 1px solid #e0e0e0; }}
        </style>
        <div id="captureTable" class="capture-area">
            {title_html}
            {table_html}
        </div>
        <div class="button-container">
            <button class="copy-button" onclick="copyElementAsImage('captureTable', this)">Copiar Tabela como Imagem</button>
        </div>
        <script>
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
    """, height=700, scrolling=True)

    if st.button("Fechar", key="close_dialog"):
        st.rerun()

# --- Interface do Aplicativo ---
st.title("Confirmação para 2 medidores")
st.markdown("""<style>[aria-label="dialog"]{width: 1100px;}</style>""", unsafe_allow_html=True)

# --- Seção de Parâmetros de Cálculo ---
param1, param2 = st.columns(2)
with param1:
    st.subheader("Medidor Anterior")
    constante_antigo = st.number_input("Constante:", min_value=0.0, value=1.0, step=0.01, format="%.4f", key="const_antigo")
    tipo_opcao_antigo = st.radio("Tipo:", ("Grandeza", "Grandeza EAC", "Pulso"), horizontal=True, key="tipo_antigo", captions=["","Comum em medidores SL7000 da EAC.", "Maioria dos pontos da ERO."])
    perdas_opcao_antigo = st.radio("Adicionar Perdas? :warning: **Não adicionar quando digitar no SILCO** :warning:", ("Não", "Sim"), horizontal=True, key="perdas_antigo", captions=["Se o cliente possuir TP e TC.","Para medições diretas ou em baixa tensão (apenas TC)."])
with param2:
    st.subheader("Medidor Novo")
    constante_novo = st.number_input("Constante:", min_value=0.0, value=1.0, step=0.01, format="%.4f", key="const_novo")
    tipo_opcao_novo = st.radio("Tipo:", ("Grandeza", "Grandeza EAC", "Pulso"), horizontal=True, key="tipo_novo", captions=["","Comum em medidores SL7000 da EAC.", "Maioria dos pontos da ERO."])
    perdas_opcao_novo = st.radio("Adicionar Perdas? :warning: **Não adicionar quando digitar no SILCO** :warning:", ("Não", "Sim"), horizontal=True, key="perdas_novo", captions=["Se o cliente possuir TP e TC.","Para medições diretas ou em baixa tensão (apenas TC)."])

# --- Botões de Ação ---
st.markdown("")
col_btn1, col_btn2, _ = st.columns([1, 1, 4]) # Cria colunas para os botões

with col_btn1:
    calculate_button = st.button("CALCULAR")

with col_btn2:
    def clear_all_text():
        st.session_state.faturamento_antigo = ""
        st.session_state.faturamento_novo = ""
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
    faturamento_antigo = st.text_area("Relatório de faturamento do medidor anterior", height=200, key="faturamento_antigo")
    st.subheader("Medidor Novo")
    faturamento_novo = st.text_area("Relatório de faturamento do medidor novo", height=200, key="faturamento_novo")

# --- Seção de Informações do Cliente ---
info_antigo = extrair_info_cliente(faturamento_antigo)
info_novo = extrair_info_cliente(faturamento_novo)

warnings_list = []
if faturamento_antigo or faturamento_novo:
    if faturamento_antigo:
        if re.search(r"Postos horários e segmentos reativos\s+Cadastro de opção tarifária", faturamento_antigo):
            warnings_list.append(":warning: Atenção: Medidor anterior está com postos horários via 'Cadastro de opção tarifária'. Verifique se os postos estão corretos.")

    contrato_antigo_final = info_antigo['contrato']
    contrato_novo_final = info_novo['contrato']

    if contrato_antigo_final != "Não encontrado" and contrato_novo_final != "Não encontrado" and contrato_antigo_final != contrato_novo_final:
        warnings_list.append(":x: Atenção: Contratos do medidor antigo e novo são diferentes.")

# --- Lógica de Cálculo ---
if calculate_button:
    res_con_antigo, res_dem_antigo = processar_dados_faturamento(faturamento_antigo)
    res_con_novo, res_dem_novo = processar_dados_faturamento(faturamento_novo)
    
    table_data = []
    postos = ['Ponta', 'Reservado', 'Fora Ponta']
    grandezas_a_processar = [
        {'key': 'kWh fornecido', 'type': 'consumo', 'label': 'kWh fornecido acumulado'},
        {'key': 'kW fornecido', 'type': 'demanda', 'label': 'kW fornecido máximo'},
        {'key': 'UFER', 'type': 'consumo', 'label': 'UFER (ERE) acumulado'},
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
        return max(val_antigo, val_novo) if grandeza.startswith("kW ") or grandeza == "DMCR" else val_antigo + val_novo

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
                table_data.append({'Posto Horário': posto, 'Valor calculado (antigo)': val_antigo, 'K (antigo)': k_antigo, 'Perdas (%) (antigo)': perdas_antigo_display, 'Valor final (antigo)': final_antigo, 'Valor calculado (novo)': val_novo, 'K (novo)': k_novo, 'Perdas (%) (novo)': perdas_novo_display, 'Valor final (novo)': final_novo, 'Sumarização': sumarizacao})

    if table_data:
        df_resultados = pd.DataFrame(table_data)
        def format_br(value, precision):
            if pd.isna(value) or value == '': return ''
            if isinstance(value, (int, float)): return f"{{:,.{precision}f}}".format(value).replace(',', 'X').replace('.', ',').replace('X', '.')
            return value
        col_format = {'Valor calculado (antigo)': 4, 'K (antigo)': 4, 'Perdas (%) (antigo)': 1, 'Valor final (antigo)': 4, 'Valor calculado (novo)': 4, 'K (novo)': 4, 'Perdas (%) (novo)': 1, 'Valor final (novo)': 4, 'Sumarização': 4}
        for col, p in col_format.items():
            if col in df_resultados.columns:
                df_resultados[col] = df_resultados[col].apply(lambda x: format_br(x, p))
        
        contrato_antigo_final = info_antigo['contrato']
        contrato_novo_final = info_novo['contrato']
        dialog_title = ""
        if contrato_antigo_final != "Não encontrado" and contrato_novo_final != "Não encontrado" and contrato_antigo_final == contrato_novo_final:
            dialog_title = contrato_antigo_final
        elif contrato_antigo_final != "Não encontrado" and contrato_novo_final == "Não encontrado":
            dialog_title = contrato_antigo_final
        elif contrato_antigo_final == "Não encontrado" and contrato_novo_final != "Não encontrado":
            dialog_title = contrato_novo_final
            
        serial_antigo_final = info_antigo['serial']
        serial_novo_final = info_novo['serial']
        
        show_results_dialog(df_resultados, dialog_title, serial_antigo_final, serial_novo_final)
        
    elif faturamento_antigo or faturamento_novo:
        message_placeholder.error("Não foi possível encontrar dados válidos nos textos informados. Verifique o conteúdo colado.")
    else:
        message_placeholder.warning("Por favor, cole o conteúdo em um ou ambos os campos de texto antes de calcular.")
else:
    if warnings_list:
        message_placeholder.warning("\n\n".join(warnings_list))

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
