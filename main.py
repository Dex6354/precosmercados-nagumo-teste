import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def slugify(text):
    text = remover_acentos(text)
    text = re.sub(r'[^a-z0-9\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text

# --- NOVA BUSCA (API INTERNA IDENTIFICADA NO .HAR) ---
def buscar_nagumo_internal(term):
    """Utiliza a API de vitrine que o site consome diretamente"""
    # Endpoint de fallback quando o Algolia falha ou é ignorado pelo site
    url = f"https://www.nagumo.com.br/api/v1/search"
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
        r = requests.get(url, params=params, headers=headers, timeout=10)
        data = r.json()
        # Retorna a lista de produtos da estrutura v1
        return data.get('products', [])
    except Exception as e:
        st.error(f"Erro na conexão com a API Nagumo: {e}")
        return []

# --- INTERFACE ---
st.set_page_config(page_title="Preços Nagumo", layout="wide")

st.markdown("""<style>
    .block-container { padding-top: 1rem; }
    div, span, strong { font-size: 0.8rem !important; }
    .product-container { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #eee; }
    .img-box { flex: 0 0 60px; }
    .price-tag { color: #2e7d32; font-weight: bold; font-size: 1.1rem !important; }
</style>""", unsafe_allow_html=True)

st.markdown("<h6>🛒 Buscador Nagumo (Internal API)</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Digite o produto:", "Cenoura").strip()

if termo:
    with st.spinner("Buscando itens..."):
        produtos = buscar_nagumo_internal(termo)
        final_list = []
        
        for p in produtos:
            nome = p.get('productName', '')
            sku = p.get('productId') or p.get('sku')
            
            # --- LÓGICA DE PREÇO (CRÍTICA PARA CENOURA) ---
            # 1. Tenta pegar de flagtypes (comum em itens de hortifruti no Nagumo)
            # 2. Tenta pegar de price -> sales -> value
            preco = 0.0
            if p.get('flagtypes'):
                preco = p['flagtypes'][0].get('valueFlag', 0.0)
            
            if preco == 0:
                price_data = p.get('price', {})
                if isinstance(price_data, dict):
                    preco = price_data.get('sales', {}).get('value', 0.0)

            if preco > 0:
                # Captura de imagem
                img = DEFAULT_IMAGE_URL
                if p.get('images'):
                    img = p['images'][0].get('src', {}).get('disUrl', DEFAULT_IMAGE_URL)
                
                final_list.append({
                    "nome": nome,
                    "preco": preco,
                    "img": img,
                    "url": f"https://www.nagumo.com.br/p/{slugify(nome)}-{sku}",
                    "unidade": p.get('averageWeightDisplay', 'un')
                })

    # Exibição
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        if not final_list:
            st.warning("Nenhum item encontrado. Tente verificar a conexão ou o termo.")
        else:
            for p in final_list:
                st.markdown(f"""
                    <div class="product-container">
                        <div class="img-box"><img src="{p['img']}" width="60"></div>
                        <div style="flex: 1;">
                            <a href="{p['url']}" target="_blank" style="text-decoration: none; color: #333;">
                                <strong>{p['nome']}</strong>
                            </a><br>
                            <span class="price-tag">R$ {p['preco']:.2f}</span>
                            <span style="color: gray; margin-left: 10px;">({p['unidade']})</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
