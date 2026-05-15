import streamlit as st
import streamlit.components.v1 as components
import requests
from bs4 import BeautifulSoup
import unicodedata
import re
import json

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def extrair_preco(texto):
    if not texto: return 0.0
    match = re.search(r'R\$\s?(\d+,\d{2})', texto)
    if match:
        return float(match.group(1).replace(',', '.'))
    return 0.0

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace('.', 'X').replace(',', '.').replace('X', ',')

# --- SCRAPER NAGUMO ---
def scrape_nagumo_product(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Busca o objeto JSON de dados do produto no atributo :product
        product_data_element = soup.find('product-detail-quantity')
        if product_data_element and product_data_element.has_attr(':product'):
            data = json.loads(product_data_element[':product'])
            
            nome = data.get('productName', 'Produto sem nome')
            # Pega o preço promocional se existir, senão o normal
            preco = data.get('price', {}).get('sales', {}).get('value', 0.0)
            if data.get('flagtypes'):
                 preco = data['flagtypes'][0].get('valueFlag', preco)
            
            img = data.get('images', {}).get('large', [{}])[0].get('src', {}).get('disUrl', DEFAULT_IMAGE_URL)
            estoque = data.get('ATSInGenerealStock', 0)
            unit = data.get('averageWeightDisplay', 'Unidade')
            
            return {
                "titulo": nome,
                "preco": float(preco),
                "img": img,
                "url_final": url,
                "unit_label": unit,
                "stock": estoque
            }
        
        # Fallback para extração via HTML caso o JSON não esteja presente
        nome = soup.find('h1', class_='product-name')
        nome = nome.text.strip() if nome else "Produto"
        
        preco_final = soup.find('span', class_='productNotice-finalPrice')
        if not preco_final:
            preco_final = soup.find('span', class_='productPrice__price')
        
        preco = extrair_preco(preco_final.text) if preco_final else 0.0
        
        img_tag = soup.find('img', class_='productDetails__images__principal__img')
        img = img_tag['src'] if img_tag else DEFAULT_IMAGE_URL
        
        return {
            "titulo": nome,
            "preco": preco,
            "img": img,
            "url_final": url,
            "unit_label": "Consultar",
            "stock": "Em estoque"
        }
    except Exception as e:
        st.error(f"Erro ao processar {url}: {e}")
        return None

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Monitor Nagumo", layout="wide")

st.title("🛒 Monitor de Itens Nagumo")

# Exemplo de URLs baseadas no seu relato
urls = [
    "https://www.nagumo.com.br/categoria/departamentos/hortifruti/frutas/fruta-tradicional/banana-nanica-2004.html",
    "https://www.nagumo.com.br/categoria/departamentos/hortifruti/legumes/tuberculos/cenoura-13772.html"
]

if st.button("Atualizar Preços"):
    cols = st.columns(len(urls))
    
    for i, url in enumerate(urls):
        p = scrape_nagumo_product(url)
        if p:
            with cols[i]:
                st.image(p['img'], width=150)
                st.subheader(p['titulo'])
                st.write(f"**Preço:** {formatar_moeda(p['preco'])}")
                st.write(f"Unidade: {p['unit_label']}")
                st.write(f"Estoque: {p['stock']}")
                st.markdown(f"[Ver no site]({p['url_final']})")
        else:
            with cols[i]:
                st.warning(f"Item não encontrado: {url.split('/')[-1]}")

st.markdown("""
<style>
    .product-container { border: 1px solid #ddd; padding: 10px; border-radius: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)
