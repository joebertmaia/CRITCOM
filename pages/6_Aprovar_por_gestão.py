import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from datetime import datetime, timedelta
import os

# --- Configurações da Página do Streamlit ---
st.set_page_config(page_title="Automação Hemera", layout="wide")
st.title("Automação de Aprovação por Gestão no Hemera")
st.markdown("---")

# --- Funções da Automação (do código original) ---
# Adicionei os parâmetros 'usuario' e 'senha' na função de login
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
    """Navega até a tela de 'Aprovação por Gestão'."""
    iframe = WebDriverWait(driver, Tesp).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[14]/div[2]/div[2]/div/iframe"))
    )
    driver.switch_to.frame(iframe)
    sleep(1)

    inputInte = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/table/tbody/tr/td[5]/table/tbody/tr/td[2]/em/button")
    inputInte.click()
    sleep(2)

    if cliente == "Grupo B":
        inputGestão = driver.find_element(By.XPATH, "/html/body/form/ul/li[3]/ul/li[2]/a")
    else:
        inputGestão = driver.find_element(By.XPATH, "/html/body/form/ul/li[3]/ul/li[3]/a")
    inputGestão.click()
    sleep(2)

    driver.switch_to.default_content()

def automacao(driver, UC, Tesp=60):
    """Executa a automação para uma única Unidade Consumidora."""
    inputUC = WebDriverWait(driver, Tesp).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[1]/fieldset/div[1]/div[7]/div/input"))
    )
    inputUC.clear()
    sleep(1)
    inputUC.send_keys(UC) # UC já vem formatada com 10 dígitos
    sleep(1)

    inputPes = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[2]/div/table/tbody/tr/td/table/tbody/tr/td[2]/em/button")
    inputPes.click()
    sleep(2)

    if cliente == "Grupo B":
        inputges = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr[1]/td[1]/div/div/a")
    else:
        inputges = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr/td[2]/div/div/a/img")
    inputges.click()
    sleep(2)

    botao_OK = WebDriverWait(driver, Tesp).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[24]/div[2]/div[2]/div/table/tbody/tr/td[1]/table/tbody/tr/td[2]/em/button"))
    )
    botao_OK.click()
    sleep(2)

# --- Interface do Usuário ---
st.header("1. Tipo de cliente")
cliente = st.radio("Selecione o tipo de cliente:", ("Grupo B", "Cliente livre"), index=0, horizontal=True)

st.header("2. Parâmetros de Entrada")

col1, col2 = st.columns(2)

with col1:
    controladores_options = [
        "ENERGISA MT", "ENERGISA MS", "ENERGISA MR", "ENERGISA SE",
        "ENERGISA PB", "ENERGISA AC", "ENERGISA RO", "ENERGISA SS", "ENERGISA TO"
    ]
    controlador = st.selectbox("Selecione o Controlador:", controladores_options)
    
    if cliente == "Grupo B":
        lote = st.number_input("Insira o número do Lote:", min_value=1, step=1)
        seta = 2 # Quantidade de vezes necessária para descer a seta até "Pendente de Aprovação"
    else:
        lote = 1 # Valor fixo para Cliente livre
        seta = 3 # Quantidade de vezes necessária para descer a seta até "Pendente de Aprovação"

with col2:
    inputUsuario = st.text_input("Usuário do Hemera:")
    inputSenha = st.text_input("Senha do Hemera:", type="password")

st.header("3. Unidades Consumidoras")
ucs_input = st.text_area(
    "Cole aqui as UCs que deseja processar (uma por linha):",
    height=250
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

                # Verifica se o Chrome e o ChromeDriver estão no caminho especificado
                user_home = os.path.expanduser('~') # Pega o diretório home do usuário (C:\Users\XXXXX)
                custom_chrome_path = os.path.join(user_home, 'Downloads', 'chrome-win64', 'chrome.exe')
                custom_driver_path = os.path.join(user_home, 'Downloads', 'chromedriver-win64', 'chromedriver.exe')
                
                st.info("Verificando configuração do Chrome...")

                chrome_options = Options()
                chrome_options.add_argument("--headless")  # Roda o Chrome em modo headless (sem interface gráfica)
                chrome_options.add_argument("--no-sandbox")  # Necessário para rodar como root em ambientes de container
                chrome_options.add_argument("--disable-dev-shm-usage") # Medida de estabilidade em containers
                chrome_options.add_argument("--disable-gpu") # Desabilita a GPU, já que não há uma no servidor
                chrome_options.add_argument("window-size=1920,1080") # Define um tamanho de janela para evitar problemas de layout
                chrome_options.add_argument("--ignore-certificate-errors")

                if os.path.exists(custom_chrome_path) and os.path.exists(custom_driver_path):
                    st.success("Versão personalizada do Chrome encontrada. Usando caminhos específicos.")
                    
                    # Aponta o chromedriver personalizado
                    service = Service(executable_path=custom_driver_path)

                    # Aponta o chrome.exe personalizado
                    options = Options()
                    options.binary_location = custom_chrome_path

                    # Inicializa o driver com os caminhos personalizados
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    st.success("Usando a instalação padrão do Chrome (gerenciada automaticamente).")
                    
                    # O Selenium Manager cuida de tudo
                    driver = webdriver.Chrome()

                with st.spinner("Abrindo navegador e fazendo login..."):
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

                    if cliente == "Grupo B":
                        # Clica no campo para abrir a busca de Lote
                        inputLote = WebDriverWait(driver, Tesp).until(
                                EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[2]/div[2]/div/div/div[1]/form/div[1]/fieldset/div[1]/div[3]/div/input"))
                        ).click()
                        sleep(1)
                        # Aguarda o campo de texto do lote aparecer, digita o número e pesquisa
                        input_pesquisa_lote = WebDriverWait(driver, Tesp).until(
                            EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[7]/div[2]/div/div[2]/div/div[1]/form/div[1]/fieldset/div[1]/div/input"))
                        )
                        input_pesquisa_lote.send_keys(str(lote))
                        sleep(1)
                        # Clicar em pesquisar o lote
                        inputLote = driver.find_element(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[7]/div[2]/div/div[2]/div/div[1]/form/div[2]/div/table/tbody/tr/td[1]/table/tbody/tr/td[2]/em/button").click()
                        # Loop principal de paginação
                        while True:
                            # Flag para controlar se lote foi encontrado na página atual
                            lote_encontrado_na_pagina = False
                            WebDriverWait(driver, Tesp).until(
                                EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[6]/div[2]/div/div[2]/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr"))
                            )
                            sleep(1)

                            linhas_lotes = driver.find_elements(By.XPATH, "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[6]/div[2]/div/div[2]/div/div[2]/div/div[1]/div[4]/div[2]/table/tbody/tr")
                            
                            # Procura o lote na lista da página atual
                            for linha in linhas_lotes:
                                if linha.text.strip().startswith(str(lote) + " -"):
                                    st.success(f"Lote {lote} encontrado! Clicando...")
                                    linha.click()
                                    lote_encontrado_na_pagina = True
                                    break # Sai do loop 'for' pois já encontramos

                            # Se o lote foi encontrado, podemos sair do loop principal 'while'
                            if lote_encontrado_na_pagina:
                                break

                            # Se o lote NÃO foi encontrado na página atual, tenta ir para a próxima
                            try:
                                xpath_proxima_pagina = "/html/body/div[2]/table/tbody/tr[2]/td[2]/div[6]/div[2]/div/div[2]/div/div[2]/div/div[1]/div[1]/div/table/tbody/tr/td[8]/table/tbody/tr/td[2]/em/button"
                                
                                botao_proxima_pagina = WebDriverWait(driver, 10).until(
                                    EC.element_to_be_clickable((By.XPATH, xpath_proxima_pagina))
                                )
                                st.warning("Lote não encontrado nesta página. Procurando na próxima...")
                                botao_proxima_pagina.click()
                                
                                # Espera um pouco para a nova página carregar
                                sleep(2)

                            except Exception as e:
                                st.warning(f"Não foi possível encontrar o botão 'Próxima Página' ou ele está desabilitado. Fim da busca pelo lote {lote}.")
                                st.warning(f"O lote {lote} não foi encontrado em nenhuma das páginas.")
                                break # Sai do loop 'while' porque não há mais páginas

                            sleep(1) # Pausa final após encontrar e clicar ou terminar a busca

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

                    for i in range(seta):
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
                        st.warning(f"Falha ao processar a UC {uc_display}. Verifique manualmente.")
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