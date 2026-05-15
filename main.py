import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"
# Endpoint da busca convencional identificada no F12
SEARCH_API_URL = "https://www.nagumo.com.br/api/v1/search"

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def slugify(text):
    text = remover_acentos(text)
    text = re.sub(r'[^a-z0-9\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text

# --- NOVA LÓGICA DE BUSCA (API V1) ---
def buscar_nagumo_v1(term):
    """Utiliza a API de busca que o site consome para renderizar a vitrine"""
    params = {
        "q": term,
        "sort": "relevance",
        "page": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://www.nagumo.com.br",
        "Referer": "https://www.nagumo.com.br/"
    }
    try:
        # Nota: O Nagumo pode exigir cookies de sessão ou store_id (loja). 
        # Esta requisição simula a busca direta do parâmetro 'q'
        r = requests.get(SEARCH_API_URL, params=params, headers=headers, timeout=10)
        data = r.json()
        # A estrutura V1 geralmente retorna 'products' ou 'items'
        return data.get('products', []) or data.get('items', [])
    except:
        return []

# --- INTERFACE ---
st.set_page_config(page_title="Preços Nagumo", layout="wide")

st.markdown("""<style>
    .block-container { padding-top: 1rem; }
    div, span, strong { font-size: 0.8rem !important; }
    .product-container { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #eee; }
    .img-box { flex: 0 0 60px; }
    .price-tag { color: #2e7d32; font-weight: bold; font-size: 1rem !important; }
</style>""", unsafe_allow_html=True)

termo = st.text_input("🔎 Pesquisar Produto:", "Cenoura").strip()

if termo:
    palavras_chave = remover_acentos(termo).split()
    
    with st.spinner("Buscando itens..."):
        # Tenta a busca pela API V1 (do site)
        itens_brutos = buscar_nagumo_v1(termo)
        final_list = []
        
        for p in itens_brutos:
            nome = p.get('productName') or p.get('name') or ""
            sku = p.get('productId') or p.get('sku')
            
            # Filtro de relevância
            if all(k in remover_acentos(nome) for k in palavras_chave):
                
                # Extração de Preço Multi-Camada (Comum em Hortifruti)
                # 1. Tenta pegar de 'price'
                # 2. Tenta pegar de 'flagtypes' (onde a cenoura costuma ficar)
                # 3. Tenta pegar de 'sales'
                preco = 0.0
                price_data = p.get('price', {})
                
                if isinstance(price_data, dict):
                    preco = price_data.get('sales', {}).get('value', 0)
                elif isinstance(price_data, (int, float)):
                    preco = price_data

                # Se for 0, busca em flagtypes (comportamento main2)
                if preco == 0 and p.get('flagtypes'):
                    preco = p['flagtypes'][0].get('valueFlag', 0)

                if preco > 0:
                    # Montagem da URL final
                    url_slug = slugify(nome)
                    p['url_final'] = f"https://www.nagumo.com.br/p/{url_slug}-{sku}"
                    p['preco_final'] = preco
                    p['nome_formatado'] = nome
                    
                    # Identifica se é KG ou UN
                    unidade = "kg" if "kg" in remover_acentos(nome) or "quilo" in remover_acentos(nome) else "un"
                    p['unit_label'] = f"R$ {preco:.2f}/{unidade}"
                    
                    final_list.append(p)

    # Exibição Centralizada
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        if not final_list:
            st.error("Nenhum item encontrado com esta busca. Tente um termo mais genérico.")
        else:
            st.success(f"Encontrados {len(final_list)} itens.")
            for p in final_list:
                # Busca imagem (vários formatos possíveis na API V1)
                img = DEFAULT_IMAGE_URL
                if p.get('images'):
                    img = p['images'][0].get('src', {}).get('disUrl', DEFAULT_IMAGE_URL)
                elif p.get('photosUrl'):
                    img = p['photosUrl'][0]

                st.markdown(f"""
                    <div class="product-container">
                        <div class="img-box"><img src="{img}" width="60"></div>
                        <div style="flex: 1;">
                            <a href="{p['url_final']}" target="_blank" style="text-decoration: none; color: #333;">
                                <strong>{p['nome_formatado']}</strong>
                            </a><br>
                            <span class="price-tag">R$ {p['preco_final']:.2f}</span>
                            <span style="color: gray; margin-left: 10px;">({p['unit_label']})</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
