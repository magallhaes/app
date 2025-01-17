import streamlit as st
import time
from credentials_manager import CredentialsManager

# Configuração da página
st.set_page_config(
    page_title="Login - Sistema de Análise de Inventário",
    layout="centered",
    page_icon="🔒"
)

# Inicializar gerenciador de credenciais
credentials_manager = CredentialsManager()

# Inicializar estado da sessão
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Estilo CSS customizado
st.markdown("""
<style>
    .login-container {
        max-width: 400px;
        margin: auto;
        padding: 20px;
    }
    .stButton>button {
        width: 100%;
        margin-top: 20px;
    }
    div[data-testid="stForm"] {
        border: 1px solid #ddd;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Container principal
with st.container():
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h1 style='text-align: center;'>Sistema de Análise de Inventário</h1>", unsafe_allow_html=True)
        
        # Formulário de login
        with st.form("login_form"):
            st.subheader("Login")
            username = st.text_input("Usuário")
            password = st.text_input("Senha", type="password")
            submit_button = st.form_submit_button("Entrar")

            if submit_button:
                if credentials_manager.verify_credentials(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    user_info = credentials_manager.get_user_info(username)
                    st.session_state.user_name = user_info.get('name', username)
                    st.success("Login realizado com sucesso!")
                    time.sleep(1)
                    st.switch_page("pages/main.py")
                else:
                    st.error("Usuário ou senha incorretos!")

# Rodapé
st.markdown("""
<div style='position: fixed; bottom: 0; width: 100%; text-align: center; padding: 10px; background-color: #f0f2f6;'>
    Desenvolvido por Leonardo Magalhães - © 2025
</div>
""", unsafe_allow_html=True)