import streamlit as st
from streamlit.runtime.scriptrunner import RerunException
import yaml
from yaml.loader import SafeLoader
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
def processar_planilhas(planilha1, planilha2, data_fim, nomes_clientes, convenios):
    # [Previous code remains the same until the tipos_devolucao_venda definition]
    
    tipos_devolucao = [
        'DEVOLUCAO DE COMPRA PARA COMERCIALIZACAO',
        'DEVOLUCAO SIMB. MERC.VENDIDA REC. ANT.CONSIG. MERC/IND.',
        'DEVOLUCAO DE MERCADORIA EM CONSIGNACAO MERC. OU IND.',
        'DEVOLUCAO MERCADORIA REMETIDA EM CONSIGNACAO MERC./IND.',
        'DEVOL. SIMBOLICA MERC. VEND./UTIL. PROCES. IND. CONSIG.',
        'DEVOLUCAO DE VENDA  MERC. ADQUIRIDA /  RECEB. TERCEIROS',
        'DEVOLUCAO DE VENDA DE MERC. ADQUIRIDA/ RECEB. TERCEIROS'
    ]

    tipos_devolucao_venda = [
        'DEVOLUCAO DE VENDA  MERC. ADQUIRIDA /  RECEB. TERCEIROS',
        'DEVOLUCAO DE VENDA DE MERC. ADQUIRIDA/ RECEB. TERCEIROS'
    ]

    tipo_faturamento = 'VENDAS DE MERC. ADQUIRIDAS E/OU RECEBIDAS DE TERCEIROS'

    # Normalizar tipos de dados
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

    # Filtrar devoluções de venda específicas (DEV_CONVENIO)
    devolucoes_venda = planilha2[
        (planilha2['TIPO_OPER'].isin(tipos_devolucao_venda)) &
        (planilha2['NOME_CLI'].str.contains('|'.join(convenios), na=False, case=False))
    ]

    # Filtrar registros de faturamento
    faturamentos = planilha2[
        (planilha2['TIPO_OPER'] == tipo_faturamento)
    ]

    # Exibir nomes de clientes encontrados para validação
    clientes_encontrados = devolucoes_pos_inventario['NOME_CLI'].unique()
    st.write("Clientes encontrados nas devoluções:", clientes_encontrados)

    # Preparar a planilha de resultados
    resultado = planilha1.copy()
    resultado['QTD_DEVOLVIDA'] = 0
    resultado['infor'] = ''
    resultado['FATURADO'] = ''
    resultado['DEV_CONVENIO'] = ''

    # Processar cada linha do resultado
    for index, row in planilha1.iterrows():
        cod = row['COD']
        lote = row['LOTE']
        diferenca = row['DIFERENÇAS']

        # Processar devoluções regulares
        devolucoes = devolucoes_pos_inventario[
            (devolucoes_pos_inventario['COD_PROD'] == cod) &
            (devolucoes_pos_inventario['LOTE'] == lote)
        ]

        # Ordenar as devoluções pela proximidade da data do inventário
        devolucoes['PROXIMIDADE'] = (devolucoes['DATA_DOC'] - data_fim).abs()
        devolucoes = devolucoes.sort_values(by='PROXIMIDADE')

        if not devolucoes.empty:
            mensagens = []
            diferenca_atual = diferenca
            for _, devolucao in devolucoes.iterrows():
                quantidade_dev = devolucao['QUANTIDADE']
                mensagens.append(f"CONSTA DEV ({-quantidade_dev})UND. NA DATA({devolucao['DATA_DOC'].date()})")
                total_devolvido = devolucoes['QUANTIDADE'].sum()
                resultado.at[index, 'QTD_DEVOLVIDA'] = total_devolvido
                diferenca_atual -= 1
                if len(mensagens) >= diferenca:
                    break

            resultado.at[index, 'infor'] = ' ; '.join(mensagens)
        else:
            resultado.at[index, 'infor'] = "Ñ CONSTA DEV., VERIFICAR SE A UTILIZAÇÃO"

        # Processar faturamentos
        faturamento_relacionado = faturamentos[
            (faturamentos['COD_PROD'] == cod) &
            (faturamentos['LOTE'] == lote) &
            (faturamentos['NOME_CLI'].isin(nomes_clientes))
        ]

        if resultado.at[index, 'infor'] == "Ñ CONSTA DEV., VERIFICAR SE A UTILIZAÇÃO":
            resultado.at[index, 'FATURADO'] = "Ñ HÁ FATURAMENTO"
        else:
            datas_devolucao = [
                pd.to_datetime(msg.split('NA DATA(')[-1].split(')')[0])
                for msg in resultado.at[index, 'infor'].split(' ; ')
            ]
            data_minima = min(datas_devolucao) if datas_devolucao else None
            
            if data_minima:
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
                resultado.at[index, 'FATURADO'] = "Ñ HÁ FATURAMENTO"

        # Processar devoluções de convênio
        devolucoes_convenio = devolucoes_venda[
            (devolucoes_venda['COD_PROD'] == cod) &
            (devolucoes_venda['LOTE'] == lote)
        ]

        if not devolucoes_convenio.empty:
            mensagens_convenio = []
            for _, dev in devolucoes_convenio.iterrows():
                mensagens_convenio.append(
                    f"DEV. NOTA FISCAL({dev['NF']}) NOTA ORIGEM({dev['NF_ORIGEM']})"
                )
            resultado.at[index, 'DEV_CONVENIO'] = ' ; '.join(mensagens_convenio)
        else:
            resultado.at[index, 'DEV_CONVENIO'] = "Ñ HÁ DEVOLUÇÃO DE CONVÊNIO"

    return resultado

# Configuração da página
st.set_page_config(
    page_title="Análise de Inventário e Faturamento",
    layout="wide",
    page_icon="assets/images/fav.svg"
)

# Logo e layout
logo = "assets/images/logo.png"
icon = "assets/images/logo.png"
st.logo(logo, icon_image=icon)

# Upload de arquivos
col1, col2 = st.columns(2)
with col1:
    upload1 = st.file_uploader("Carregue a primeira planilha (Inventário):", type=['xlsx'])

with col2:
    upload2 = st.file_uploader("Carregue a segunda planilha (Movimentos):", type=['xlsx'])

# Seleção de data e clientes
col3, col4, col5 = st.columns(3)

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

with col5:
    if upload2:
        try:
            if 'NOME_CLI' in planilha2.columns:
                convenios = st.multiselect("Selecione os convênio:", options=sorted(clientes_unicos))
            else:
                convenios = []
        except Exception as e:
            convenios = []
    else:
        convenios = []

# Botão para gerar relatório
if st.button("Gerar Relatório"):
    if upload1 and upload2 and nomes_clientes:
        try:
            planilha1 = pd.read_excel(upload1, skiprows=4)
            resultado = processar_planilhas(planilha1, planilha2, data_fim, nomes_clientes, convenios)

            # Gerar arquivo para download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                resultado.to_excel(writer, index=False, sheet_name='Relatório')
            output.seek(0)

            # Nome do arquivo de download
            nome_relatorio = f"TRATATIVA - {upload1.name}" if upload1 else "relatorio_filtrado.xlsx"

            st.success("Relatório gerado com sucesso!")
            st.download_button(
                label="Baixar Relatório",
                data=output,
                file_name=nome_relatorio,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            st.error(f"Erro ao processar os dados: {e}")
    else:
        st.warning("Por favor, carregue as duas planilhas e selecione os clientes antes de gerar o relatório.")




if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.switch_page("login.py")
# Rodapé
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
