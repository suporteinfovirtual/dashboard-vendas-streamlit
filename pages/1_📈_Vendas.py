# dashboard_com_custo.py
import streamlit as st
import pandas as pd
import psycopg2
import locale
from datetime import date, timedelta

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Vendas com Custos",
    page_icon="🚀",
    layout="wide"
)

# --- 2. CONFIGURAÇÃO DE LOCALIZAÇÃO ---
try:
    locale.setlocale(locale.LC_TIME, "pt_BR.utf8")
except:
    try:
        locale.setlocale(locale.LC_TIME, "Portuguese_Brazil.1252")  # Windows
    except:
        pass  # fallback


# --- 3. CONEXÃO COM O POSTGRESQL ---
@st.cache_resource
def init_connection():
    try:
        # A linha abaixo é a única mudança.
        # Ela busca as credenciais do arquivo de segredos do Streamlit.
        conn = psycopg2.connect(**st.secrets["postgres"])
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Erro de conexão com o PostgreSQL: {e}")
        return None


conn = init_connection()
if conn is None:
    st.stop()


# --- 4. FUNÇÕES DE BUSCA DE DADOS ---
@st.cache_data(ttl=60)
def get_dynamic_models(start_date, end_date):
    query = "SELECT DISTINCT modelo FROM vendas_itens_view WHERE emissao BETWEEN %s AND %s"
    with conn.cursor() as cur:
        cur.execute(query, (start_date, end_date))
        models = [row[0] for row in cur.fetchall()]
    return ['Todos'] + sorted(models)


def run_query(query, params=None):
    try:
        df = pd.read_sql(query, conn, params=params)
        df['emissao'] = pd.to_datetime(df['emissao'], errors='coerce')
        df['total'] = pd.to_numeric(df['total'], errors='coerce')
        df.dropna(subset=['emissao', 'total', 'documento'], inplace=True)
        return df
    except Exception as e:
        st.error(f"Erro ao executar a consulta: {e}")
        return pd.DataFrame()


# --- 5. FUNÇÃO PARA APLICAR CORES CONDICIONAIS ---
def color_margem(val):
    """
    Aplica cor verde para valores positivos e vermelho para valores negativos
    """
    try:
        # Remove o símbolo % e converte para float
        num_val = float(val.replace('%', ''))
        if num_val > 0:
            return 'color: green; font-weight: bold'
        elif num_val < 0:
            return 'color: red; font-weight: bold'
        else:
            return 'color: gray'
    except:
        return ''


# --- 6. BARRA LATERAL DE FILTROS ---
st.sidebar.header("Filtros")
hoje = date.today()
data_inicio = st.sidebar.date_input("Data de Início", value=hoje, format="DD/MM/YYYY")
data_fim = st.sidebar.date_input("Data de Fim", value=hoje, format="DD/MM/YYYY")

try:
    with st.spinner("Buscando opções de filtro..."):
        opcoes_modelo_dinamicas = get_dynamic_models(data_inicio, data_fim)
except Exception as e:
    st.sidebar.error("Não foi possível carregar os modelos de nota.")
    opcoes_modelo_dinamicas = ['Todos']

modelo_selecionado = st.sidebar.selectbox(
    "Selecione o Modelo",
    options=opcoes_modelo_dinamicas,
    help="Os modelos são carregados com base no período de datas selecionado."
)

# --- 7. LÓGICA PRINCIPAL E QUERY ---
st.title("🚀 Dashboard de Vendas com Custos e Margem")

query = """
SELECT v.modelo, v.emissao, v.produto, v.descricao, v.quantidade, v.total, v.documento,
       p.precoultimacompra AS custo_unitario,
       COALESCE(p.precoultimacompra,0) * v.quantidade AS total_custo,
       v.total - COALESCE(p.precoultimacompra,0) * v.quantidade AS lucro,
       CASE WHEN v.total != 0 THEN
            (v.total - COALESCE(p.precoultimacompra,0) * v.quantidade)/v.total * 100
       ELSE 0 END AS margem_sobre_venda,
       CASE WHEN COALESCE(p.precoultimacompra,0) != 0 THEN
            (v.total - COALESCE(p.precoultimacompra,0) * v.quantidade)/COALESCE(p.precoultimacompra,0) * 100
       ELSE 0 END AS margem_sobre_custo
FROM vendas_itens_view v
LEFT JOIN produto p ON p.codigo = v.produto
WHERE 1=1
"""

params = []
if modelo_selecionado != 'Todos':
    query += " AND v.modelo = %s"
    params.append(modelo_selecionado)

query += " AND v.emissao BETWEEN %s AND %s"
params.append(data_inicio)
params.append(data_fim)

df_filtrado = run_query(query, params)

# --- 8. EXIBIÇÃO DOS RESULTADOS ---
if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    total_vendas = df_filtrado['total'].sum()
    total_custo = df_filtrado['total_custo'].sum()
    lucro_total = df_filtrado['lucro'].sum()
    margem_venda = (lucro_total / total_vendas * 100) if total_vendas else 0
    margem_custo = (lucro_total / total_custo * 100) if total_custo else 0
    quantidade_itens_total = df_filtrado['quantidade'].sum()
    numero_vendas_unicas = df_filtrado['documento'].nunique()
    ticket_medio = total_vendas / numero_vendas_unicas if numero_vendas_unicas > 0 else 0
    itens_por_venda = quantidade_itens_total / numero_vendas_unicas if numero_vendas_unicas > 0 else 0

    # --- Métricas principais ---
    col1, col2, col3, col4, col5, col6, col7 = st.columns(7)
    col1.metric("Faturamento Total", f"R$ {total_vendas:,.2f}")
    col2.metric("Total de Custo", f"R$ {total_custo:,.2f}")
    col3.metric("Lucro Total", f"R$ {lucro_total:,.2f}")
    col4.metric("Margem sobre Venda", f"{margem_venda:.2f}%")
    col5.metric("Margem sobre Custo", f"{margem_custo:.2f}%")
    col6.metric("Ticket Médio (R$)", f"R$ {ticket_medio:,.2f}")
    col7.metric("Itens por Venda", f"{itens_por_venda:.2f}")

    st.markdown("---")

    # --- Vendas por Dia ---
    st.subheader("📊 Vendas por Dia")
    vendas_por_dia = df_filtrado.groupby(df_filtrado['emissao'].dt.date)['total'].sum().reset_index()
    vendas_por_dia.columns = ['Data', 'Total']
    vendas_por_dia['Data'] = pd.to_datetime(vendas_por_dia['Data'])

    idx = pd.date_range(start=data_inicio, end=data_fim, freq='D')
    df_completo = pd.DataFrame(idx, columns=['Data'])
    df_grafico = pd.merge(df_completo, vendas_por_dia, on='Data', how='left').fillna(0)
    df_grafico['Data Formatada'] = df_grafico['Data'].dt.strftime('%d/%m')
    st.bar_chart(df_grafico.set_index('Data Formatada'), y='Total')

    st.markdown("---")

    # --- Ranking de Produtos ---
    st.subheader("🏆 Ranking de Produtos Mais Vendidos")
    ranking_produtos = df_filtrado.groupby(['produto', 'descricao']).agg(
        Quantidade=('quantidade', 'sum'),
        Valor_Total=('total', 'sum'),
        Custo_Total=('total_custo', 'sum'),
        Lucro=('lucro', 'sum'),
        Margem_sobre_Venda=('margem_sobre_venda', 'mean'),
        Margem_sobre_Custo=('margem_sobre_custo', 'mean')
    ).reset_index()

    # Ordena por Quantidade vendida
    ranking_produtos = ranking_produtos.sort_values(by='Quantidade', ascending=False)

    # Formatação
    ranking_produtos['Valor_Total'] = ranking_produtos['Valor_Total'].map('R$ {:,.2f}'.format)
    ranking_produtos['Custo_Total'] = ranking_produtos['Custo_Total'].map('R$ {:,.2f}'.format)
    ranking_produtos['Lucro'] = ranking_produtos['Lucro'].map('R$ {:,.2f}'.format)
    ranking_produtos['Margem_sobre_Venda'] = ranking_produtos['Margem_sobre_Venda'].map('{:.2f}%'.format)
    ranking_produtos['Margem_sobre_Custo'] = ranking_produtos['Margem_sobre_Custo'].map('{:.2f}%'.format)

    ranking_produtos.columns = ['Código', 'Descrição', 'Qtd. Vendida', 'Valor Total', 'Custo Total', 'Lucro',
                                'Margem Venda', 'Margem Custo']

    # Aplicar formatação condicional nas colunas de margem
    styled_df = ranking_produtos.set_index('Código').style.applymap(
        color_margem,
        subset=['Margem Venda', 'Margem Custo']
    )

    st.dataframe(styled_df)

