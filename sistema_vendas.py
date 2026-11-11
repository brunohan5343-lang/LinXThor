import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
import os
import json
import requests
from openai import OpenAI

st.set_page_config(
    page_title="Sistema LinXThor",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
        padding-top: 1rem;
    }
    
    [data-testid="stSidebar"] h2 {
        font-size: 1.15rem;
        font-weight: 700;
        color: #1e293b;
        letter-spacing: -0.025em;
        margin-bottom: 0.5rem;
    }
    
    [data-testid="stSidebar"] h3 {
        font-size: 1rem;
        font-weight: 600;
        color: #475569;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }

    .stSelectbox, .stDateInput, .stNumberInput, .stTextInput {
        margin-bottom: 0.5rem;
    }

    .stButton button {
        width: 100%;
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        border: none;
        box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2);
        transition: all 0.2s ease-in-out;
    }
    
    .stButton button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
        box-shadow: 0 6px 8px -1px rgba(59, 130, 246, 0.3);
        transform: translateY(-1px);
    }

    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 1rem 1.25rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
    }
    
    [data-testid="stMetricValue"] {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0f172a;
    }
    </style>
""", unsafe_allow_html=True)

APPS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxd6a2c1LMPGZLNP-7GqqvarGgc2gKobj_jQuYQVmG9fmtY-x_NCSa7SYt8qxGbL0m8ng/exec'

# --- FUNÇÕES DE CARREGAMENTO E SALVAMENTO COM CACHE (SESSION STATE) ---

def buscar_dados_nuvem():
    """Busca os dados diretamente no Google Drive via Apps Script."""
    try:
        response = requests.get(f"{APPS_SCRIPT_URL}?action=ler", timeout=15)
        if response.text.strip().startswith("<") or response.status_code != 200:
            return None, None, None
            
        dados = response.json()
        if dados.get("status") == "erro":
            return None, None, None

        # Vendas
        raw_vendas = dados.get('vendas', [])
        if len(raw_vendas) > 1:
            tabela = pd.DataFrame(raw_vendas[1:], columns=raw_vendas[0])
            if 'Unnamed: 0' in tabela.columns:
                tabela = tabela.drop(columns=['Unnamed: 0'])
            if '' in tabela.columns:
                tabela = tabela.drop(columns=[''])
            
            # Limpa o formato de data caso venha com horário ISO
            if 'data' in tabela.columns:
                tabela['data'] = pd.to_datetime(tabela['data'], errors='coerce').dt.strftime('%Y-%m-%d').fillna(tabela['data'].astype(str))
        else:
            tabela = pd.DataFrame(columns=['data', 'vendedor', 'produto', 'quantidade', 'valor'])
            
        # Vendedores
        raw_vend = dados.get('vendedores', [])
        if len(raw_vend) > 1:
            df_v = pd.DataFrame(raw_vend[1:], columns=raw_vend[0])
            vendedores = df_v['vendedor'].astype(str).tolist() if 'vendedor' in df_v.columns else ['Bárbara', 'Bruno', 'Vitor', 'Juninho']
        else:
            vendedores = ['Bárbara', 'Bruno', 'Vitor', 'Juninho']
            
        # Produtos
        raw_prod = dados.get('produtos', [])
        if len(raw_prod) > 1:
            df_p = pd.DataFrame(raw_prod[1:], columns=raw_prod[0])
            produtos = df_p['produto'].astype(str).tolist() if 'produto' in df_p.columns else ['Notebook', 'Celular', 'Fone']
        else:
            produtos = ['Notebook', 'Celular', 'Fone']
            
        return tabela, vendedores, produtos
    except Exception:
        return None, None, None

if 'tabela_cache' not in st.session_state:
    with st.spinner("🔄 Conectando ao Google Drive e carregando dados..."):
        tab, vend, prod = buscar_dados_nuvem()
        if tab is not None:
            st.session_state['tabela_cache'] = tab
            st.session_state['vendedores_cache'] = vend
            st.session_state['produtos_cache'] = prod
        else:
            st.session_state['tabela_cache'] = pd.DataFrame(columns=['data', 'vendedor', 'produto', 'quantidade', 'valor'])
            st.session_state['vendedores_cache'] = ['Bárbara', 'Bruno', 'Vitor', 'Juninho']
            st.session_state['produtos_cache'] = ['Notebook', 'Celular', 'Fone']

tabela = st.session_state['tabela_cache']
vendedores_cadastrados = st.session_state['vendedores_cache']
produtos_cadastrados = st.session_state['produtos_cache']

def salvar_tudo(tabela_atual, vendedores_atuais, produtos_atuais):
    st.session_state['tabela_cache'] = tabela_atual
    st.session_state['vendedores_cache'] = vendedores_atuais
    st.session_state['produtos_cache'] = produtos_atuais
    
    tabela_limpa = tabela_atual.copy()
    if 'Unnamed: 0' in tabela_limpa.columns:
        tabela_limpa = tabela_limpa.drop(columns=['Unnamed: 0'])
    if '' in tabela_limpa.columns:
        tabela_limpa = tabela_limpa.drop(columns=[''])
        
    payload = {
        "vendas": [tabela_limpa.columns.tolist()] + tabela_limpa.values.tolist(),
        "vendedores": [["vendedor"]] + [[v] for v in vendedores_atuais],
        "produtos": [["produto"]] + [[p] for p in produtos_atuais]
    }
    
    try:
        requests.post(APPS_SCRIPT_URL, json=payload, timeout=15)
    except Exception:
        pass

# --- FUNÇÕES DE MANIPULAÇÃO E CONSULTA PARA O CHATBOT (TOOLS) ---

def consultar_dados(filtro_vendedor=None, filtro_produto=None, filtro_data=None):
    """Consulta as vendas cadastradas aplicando filtros opcionais para responder a perguntas analíticas."""
    global tabela
    if tabela.empty:
        return "Não há vendas cadastradas no momento."
    
    df = tabela.copy()
    if filtro_vendedor:
        df = df[df['vendedor'].str.contains(filtro_vendedor, case=False, na=False)]
    if filtro_produto:
        df = df[df['produto'].str.contains(filtro_produto, case=False, na=False)]
    if filtro_data:
        df = df[df['data'].astype(str) == str(filtro_data)]
        
    if df.empty:
        df = tabela 
        
    if 'data' in df.columns:
        df['data'] = df['data'].astype(str)
        
    total_vendas = len(df)
    valor_total = float(df['valor'].sum()) if not df.empty else 0.0
    
    resumo = {
        "total_registros_encontrados": total_vendas,
        "valor_total_acumulado": f"R$ {valor_total:,.2f}",
        "detalhes_das_vendas": df.to_dict(orient="records")
    }
    return json.dumps(resumo, ensure_ascii=False, default=str)

def cadastrar_venda(data, vendedor, produto, quantidade, valor):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    data_formatada = pd.to_datetime(data).strftime('%Y-%m-%d') if pd.notna(data) else str(data)
    nova_venda = pd.DataFrame([[data_formatada, vendedor, produto, int(quantidade), float(valor)]], columns=['data', 'vendedor', 'produto', 'quantidade', 'valor'])
    tabela = pd.concat([tabela, nova_venda], ignore_index=True)
    salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
    return f"Venda cadastrada com sucesso: {quantidade}x {produto} por {vendedor} em {data_formatada} (Valor: R$ {valor})."

def editar_venda(indice, data, vendedor, produto, quantidade, valor):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if indice in tabela.index:
        data_formatada = pd.to_datetime(data).strftime('%Y-%m-%d') if pd.notna(data) else str(data)
        tabela.loc[indice] = [data_formatada, vendedor, produto, int(quantidade), float(valor)]
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Venda de índice {indice} atualizada com sucesso."
    return f"Erro: Índice de venda {indice} não encontrado."

def excluir_venda(indice):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if indice in tabela.index:
        tabela = tabela.drop(indice).reset_index(drop=True)
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Venda de índice {indice} excluída com sucesso."
    return f"Erro: Índice de venda {indice} não encontrado."

def adicionar_vendedor(nome):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if nome.strip() != '' and nome not in vendedores_cadastrados:
        vendedores_cadastrados.append(nome)
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Vendedor(a) '{nome}' adicionado(a) com sucesso."
    return "Erro: Nome inválido ou já cadastrado."

def editar_vendedor(nome_antigo, novo_nome):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if nome_antigo in vendedores_cadastrados and novo_nome.strip() != '':
        idx = vendedores_cadastrados.index(nome_antigo)
        vendedores_cadastrados[idx] = novo_nome
        if not tabela.empty:
            tabela.loc[tabela['vendedor'] == nome_antigo, 'vendedor'] = novo_nome
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Vendedor(a) '{nome_antigo}' alterado(a) para '{novo_nome}' com sucesso."
    return "Erro: Vendedor não encontrado ou novo nome vazio."

def excluir_vendedor(nome):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if len(vendedores_cadastrados) > 1 and nome in vendedores_cadastrados:
        vendedores_cadastrados.remove(nome)
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Vendedor(a) '{nome}' excluído(a) com sucesso."
    return "Erro: Não é possível excluir (deve manter pelo menos um vendedor ou nome não encontrado)."

def adicionar_produto(nome):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if nome.strip() != '' and nome not in produtos_cadastrados:
        produtos_cadastrados.append(nome)
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Produto '{nome}' adicionado com sucesso."
    return "Erro: Nome inválido ou produto já cadastrado."

def editar_produto(nome_antigo, novo_nome):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if nome_antigo in produtos_cadastrados and novo_nome.strip() != '':
        idx = produtos_cadastrados.index(nome_antigo)
        produtos_cadastrados[idx] = novo_nome
        if not tabela.empty:
            tabela.loc[tabela['produto'] == nome_antigo, 'produto'] = novo_nome
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Produto '{nome_antigo}' alterado para '{novo_nome}' com sucesso."
    return "Erro: Produto não encontrado ou novo nome vazio."

def excluir_produto(nome):
    global tabela, vendedores_cadastrados, produtos_cadastrados
    if len(produtos_cadastrados) > 1 and nome in produtos_cadastrados:
        produtos_cadastrados.remove(nome)
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        return f"Produto '{nome}' excluído com sucesso."
    return "Erro: Não é possível excluir (deve manter pelo menos um produto ou nome não encontrado)."

funcoes_disponiveis = {
    "consultar_dados": consultar_dados,
    "cadastrar_venda": cadastrar_venda,
    "editar_venda": editar_venda,
    "excluir_venda": excluir_venda,
    "adicionar_vendedor": adicionar_vendedor,
    "editar_vendedor": editar_vendedor,
    "excluir_vendedor": excluir_vendedor,
    "adicionar_produto": adicionar_produto,
    "editar_produto": editar_produto,
    "excluir_produto": excluir_produto,
}

declaracao_ferramentas = [
    {
        "type": "function",
        "function": {
            "name": "consultar_dados",
            "description": "Consulta o banco de dados de vendas aplicando filtros por vendedor, produto ou data para responder a perguntas analíticas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filtro_vendedor": {"type": "string", "description": "Filtrar por nome específico do vendedor (opcional)"},
                    "filtro_produto": {"type": "string", "description": "Filtrar por nome específico do produto (opcional)"},
                    "filtro_data": {"type": "string", "description": "Filtrar por data exata no formato AAAA-MM-DD (opcional)"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "cadastrar_venda",
            "description": "Cadastra uma nova venda no sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data": {"type": "string", "description": "Data no formato AAAA-MM-DD"},
                    "vendedor": {"type": "string", "description": f"Nome do vendedor. Opções válidas: {vendedores_cadastrados}"},
                    "produto": {"type": "string", "description": f"Nome do produto. Opções válidas: {produtos_cadastrados}"},
                    "quantidade": {"type": "integer", "description": "Quantidade vendida"},
                    "valor": {"type": "number", "description": "Valor total da venda em Reais"}
                },
                "required": ["data", "vendedor", "produto", "quantidade", "valor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "editar_venda",
            "description": "Edita uma venda existente informando o índice da tabela.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indice": {"type": "integer", "description": "Índice numérico da linha da venda"},
                    "data": {"type": "string", "description": "Nova data (AAAA-MM-DD)"},
                    "vendedor": {"type": "string", "description": "Novo vendedor"},
                    "produto": {"type": "string", "description": "Novo produto"},
                    "quantidade": {"type": "integer", "description": "Nova quantidade"},
                    "valor": {"type": "number", "description": "Novo valor"}
                },
                "required": ["indice", "data", "vendedor", "produto", "quantidade", "valor"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "excluir_venda",
            "description": "Exclui uma venda pelo seu índice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "indice": {"type": "integer", "description": "Índice da venda a ser excluída"}
                },
                "required": ["indice"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adicionar_vendedor",
            "description": "Adiciona um novo vendedor ao sistema.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do novo vendedor"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "editar_vendedor",
            "description": "Altera o nome de um vendedor existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_antigo": {"type": "string", "description": "Nome atual do vendedor"},
                    "novo_nome": {"type": "string", "description": "Novo nome para o vendedor"}
                },
                "required": ["nome_antigo", "novo_nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "excluir_vendedor",
            "description": "Exclui um vendedor cadastrado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do vendedor a excluir"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adicionar_produto",
            "description": "Adiciona um novo produto ao catálogo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do produto"}
                },
                "required": ["nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "editar_produto",
            "description": "Altera o nome de um produto existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_antigo": {"type": "string", "description": "Nome atual do produto"},
                    "novo_nome": {"type": "string", "description": "Novo nome do produto"}
                },
                "required": ["nome_antigo", "novo_nome"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "excluir_produto",
            "description": "Exclui um produto do catálogo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {"type": "string", "description": "Nome do produto a excluir"}
                },
                "required": ["nome"]
            }
        }
    }
]

# --- LAYOUT PRINCIPAL ---

col_logo, col_titulo = st.columns([1, 4])

with col_logo:
    if os.path.exists('imagem.jpg'):
        img_capa = Image.open('imagem.jpg')
        st.image(img_capa, width=160)

with col_titulo:
    st.markdown('# 🛡️ Sistema LinXThor')
    st.markdown('_LinXThor é a perspicácia do lince, que enxerga longe, e a força inabalável do Thor, que juntos sustentam seu negócio rumo ao topo._')

st.write('---')

# --- SIDEBAR ORIGINAL COMPLETA ---

st.sidebar.markdown("### ⚙️ Painel de Controle (Manual)")
st.sidebar.markdown("---")

if st.sidebar.button("🔄 Sincronizar com o Google Drive"):
    with st.spinner("Atualizando com a nuvem..."):
        tab, vend, prod = buscar_dados_nuvem()
        if tab is not None:
            st.session_state['tabela_cache'] = tab
            st.session_state['vendedores_cache'] = vend
            st.session_state['produtos_cache'] = prod
            st.success("Dados sincronizados com sucesso!")
            st.rerun()
        else:
            st.error("Erro ao sincronizar com a nuvem.")

st.sidebar.markdown("---")

modulo = st.sidebar.selectbox('Escolha o módulo', ['Venda', 'Vendedor', 'Produto'])

if modulo == 'Venda':
    acao = st.sidebar.selectbox('Escolha a ação', ['Cadastrar', 'Editar', 'Excluir'])
elif modulo == 'Vendedor':
    acao = st.sidebar.selectbox('Escolha a ação', ['Adicionar', 'Editar', 'Excluir'])
else:
    acao = st.sidebar.selectbox('Escolha a ação', ['Adicionar', 'Editar', 'Excluir'])

st.sidebar.markdown("---")

if modulo == 'Venda' and acao == 'Cadastrar':
    st.sidebar.subheader('✨ Nova Venda')
    data = st.sidebar.date_input('Data')
    vendedor = st.sidebar.selectbox('Vendedores(as)', vendedores_cadastrados, key='cad_vendedor')
    produto = st.sidebar.selectbox('Produtos', produtos_cadastrados, key='cad_produto')
    quantidade = st.sidebar.number_input('Quantidade', step=1, key='cad_qtd')
    valor = st.sidebar.number_input('Valor (R$)', key='cad_val')
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    botao_cadastrar = st.sidebar.button('Cadastrar nova venda')

    if botao_cadastrar:
        data_formatada = pd.to_datetime(data).strftime('%Y-%m-%d')
        nova_venda = pd.DataFrame([[data_formatada, vendedor, produto, quantidade, valor]], columns=['data', 'vendedor', 'produto', 'quantidade', 'valor'])
        tabela = pd.concat([tabela, nova_venda], ignore_index=True)
        salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
        st.success('Venda cadastrada com sucesso!')
        st.rerun()

elif modulo == 'Venda' and acao == 'Editar':
    st.sidebar.subheader('✏️ Editar Venda')
    if not tabela.empty:
        indice_edicao = st.sidebar.selectbox('Selecione o índice da venda', tabela.index)
        
        venda_atual = tabela.loc[indice_edicao]
        data_atual = pd.to_datetime(venda_atual['data']).date() if pd.notna(venda_atual['data']) else None
        
        novo_data = st.sidebar.date_input('Data', value=data_atual, key='edit_data')
        
        idx_vend = vendedores_cadastrados.index(venda_atual['vendedor']) if venda_atual['vendedor'] in vendedores_cadastrados else 0
        novo_vendedor = st.sidebar.selectbox('Vendedores(as)', vendedores_cadastrados, index=idx_vend, key='edit_vendedor')
        
        idx_prod = produtos_cadastrados.index(venda_atual['produto']) if venda_atual['produto'] in produtos_cadastrados else 0
        novo_produto = st.sidebar.selectbox('Produtos', produtos_cadastrados, index=idx_prod, key='edit_produto')
        
        nova_quantidade = st.sidebar.number_input('Quantidade', value=int(venda_atual['quantidade']), step=1, key='edit_qtd')
        novo_valor = st.sidebar.number_input('Valor (R$)', value=float(venda_atual['valor']), key='edit_val')
        
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        botao_editar = st.sidebar.button('Salvar Alterações')

        if botao_editar:
            data_formatada = pd.to_datetime(novo_data).strftime('%Y-%m-%d')
            tabela.loc[indice_edicao] = [data_formatada, novo_vendedor, novo_produto, nova_quantidade, novo_valor]
            salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
            st.success('Venda atualizada com sucesso!')
            st.rerun()
    else:
        st.sidebar.warning('Não há vendas cadastradas para editar.')

elif modulo == 'Venda' and acao == 'Excluir':
    st.sidebar.subheader('🗑️ Excluir Venda')
    if not tabela.empty:
        indice_exclusao = st.sidebar.selectbox('Selecione o índice da venda para excluir', tabela.index)
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        botao_excluir = st.sidebar.button('Excluir Venda selecionada')

        if botao_excluir:
            tabela = tabela.drop(indice_exclusao).reset_index(drop=True)
            salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
            st.success('Venda excluída com sucesso!')
            st.rerun()
    else:
        st.sidebar.warning('Não há vendas cadastradas para excluir.')

elif modulo == 'Vendedor' and acao == 'Adicionar':
    st.sidebar.subheader('👤 Novo Vendedor(a)')
    novo_vend = st.sidebar.text_input('Nome do(a) Vendedor(a)')
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    botao_add_vend = st.sidebar.button('Adicionar Vendedor')

    if botao_add_vend:
        if novo_vend.strip() != '':
            if novo_vend not in vendedores_cadastrados:
                vendedores_cadastrados.append(novo_vend)
                salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
                st.success(f'Vendedor(a) "{novo_vend}" adicionado(a) com sucesso!')
                st.rerun()
            else:
                st.sidebar.error('Este vendedor já está cadastrado.')
        else:
            st.sidebar.warning('Digite um nome válido.')

elif modulo == 'Vendedor' and acao == 'Editar':
    st.sidebar.subheader('✏️ Editar Vendedor(a)')
    if vendedores_cadastrados:
        vend_selecionado = st.sidebar.selectbox('Selecione o vendedor para editar', vendedores_cadastrados)
        novo_nome_vend = st.sidebar.text_input('Novo nome', value=vend_selecionado)
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        botao_salvar_vend = st.sidebar.button('Salvar Alteração')

        if botao_salvar_vend:
            if novo_nome_vend.strip() != '':
                idx = vendedores_cadastrados.index(vend_selecionado)
                vendedores_cadastrados[idx] = novo_nome_vend
                
                if not tabela.empty:
                    tabela.loc[tabela['vendedor'] == vend_selecionado, 'vendedor'] = novo_nome_vend

                salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
                st.success('Vendedor atualizado com sucesso!')
                st.rerun()
            else:
                st.sidebar.warning('O nome não pode estar vazio.')
    else:
        st.sidebar.warning('Não há vendedores cadastrados.')

elif modulo == 'Vendedor' and acao == 'Excluir':
    st.sidebar.subheader('🗑️ Excluir Vendedor(a)')
    if vendedores_cadastrados:
        vend_para_deletar = st.sidebar.selectbox('Selecione o vendedor para excluir', vendedores_cadastrados)
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        botao_del_vend = st.sidebar.button('Excluir Vendedor')

        if botao_del_vend:
            if len(vendedores_cadastrados) > 1:
                vendedores_cadastrados.remove(vend_para_deletar)
                salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
                st.success(f'Vendedor(a) "{vend_para_deletar}" removido(a)!')
                st.rerun()
            else:
                st.sidebar.error('Você deve manter pelo menos um vendedor cadastrado.')
    else:
        st.sidebar.warning('Não há vendedores cadastrados.')

elif modulo == 'Produto' and acao == 'Adicionar':
    st.sidebar.subheader('📦 Novo Produto')
    novo_prod = st.sidebar.text_input('Nome do Produto')
    st.sidebar.markdown("<br>", unsafe_allow_html=True)
    botao_add_prod = st.sidebar.button('Adicionar Produto')

    if botao_add_prod:
        if novo_prod.strip() != '':
            if novo_prod not in produtos_cadastrados:
                produtos_cadastrados.append(novo_prod)
                salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
                st.success(f'Produto "{novo_prod}" adicionado com sucesso!')
                st.rerun()
            else:
                st.sidebar.error('Este produto já está cadastrado.')
        else:
            st.sidebar.warning('Digite um nome válido.')

elif modulo == 'Produto' and acao == 'Editar':
    st.sidebar.subheader('✏️ Editar Produto')
    if produtos_cadastrados:
        prod_selecionado = st.sidebar.selectbox('Selecione o produto para editar', produtos_cadastrados)
        novo_nome_prod = st.sidebar.text_input('Novo nome do produto', value=prod_selecionado)
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        botao_salvar_prod = st.sidebar.button('Salvar Alteração de Produto')

        if botao_salvar_prod:
            if novo_nome_prod.strip() != '':
                idx = produtos_cadastrados.index(prod_selecionado)
                produtos_cadastrados[idx] = novo_nome_prod
                
                if not tabela.empty:
                    tabela.loc[tabela['produto'] == prod_selecionado, 'produto'] = novo_nome_prod

                salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
                st.success('Produto atualizado com sucesso!')
                st.rerun()
            else:
                st.sidebar.warning('O nome não pode estar vazio.')
    else:
        st.sidebar.warning('Não há produtos cadastrados.')

elif modulo == 'Produto' and acao == 'Excluir':
    st.sidebar.subheader('🗑️ Excluir Produto')
    if produtos_cadastrados:
        prod_para_deletar = st.sidebar.selectbox('Selecione o produto para excluir', produtos_cadastrados)
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        botao_del_prod = st.sidebar.button('Excluir Produto')

        if botao_del_prod:
            if len(produtos_cadastrados) > 1:
                produtos_cadastrados.remove(prod_para_deletar)
                salvar_tudo(tabela, vendedores_cadastrados, produtos_cadastrados)
                st.success(f'Produto "{prod_para_deletar}" removido!')
                st.rerun()
            else:
                st.sidebar.error('Você deve manter pelo menos um produto cadastrado.')
    else:
        st.sidebar.warning('Não há produtos cadastrados.')


# --- ADIÇÃO DO CHATBOT INTELIGENTE ABAIXO DO PAINEL MANUAL ---

st.sidebar.markdown("---")
st.sidebar.markdown("### 🤖 Assistente de IA (Chat)")
st.sidebar.markdown("Fale com o assistente para operar o sistema por voz/texto ou consultar relatórios.")

api_key_gemini = os.getenv("GEMINI_API_KEY")
if "GEMINI_API_KEY" in st.secrets:
    api_key_gemini = st.secrets["GEMINI_API_KEY"]

cliente_ia = OpenAI(
    api_key=api_key_gemini, 
    base_url='https://generativelanguage.googleapis.com/v1beta/openai/'
)

if 'lista_mensagens' not in st.session_state:
    st.session_state['lista_mensagens'] = [
        {
            "role": "system", 
            "content": f"Você é o assistente inteligente do sistema LinXThor. Vendedores atuais: {vendedores_cadastrados}. Produtos atuais: {produtos_cadastrados}. Vendas atuais cadastradas (índices): {list(tabela.index) if not tabela.empty else 'Nenhuma'}. Sempre que o usuário fizer perguntas analíticas sobre relatórios, faturamento, quantidade de vendas, desempenho de vendedores ou produtos, utilize a ferramenta 'consultar_dados' para buscar as informações reais antes de responder."
        }
    ]

for mensagem in st.session_state['lista_mensagens']:
    if isinstance(mensagem, dict):
        role = mensagem.get('role')
        content = mensagem.get('content')
        if role in ['user', 'assistant'] and content:
            with st.sidebar.chat_message(role):
                st.sidebar.write(content)

mensagem_usuario = st.sidebar.chat_input('Digite seu comando ou pergunta para a IA...')

if mensagem_usuario:
    st.session_state['lista_mensagens'].append({'role': 'user', 'content': mensagem_usuario})
    with st.sidebar.chat_message('user'):
        st.sidebar.write(mensagem_usuario)

    resposta_modelo = cliente_ia.chat.completions.create(
        messages=st.session_state['lista_mensagens'],
        model='gemini-flash-lite-latest',
        tools=declaracao_ferramentas,
        tool_choice="auto"
    )

    mensagem_resposta = resposta_modelo.choices[0].message
    
    if mensagem_resposta.tool_calls:
        st.session_state['lista_mensagens'].append(mensagem_resposta)
        
        for tool_call in mensagem_resposta.tool_calls:
            nome_funcao = tool_call.function.name
            argumentos = json.loads(tool_call.function.arguments)
            
            if nome_funcao in funcoes_disponiveis:
                resultado_funcao = funcoes_disponiveis[nome_funcao](**argumentos)
                
                st.session_state['lista_mensagens'].append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": nome_funcao,
                    "content": str(resultado_funcao)
                })

        segunda_resposta = cliente_ia.chat.completions.create(
            messages=st.session_state['lista_mensagens'],
            model='gemini-flash-lite-latest'
        )
        
        resposta_ia = segunda_resposta.choices[0].message.content
        st.session_state['lista_mensagens'].append({'role': 'assistant', 'content': resposta_ia})
        
        with st.sidebar.chat_message('assistant'):
            st.sidebar.write(resposta_ia)
            
        st.rerun()

    else:
        resposta_ia = mensagem_resposta.content
        if resposta_ia:
            st.session_state['lista_mensagens'].append({'role': 'assistant', 'content': resposta_ia})
            with st.sidebar.chat_message('assistant'):
                st.sidebar.write(resposta_ia)


# --- CORPO PRINCIPAL DO SISTEMA (Tabelas e Gráficos) ---

st.write('## 📋 Vendas Cadastradas')
st.dataframe(tabela, use_container_width=True)

st.write('## 📈 Dashboard')

if not tabela.empty:
    soma = tabela['valor'].sum()
    soma_formatada = f'{soma:,.2f}'.replace(',', 'x').replace('.', ',').replace('x', '.')
    st.metric('Faturamento Total', f'R$ {soma_formatada}')

    st.write('### Faturamento por Vendedor')

    fat_vendedor = tabela.groupby('vendedor')['valor'].sum().reset_index()
    fat_vendedor = fat_vendedor.sort_values(by='valor', ascending=False).reset_index(drop=True)

    fat_vendedor.insert(0, 'Colocação', [f'{i+1}º lugar' for i in range(len(fat_vendedor))])

    fat_vendedor['valor'] = fat_vendedor['valor'].apply(
        lambda x: f'R$ {x:,.2f}'.replace(',', 'x').replace('.', ',').replace('x', '.'))

    fat_vendedor.columns = ['Colocação', 'Vendedor(a)', 'Faturamento Total']

    st.dataframe(fat_vendedor, hide_index=True, use_container_width=True)

    col_graf1, col_graf2 = st.columns(2)
    with col_graf1:
        grafico1 = px.bar(tabela, x='vendedor', y='valor', color='produto', title="Faturamento por Vendedor e Produto")
        st.plotly_chart(grafico1, use_container_width=True)

    with col_graf2:
        grafico2 = px.pie(tabela, names='produto', values='valor', hole=0.5, title="Participação por Produto")
        st.plotly_chart(grafico2, use_container_width=True)
else:
    st.info('Cadastre sua primeira venda para visualizar o dashboard.')
