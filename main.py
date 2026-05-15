import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import html
import re

# --- CONFIGURAÇÕES ---
BASE_URL = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"

def buscar_produtos_nagumo(termo, total_itens=40):
    todos_produtos = []
    itens_por_pagina = 20
    
    # Headers para simular um navegador e evitar bloqueios
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    for start in range(0, total_itens, itens_por_pagina):
        params = {
            'q': termo,
            'start': start,
            'sz': itens_por_pagina,
            'srule': 'Relevance'
        }
        
        try:
            # Correção do atributo status_code
            response = requests.get(BASE_URL, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # O Nagumo retorna um fragmento de HTML que contém a tag <search-card-grid>
                # Usamos Regex para extrair o conteúdo do atributo 'products' que é um JSON gigante
                match = re.search(r'products="([^"]+)"', response.text)
                
                if match:
                    # Decodifica as entidades HTML (&quot;) para formato JSON real
                    dados_sujos = match.group(1)
                    dados_limpos = html.unescape(dados_sujos)
                    lista_produtos = json.loads(dados_limpos)
                    
                    if not lista_produtos:
                        break
                        
                    todos_produtos.extend(lista_produtos)
                else:
                    # Se não houver o atributo products, pode ser o fim dos resultados
                    break
            else:
                st.error(f"Erro no servidor: Status {response.status_code}")
                break
        except Exception as e:
            st.error(f"Erro na conexão: {e}")
            break
            
    return todos_produtos

# --- INTERFACE ---
st.set_page_config(page_title="Monitor Nagumo", layout="wide")

# CSS para manter o estilo do seu projeto original
st.markdown("""
    <style>
    .product-container { display: flex; align-items: center; gap: 15px; padding: 10px; }
    .product-info { flex-grow: 1; }
    .product-separator { border: 0; border-top: 1px solid #eee; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 Busca Avançada Nagumo")

col_input, col_quant = st.columns([3, 1])
with col_input:
    termo = st.text_input("Produto:", "cenoura")
with col_quant:
    quantidade = st.selectbox("Quantidade total", [20, 40, 60, 80, 100], index=1)

if st.button("Pesquisar Agora"):
    with st.spinner('Carregando itens...'):
        resultados = buscar_produtos_nagumo(termo, total_itens=quantidade)
    
    if resultados:
        st.success(f"Exibindo {len(resultados)} produtos encontrados.")
        
        for p in resultados:
            # Mapeamento dos campos do JSON interno do Nagumo
            nome = p.get('productName', 'Produto sem nome')
            
            # Preço - Tenta pegar o valor de venda (sales)
            preco_data = p.get('price', {}).get('sales', {})
            preco_final = preco_data.get('value', 0.0) if preco_data else 0.0
            
            # Imagem
            img_url = DEFAULT_IMAGE_URL
            images = p.get('images', {}).get('medium', [])
            if images:
                img_url = images[0].get('absURL', DEFAULT_IMAGE_URL)
            
            url_site = p.get('productShowFullUrl', '#')
            
            # Layout seguindo seu padrão anterior
            st.markdown(f"""
                <div class='product-container'>
                    <a href='{url_site}' target='_blank'>
                        <img src="{img_url}" width="80" style="border-radius: 6px; border: 1px solid #eee; background: white;"/>
                    </a>
                    <div class='product-info'>
                        <a href='{url_site}' target='_blank' style='text-decoration:none; color:black;'>
                            <strong>{nome}</strong>
                        </a><br>
                        <span style='font-weight: bold; color: #d32f2f; font-size: 1.1rem;'>
                            R$ {preco_final:.2f}
                        </span>
                    </div>
                </div>
                <hr class='product-separator' />
            """, unsafe_allow_html=True)
    else:
        st.warning("Nenhum item encontrado para esta busca.")
