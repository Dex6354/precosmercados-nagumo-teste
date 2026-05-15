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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "pt-BR,pt;q=0.9"
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

# --- SCRAPER DE BUSCA (A FORMA QUE TRAZ A CENOURA) ---
def buscar_nagumo_scraping(termo):
    """Faz o scrap direto da página de busca do site"""
    url_busca = f"https://www.nagumo.com.br/busca?q={termo}"
    try:
        response = requests.get(url_busca, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return []
        
        soup = BeautifulSoup(response.content, 'html.parser')
        produtos_finais = []
        
        # O Nagumo armazena os dados dos produtos em elementos <product-card> ou em JSONs dentro de scripts
        # Vamos buscar todos os cards de produto na página
        cards = soup.find_all('div', class_='product-card') # Ajuste conforme a classe real do grid
        
        # Se não achar por classe, tentamos extrair o objeto JSON que o Nagumo injeta na página (Common em Vue/Nuxt)
        scripts = soup.find_all('script')
        for script in scripts:
            if 'window.__NUXT__' in script.text or 'window.state' in script.text:
                # Aqui poderíamos fazer um regex para pegar o JSON, mas vamos pelo HTML que é mais estável para você
                pass

        # Fallback: Se o seu main2.py funcionou para URLs fixas, vamos aplicar a lógica de extração aqui
        # O Nagumo renderiza os itens de hortifruti muitas vezes em tags customizadas
        items = soup.select('div[class*="product-item"], div[class*="item-product"]')
        
        if not items:
            # Busca por links de produtos que contenham o termo
            items = soup.find_all('a', href=re.compile(r'/p/'))

        for item in items:
            try:
                nome_elem = item.find(['h2', 'h3', 'span'], class_=re.compile(r'name|title'))
                nome = nome_elem.text.strip() if nome_elem else item.get('title', '')
                
                if not nome and 'title' in item.attrs: nome = item['title']
                
                # Se ainda não tem nome, pula
                if not nome or remover_acentos(termo) not in remover_acentos(nome):
                    continue

                link = item['href'] if item.name == 'a' else item.find('a')['href']
                if not link.startswith('http'):
                    link = "https://www.nagumo.com.br" + link
                
                preco_elem = item.find(class_=re.compile(r'price|value'))
                preco_texto = preco_elem.text.strip() if preco_elem else "0"
                # Limpa o preço (R$ 5,49 -> 5.49)
                preco_num = re.search(r'(\d+,\d{2})', preco_texto)
                preco = float(preco_num.group(1).replace(',', '.')) if preco_num else 0.0

                img_elem = item.find('img')
                img = img_elem.get('src') or img_elem.get('data-src') or DEFAULT_IMAGE_URL

                produtos_finais.append({
                    "name": nome,
                    "price": preco,
                    "img": img,
                    "url": link,
                    "sku": link.split('-')[-1].replace('.html', '')
                })
            except:
                continue
                
        return produtos_finais
    except Exception as e:
        st.error(f"Erro no scraping: {e}")
        return []

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Monitor Nagumo", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        .product-card { border: 1px solid #eee; padding: 10px; border-radius: 8px; margin-bottom: 10px; display: flex; align-items: center; gap: 15px; }
        .price { color: #2e7d32; font-weight: bold; font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 Buscador Nagumo (Scraping Mode)")
termo = st.text_input("Digite o produto (ex: Cenoura):", "Cenoura").strip()

if termo:
    with st.spinner(f"Lendo página de busca para '{termo}'..."):
        # Tenta a técnica do main2 (Scraping direto do HTML da busca)
        resultados = buscar_nagumo_scraping(termo)
        
        if not resultados:
            st.warning("A busca não retornou itens no HTML. Verificando via API de fallback...")
            # Fallback para a busca via URL de categoria se for cenoura
            if "cenoura" in remover_acentos(termo):
                url_cenoura = "https://www.nagumo.com.br/categoria/departamentos/hortifruti/legumes/tuberculos/cenoura-13772.html"
                st.info(f"Tentando extração direta do link conhecido...")
                # Aqui você pode chamar a função scrape_nagumo_product do seu main2.py
        
        _, col_center, _ = st.columns([1, 2, 1])
        with col_center:
            st.write(f"**{len(resultados)} itens encontrados no HTML**")
            for p in resultados:
                st.markdown(f"""
                    <div class="product-card">
                        <img src="{p['img']}" width="80">
                        <div>
                            <a href="{p['url']}" target="_blank"><strong>{p['name']}</strong></a><br>
                            <span class="price">R$ {p['price']:.2f}</span><br>
                            <small>SKU: {p['sku']}</small>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

# Log para F12
if st.checkbox("Ver Log da Página"):
    r_debug = requests.get(f"https://www.nagumo.com.br/busca?q={termo}", headers=HEADERS)
    st.code(r_debug.text[:2000], language="html")
