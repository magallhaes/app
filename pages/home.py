import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO

# Verificar autenticação
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.error("Por favor, faça login para acessar esta página.")
    st.switch_page("login.py")  # Redireciona para a página de login
    st.stop()

@st.cache_data
# Função para processar as planilhas
def processar_planilhas(planilha1, planilha2, data_fim, nomes_clientes):
    # Converter DATA_DOC em formato datetime para comparação
    planilha2['DATA_DOC'] = pd.to_datetime(planilha2['DATA_DOC'], errors='coerce')

    # Criar lista de tipos de operação
    tipos_devolucao = [
        'DEVOLUCAO DE COMPRA PARA COMERCIALIZACAO',
        'DEVOLUCAO SIMB. MERC.VENDIDA REC. ANT.CONSIG. MERC/IND.',
        'DEVOLUCAO DE MERCADORIA EM CONSIGNACAO MERC. OU IND.',
        'DEVOLUCAO MERCADORIA REMETIDA EM CONSIGNACAO MERC./IND.',
        'DEVOL. SIMBOLICA MERC. VEND./UTIL. PROCES. IND. CONSIG.',
        'DEVOLUCAO DE VENDA  MERC. ADQUIRIDA /  RECEB. TERCEIROS',
        'DEVOLUCAO DE VENDA DE MERC. ADQUIRIDA/ RECEB. TERCEIROS'
    ]

    tipo_faturamento = 'VENDAS DE MERC. ADQUIRIDAS E/OU RECEBIDAS DE TERCEIROS'

    # Normalizar tipos de dados para garantir correspondência
    planilha1['COD'] = planilha1['COD'].astype(str)
    planilha1['LOTE'] = planilha1['LOTE'].astype(str)
    planilha2['COD_PROD'] = planilha2['COD_PROD'].astype(str)
    planilha2['LOTE'] = planilha2['LOTE'].astype(str)

    # Filtrar devoluções após a data do inventário
    devolucoes_pos_inventario = planilha2[
        (planilha2['DATA_DOC'] > data_fim) &
        (planilha2['TIPO_OPER'].isin(tipos_devolucao)) &
        (planilha2['NOME_CLI'].str.contains('|'.join(nomes_clientes), na=False, case=False))
    ]

    # Filtrar registros de faturamento
    faturamentos = planilha2[
        (planilha2['TIPO_OPER'] == tipo_faturamento)
    ]

    # Exibir nomes de clientes encontrados para validação
    clientes_encontrados = devolucoes_pos_inventario['NOME_CLI'].unique()
    st.write("Clientes encontrados nas devoluções:", clientes_encontrados)

    # Preparar a planilha de resultados com o mesmo formato da planilha 1
    resultado = planilha1.copy()
    resultado['QTD_DEVOLVIDA'] = 0
    resultado['infor'] = ''
    resultado['FATURADO'] = ''
    

    # Iterar sobre as linhas da planilha 1
    for index, row in planilha1.iterrows():
        cod = row['COD']
        lote = row['LOTE']
        diferenca = row['DIFERENÇAS']

        # Filtrar devoluções relacionadas ao produto e lote após o inventário
        devolucoes = devolucoes_pos_inventario[
            (devolucoes_pos_inventario['COD_PROD'] == cod) &
            (devolucoes_pos_inventario['LOTE'] == lote)
        ]

        # Debug: Exibir devoluções filtradas
        #st.write(f"Devoluções filtradas para COD: {cod}, LOTE: {lote}")
        #st.write(devolucoes)

        # Ordenar as devoluções pela proximidade da data do inventário
        devolucoes['PROXIMIDADE'] = (devolucoes['DATA_DOC'] - data_fim).abs()
        devolucoes = devolucoes.sort_values(by='PROXIMIDADE')

        if not devolucoes.empty:
            mensagens = []
            diferenca_atual = diferenca
            for _, devolucao in devolucoes.iterrows():
                quantidade_dev = devolucao['QUANTIDADE']
                
                mensagens.append(f"CONSTA DEV ({-quantidade_dev})UND. NA DATA({devolucao['DATA_DOC'].date()})")
                # Calculate the total quantity returned
                total_devolvido = devolucoes['QUANTIDADE'].sum()
                resultado.at[index, 'QTD_DEVOLVIDA'] = total_devolvido
                #mensagens.append(f"TOTAL DEVOLVIDO: {-total_devolvido} UND.")

                # Reduzir a diferença restante e parar se atingir o limite
                diferenca_atual -= 1
                if len(mensagens) >= diferenca:
                    break

            resultado.at[index, 'infor'] = ' ; '.join(mensagens)
        else:
            #st.write(f"Nenhuma devolução encontrada para COD: {cod}, LOTE: {lote}")
            resultado.at[index, 'infor'] = "NÃO CONSTA DEVOLUÇÃO, VERIFICAR SE A UTILIZAÇÃO"

        # Filtrar faturamentos relacionados ao produto, lote e cliente
        faturamento_relacionado = faturamentos[
            (faturamentos['COD_PROD'] == cod) &
            (faturamentos['LOTE'] == lote) &
            (faturamentos['NOME_CLI'].isin(nomes_clientes))
        ]

        # Verificar se a coluna "infor" indica ausência de devolução
        if resultado.at[index, 'infor'] == "NÃO CONSTA DEVOLUÇÃO, VERIFICAR SE A UTILIZAÇÃO":
            resultado.at[index, 'FATURADO'] = "NÃO HÁ FATURAMENTO"
        else:
            # Filtrar apenas os faturamentos com DATA_DOC igual ou posterior às datas em "infor"
            datas_devolucao = [
                pd.to_datetime(msg.split('NA DATA(')[-1].split(')')[0])
                for msg in resultado.at[index, 'infor'].split(' ; ')
            ]
            data_minima = min(datas_devolucao) if datas_devolucao else None
            faturamento_relacionado = faturamento_relacionado[
                (faturamento_relacionado['DATA_DOC'] >= data_minima)
            ]

            if not faturamento_relacionado.empty:
                mensagens_faturamento = []
                for _, faturamento in faturamento_relacionado.iterrows():
                    mensagens_faturamento.append(
                        f"FAT ({faturamento['QUANTIDADE']})UNI DATA({faturamento['DATA_DOC'].date()}) NOTA FISCAL ({faturamento['NF']})"
                    )

                resultado.at[index, 'FATURADO'] = ' ; '.join(mensagens_faturamento)
            else:
                resultado.at[index, 'FATURADO'] = "NÃO HÁ FATURAMENTO"

    return resultado

# Configuração da página do Streamlit
#st.title("Análisede Inventário e Faturamento")
#st.write("Carregue as planilhas e configure a data de inventário para gerar o relatório.")
st.set_page_config(
    page_title="Análisede Inventário e Faturamento",
    layout="wide",
    page_icon="assets/images/fav.svg"
)
# Sidebar com logo e filtros
logo = "assets/images/logo.png" # Insira o caminho do seu logo aqui
icon ="assets/images/logo.png" # Insira o caminho do seu logo aqui
st.logo(logo, icon_image=icon)
#st.image(logo, use_column_width=True)
#st.sidebar.image(icon, use_column_width=True)
  # Create two columns for file uploads
# Create two columns for file uploads
col1, col2 = st.columns(2)

with col1:
    upload1 = st.file_uploader("Carregue a primeira planilha (Inventário):", type=['xlsx'])

with col2:    
    upload2 = st.file_uploader("Carregue a segunda planilha (Movimentos):", type=['xlsx'])


  # Create two columns for date and client selection
col3, col4 = st.columns(2)

with col3:
      data_fim = st.date_input("Data do inventário:")
      data_fim = pd.to_datetime(data_fim)

with col4:
      if upload2:
          try:
              planilha2 = pd.read_excel(upload2)
              if 'NOME_CLI' in planilha2.columns:
                  clientes_unicos = planilha2['NOME_CLI'].dropna().unique()
                  nomes_clientes = st.multiselect("Selecione os clientes:", options=sorted(clientes_unicos))
              else:
                  st.error("A coluna 'NOME_CLI' não foi encontrada na planilha de movimentos.")
                  nomes_clientes = []
          except Exception as e:
              st.error(f"Erro ao processar a planilha de movimentos: {e}")
              nomes_clientes = []
      else:
          nomes_clientes = []
# Processar as planilhas quando todas as entradas forem fornecidas
if st.button("Gerar Relatório"):
    if upload1 and upload2 and nomes_clientes:
        try:
            # Carregar as planilhas
            planilha1 = pd.read_excel(upload1, skiprows=4)  # Começa na linha 5

            # Processar os dados
            resultado = processar_planilhas(planilha1, planilha2, data_fim, nomes_clientes)

            # Gerar o arquivo para download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:

                    resultado.to_excel(writer, index=False, sheet_name='Relatório')
            output.seek(0)

            # Pega o nome da planilha1 para o nome do arquivo de download
            if upload1:
                nome_arquivo_planilha1 = upload1.name
                nome_relatorio = f"TRATATIVA - {nome_arquivo_planilha1}"
            else:
                nome_relatorio = "relatorio_filtrado.xlsx"

            # Depois do processamento e ao gerar o relatório
            st.success("Relatório gerado com sucesso!")
            st.download_button(
                label="Baixar Relatório", 
                data=output, 
                file_name=nome_relatorio,  # Nome do arquivo de download baseado no nome da planilha 1
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"Erro ao processar os dados: {e}")
    else:
        st.warning("Por favor, carregue as duas planilhas e selecione os clientes antes de gerar o relatório.")

# Adicionar o rodapé
footer = """
<style>
    .footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        text-align: center;
        font-size: 14px;
        color: #666;
        background-color: #f9f9f9;
        padding: 10px;
        align-items: center;
        justify-content: center;
        
    }
</style>
<div class="footer">
    Desenvolvido por Leonardo Magalhães - © 2025
</div>
"""
st.markdown(footer, unsafe_allow_html=True)
