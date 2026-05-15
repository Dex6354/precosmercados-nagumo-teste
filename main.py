import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"

# Dados extraídos do seu arquivo .har
ALGOLIA_URL = "https://v7m6p98id9-dsn.algolia.net/1/indexes/nagumo_production_products/query"
ALGOLIA_HEADERS = {
    "X-Algolia-API-Key": "94490f23032502013876e6255767b419", # Chave pública do Nagumo
    "X-Algolia-Application-Id": "V7M6P98ID9",
    "Content-Type": "application/json"
}

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def slugify(text):
    text = remover_acentos(text)
    text = re.sub(r'[^a-z0-9\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text

# --- BUSCA VIA ALGOLIA (API CORRETA) ---
def buscar_nagumo_algolia(term):
    """Realiza a busca utilizando o motor Algolia identificado no .har"""
    # O payload precisa do filtro da loja (storeReference 22 foi o identificado no seu log)
    payload = {
        "params": f"query={term}&hitsPerPage=40&filters=storeReference:22 AND stock>0"
    }
    try:
        r = requests.post(ALGOLIA_URL, headers=ALGOLIA_HEADERS, json=payload, timeout=10)
        data = r.json()
        return data.get('hits', [])
    except Exception as e:
        st.error(f"Erro na API Algolia: {e}")
        return []

# --- INTERFACE ---
st.set_page_config(page_title="Preços Nagumo", layout="wide")

st.markdown("""<style>
    .block-container { padding-top: 1rem; }
    div, span, strong { font-size: 0.8rem !important; }
    .product-container { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #eee; }
    .img-box { flex: 0 0 60px; }
    .price-tag { color: #2e7d32; font-weight: bold; font-size: 1.1rem !important; }
</style>""", unsafe_allow_html=True)

st.markdown("<h6>🛒 Buscador Nagumo (Algolia API)</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Digite o produto:", "Cenoura").strip()

if termo:
    with st.spinner("Buscando itens reais..."):
        hits = buscar_nagumo_algolia(termo)
        final_list = []
        
        for h in hits:
            nome = h.get('name', '')
            # No Algolia, o preço costuma vir em 'price' ou dentro de 'promotion'
            preco = h.get('price', 0)
            sku = h.get('sku')
            
            # Captura de imagem do Algolia
            img = DEFAULT_IMAGE_URL
            if h.get('photosUrl'):
                img = h['photosUrl'][0]
            
            # Filtro básico de conferência
            if remover_acentos(termo) in remover_acentos(nome):
                url_final = f"https://www.nagumo.com.br/p/{slugify(nome)}-{sku}"
                
                final_list.append({
                    "nome": nome,
                    "preco": preco,
                    "img": img,
                    "url": url_final,
                    "unit": h.get('unit', 'un')
                })

    # Exibição
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        if not final_list:
            st.warning("Nenhum item encontrado nesta loja (Referência 22).")
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
                            <span style="color: gray; margin-left: 10px;">({p['unit']})</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
