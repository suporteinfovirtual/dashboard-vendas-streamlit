# main.py
import streamlit as st

# Configura a página principal
st.set_page_config(
    page_title="Dashboard de Gestão",
    page_icon="🏠", # Ícone de casa
    layout="wide"
)

# Título da página
st.title("Bem-vindo ao seu Painel de Gestão Integrado")
st.markdown("---")

# Mensagem de boas-vindas e instruções
st.sidebar.success("Selecione um dashboard no menu acima.")

st.markdown(
    """
    ### Navegue pelos dashboards disponíveis no menu da barra lateral à esquerda.

    - **📈 Vendas:** Análise detalhada de faturamento, custos, margens e produtos mais vendidos.
    - **💰 Financeiro:** (Em breve) Acompanhamento de fluxo de caixa, contas a pagar e a receber.

    Selecione uma das páginas para começar a sua análise.
    """
)

