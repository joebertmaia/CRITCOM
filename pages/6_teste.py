import streamlit as st
import pandas as pd
import getpass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from datetime import datetime, timedelta

# --- Configurações da Página do Streamlit ---
st.set_page_config(page_title="Automação Hemera", layout="wide")
st.title("Aprovação por Gestão no Hemera")
with st.expander("Para utilizar esse aplicativo, copie o arquivo chrome.7z na rede, cole na sua pasta Downloads e use a opção \"Extrair aqui\"",expanded=False,icon=":material/add_alert:"):
    st.write('As pastas devem ficar assim em Downloads:')
    st.image(f"data:image/png;base64,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")
st.markdown("---")

# --- Funções da Automação com os parâmetros 'usuario' e 'senha' na função de login ---
def login(driver, usuario, senha, Tesp=60):
    """Realiza o login no sistema Hemera."""
    inputUsuario = WebDriverWait(driver, Tesp).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/form/div/div[1]/div/input"))
    )
    inputUsuario.send_keys(usuario)
    sleep(1)

    inputSenha = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/form/div/div[3]/div/input")
    inputSenha.send_keys(senha)
    sleep(1)

    inputSeta = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[1]/div[1]/form/div/div[5]/div/div/input[2]")
    inputSeta.click()
    sleep(1)

    inputServidor = driver.find_element(By.XPATH, "/html/body/div[3]/div/div[4]")
    inputServidor.click()
    sleep(1)

    buttonLogin = driver.find_element(By.XPATH, "/html/body/div[1]/div[2]/div[2]/div[1]/div[2]")
    buttonLogin.click()

def integracao(driver, Tesp=60):
    """Navega até a tela de 'Integração MT'"""
    iframe = WebDriverWait(driver, Tesp).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[14]/div[2]/div[2]/div/iframe"))
    )
    driver.switch_to.frame(iframe)
    sleep(1)

    inputInte = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/table/tbody/tr/td[5]/table/tbody/tr/td[2]/em/button")
    inputInte.click()
    sleep(2)

    inputGestão = driver.find_element(By.XPATH, "/html/body/form/ul/li[3]/ul/li[2]/a")
    inputGestão.click()
    sleep(2)

    driver.switch_to.default_content()

def automacao(driver, UC, Tesp=60):
    """Executa a automação para uma única Unidade Consumidora."""
    inputUC = WebDriverWait(driver, Tesp).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[1]/fieldset/div[1]/div[7]/div/input"))
    )
    # Apaga a UC anterior
    inputUC.clear()
    sleep(0.5)

    # Digita a UC nova
    inputUC.send_keys(UC) # UC já vem formatada com 10 dígitos
    sleep(0.5)

    # Clica em Pesquisar
    inputPes = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[2]/div/table/tbody/tr/td/table/tbody/tr/td[2]/em/button")
    inputPes.click()
    sleep(5)

    # Clica na engrenagem "Aprovar Leitura"
    inputges = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr[1]/td[1]/div/div/a")
    inputges.click()
    sleep(0.5)

    # Aguarda aparecer a janela de Leitura aprovada
    botao_OK = WebDriverWait(driver, Tesp).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[24]/div[2]/div[2]/div/table/tbody/tr/td[1]/table/tbody/tr/td[2]/em/button"))
    )
    botao_OK.click()
    sleep(0.5)


# --- Interface do Usuário ---
st.header("1. Parâmetros de Entrada")

col1, col2 = st.columns(2)

with col1:
    controladores_options = [
        "ENERGISA MT", "ENERGISA MS", "ENERGISA MR", "ENERGISA SE",
        "ENERGISA PB", "ENERGISA AC", "ENERGISA RO", "ENERGISA SS", "ENERGISA TO"
    ]
    controlador = st.selectbox("Selecione o Controlador:", controladores_options)
    
    inputUsuario = st.text_input("Usuário Hemera:")

with col2:
    lote = st.number_input("Insira o número do Lote:", min_value=1, step=1, value=1)
    
    inputSenha = st.text_input("Senha Hemera:", type="password")

st.header("2. Unidades Consumidoras")
ucs_input = st.text_area(
    "Cole aqui as UCs que deseja processar (uma por linha):",
    height=250,
    placeholder="Exemplo:\n6464\n1234567890\n98765"
)

# --- Botão para iniciar o processamento ---
if st.button("🚀 Iniciar Processamento", type="primary"):
    # Validações iniciais
    if not inputUsuario or not inputSenha:
        st.error("Por favor, informe seu usuário e senha.")
    elif not ucs_input.strip():
        st.error("Por favor, insira pelo menos uma Unidade Consumidora.")
    else:
        # Processamento e validação das UCs
        ucs_raw = ucs_input.strip().split('\n')
        ucs_para_processar = []
        ucs_para_display = []
        ucs_invalidas = []

        for uc in ucs_raw:
            uc_limpa = uc.strip()
            if uc_limpa: # Ignora linhas vazias
                if uc_limpa.isdigit() and len(uc_limpa) <= 10:
                    ucs_para_display.append(uc_limpa)
                    ucs_para_processar.append(uc_limpa.zfill(10)) # Adiciona zeros à esquerda
                else:
                    ucs_invalidas.append(uc_limpa)

        if ucs_invalidas:
            st.error(f"As seguintes UCs são inválidas (possuem letras ou mais de 10 dígitos) e não serão processadas: {', '.join(ucs_invalidas)}")
        
        if not ucs_para_processar:
            st.warning("Nenhuma UC válida foi inserida para processamento.")
        else:
            st.info(f"Iniciando automação para {len(ucs_para_processar)} UCs válidas...")
            
            # Cria o DataFrame para armazenar os resultados
            df_resultado = pd.DataFrame({
                'UC': ucs_para_display,
                'Status': "Pendente"
            })
            
            # Placeholder para a tabela de resultados
            resultado_placeholder = st.empty()
            resultado_placeholder.dataframe(df_resultado)

            driver = None # Inicializa a variável driver
            try:
                # --- Início da Lógica de Automação ---
                Tesp = 60
                amanha = datetime.now() + timedelta(days=1)
                amanha_str = amanha.strftime("%d/%m/%Y")

                driver_path = fr"C:\Users\{getpass.getuser()}\Downloads\chromedriver-win64\chromedriver.exe"
                service = Service(driver_path)

                chrome_options = Options()
                chrome_options.add_argument("start-maximized")
                chrome_options.add_argument("--ignore-certificate-errors")

                with st.spinner("Abrindo navegador e fazendo login..."):
                    # Se quiser rodar com um Chrome específico (chrome.exe em outra pasta):
                    chrome_options.binary_location = fr"C:\Users\{getpass.getuser()}\Downloads\chrome-win64\chrome.exe"
                    
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    driver.get("http://172.16.102.245:8082/hemera/hemera.jsp")
                    
                    login(driver, inputUsuario, inputSenha, Tesp)
                    sleep(2)
                    integracao(driver, Tesp)
                    sleep(2)

                with st.spinner("Configurando filtros (Controlador, Lote, etc)..."):
                    iframe = WebDriverWait(driver, Tesp).until(
                        EC.presence_of_element_located((By.XPATH, "/html/body/div[14]/div[2]/div[2]/iframe[1]"))
                    )
                    driver.switch_to.frame(iframe)

                    # Clica no campo do Controlador
                    WebDriverWait(driver, Tesp).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[1]/fieldset/div[1]/div[1]/div/input"))).click()
                    # Digita o Controlador
                    inputEmpresa = WebDriverWait(driver, Tesp).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[5]/div[2]/div/div[2]/div/div[1]/form/div[1]/fieldset/div[1]/div/input")))
                    inputEmpresa.send_keys(controlador)
                    sleep(1)
                    # Clica em Pesquisar
                    WebDriverWait(driver, Tesp).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[5]/div[2]/div/div[2]/div/div[1]/form/div[2]/div/table/tbody/tr/td[1]/table/tbody/tr/td[2]/em/button"))).click()
                    sleep(1)
                    # Clica no Controlador
                    WebDriverWait(driver, Tesp).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[5]/div[2]/div/div[2]/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr/td[3]/div/div"))).click()
                    sleep(1)

                    # Clica no campo do Lote
                    inputLote = WebDriverWait(driver, Tesp).until(
                        EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[1]/fieldset/div[1]/div[3]/div/input"))
                    ).click()

                    sleep(1)

                    inputLote = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[7]/div[2]/div/div[2]/div/div[1]/form/div[1]/fieldset/div[1]/div/input")
                    inputLote.send_keys(lote)
                    sleep(1)

                    # Clicar em pesquisar o lote

                    inputLote = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[7]/div[2]/div/div[2]/div/div[1]/form/div[2]/div/table/tbody/tr/td[1]/table/tbody/tr/td[2]/em/button").click()

                    sleep(1)

                    # Esperar a lista de lote ficar disponível para seleção

                    inputLote = WebDriverWait(driver, Tesp).until(
                            EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[6]/div[2]/div/div[2]/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr[1]/td[3]/div/div"))
                    )

                    lotes = driver.find_elements(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[6]/div[2]/div/div[2]/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr")

                    for el in lotes:
                        if el.get_property("innerText").startswith(str(lote) + " -"):
                            el.click()
                    
                    # Preenche a data final da leitura como hoje+1
                    data_final = WebDriverWait(driver, Tesp).until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[1]/fieldset/div[1]/fieldset/div[3]/div/div/input")))
                    data_final.clear()
                    sleep(1)
                    data_final.send_keys(amanha_str)
                    sleep(1)

                    # Seleciona a opção "Pendente de Aprovação"
                    lista_situacao = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[1]/fieldset/div[2]/div[7]/div/div/input[2]")
                    lista_situacao.click()
                    sleep(1)

                    for i in range(2):
                        lista_situacao.send_keys(Keys.ARROW_DOWN)
                        sleep(0.5)
                    lista_situacao.send_keys(Keys.ENTER)

                # Loop para processar cada UC
                st.info("Iniciando o processamento das UCs...")
                progress_bar = st.progress(0)
                total_ucs = len(ucs_para_processar)
                
                for i, uc_processar in enumerate(ucs_para_processar):
                    try:
                        uc_display = ucs_para_display[i]
                        st.write(f"Processando UC: **{uc_display}**...")
                        automacao(driver, uc_processar, Tesp)
                        df_resultado.loc[i, 'Status'] = "✅ Processado"
                    except Exception as e:
                        st.warning(f"Falha ao processar a UC {uc_display}. Erro: {e}")
                        df_resultado.loc[i, 'Status'] = "❌ Falha"
                    
                    # Atualiza a UI
                    progress_bar.progress((i + 1) / total_ucs)
                    resultado_placeholder.dataframe(df_resultado)

                st.success("🎉 Processamento concluído!")

            except Exception as e:
                st.error(f"Ocorreu um erro geral na automação: {e}")
            
            finally:
                if driver:
                    driver.quit()
                    st.info("Navegador fechado.")