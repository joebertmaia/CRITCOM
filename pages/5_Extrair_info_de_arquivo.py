import streamlit as st
import io

def obterDados(data, posicao, tamanho):
    """
    Extrai uma porção de dados de uma string com base na posição e tamanho.
    A posição é baseada em 1 (e não em 0 como no índice de strings do Python).

    Args:
        data (str): A string de onde os dados serão extraídos.
        posicao (int): A posição inicial (base 1) para a extração.
        tamanho (int): O número de caracteres a serem extraídos.

    Returns:
        str: A porção extraída da string.
    """
    # Converte a posição de base 1 para base 0 para o fatiamento do Python
    posicao_base_0 = posicao - 1

    # Garante que a posição inicial não seja negativa
    if posicao_base_0 < 0:
        return ""

    # Calcula a posição final
    posicao_final = posicao_base_0 + tamanho

    # Retorna a fatia da string, o fatiamento do Python já lida com índices
    # que ultrapassam o comprimento da string de forma segura.
    return data[posicao_base_0:posicao_final]

# --- Interface do Streamlit ---

# Configurações da página
st.set_page_config(layout="centered", page_title="Extrator de Dados")

# Título principal do aplicativo
st.title("✂️ Extrator de Dados de Arquivo")

st.write(
    "Faça o upload de um arquivo de texto e extraia uma porção específica dos dados "
    "informando a posição inicial e o tamanho do trecho desejado."
)

# Widget para upload do arquivo
uploaded_file = st.file_uploader(
    "Escolha um arquivo de texto (.txt)")

# Utiliza o estado da sessão para persistir o conteúdo do arquivo
if 'file_content' not in st.session_state:
    st.session_state.file_content = ""

# Processa o arquivo se ele for enviado
if uploaded_file is not None:
    # Para ler o arquivo como texto, é preciso decodificá-lo.
    # Usamos um StringIO para tratar o arquivo em memória de forma eficiente.
    stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8", errors="ignore"))
    
    # Lê o conteúdo do arquivo e o armazena no estado da sessão, MANTENDO as quebras de linha.
    file_content_raw = stringio.read()
    st.session_state.file_content = file_content_raw

    st.info("Conteúdo do arquivo (com quebras de linha):")
    st.text_area("Conteúdo", st.session_state.file_content, height=150, disabled=True)

# Só mostra os campos de entrada e o botão se houver conteúdo no arquivo
if st.session_state.file_content:
    st.markdown("---")
    st.header("Defina os parâmetros para extração")

    # Cria duas colunas para organizar os campos de entrada
    col1, col2 = st.columns(2)

    with col1:
        # Campo numérico para o usuário inserir a posição inicial
        posicao = st.number_input(
            "Posição Inicial (base 1)", 
            min_value=1, 
            value=1, 
            step=1,
            help="O primeiro caractere do texto está na posição 1. Quebras de linha contam como um caractere."
        )

    with col2:
        # Campo numérico para o usuário inserir o tamanho da extração
        tamanho = st.number_input(
            "Tamanho (nº de caracteres)", 
            min_value=1, 
            value=10, 
            step=1,
            help="Quantos caracteres você deseja extrair a partir da posição inicial."
        )

    # Botão para executar a extração
    if st.button("Extrair Dados", type="primary", use_container_width=True):
        # Chama a função com os dados do arquivo e os parâmetros do usuário
        resultado = obterDados(st.session_state.file_content, posicao, tamanho)
        
        st.success("Resultado da Extração:")
        
        # Mostra o resultado em uma caixa de código para melhor visualização
        st.code(resultado, language="")
        
        st.write(f"**Tamanho do resultado:** {len(resultado)} caractere(s)")
else:
    st.warning("Aguardando o upload de um arquivo para começar.")
