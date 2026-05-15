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

def calcular_preco_unitario_nagumo(preco_valor, descricao, nome, unidade_api=None):
    texto_completo = remover_acentos(f"{nome} {descricao}")
    unidade = str(unidade_api).lower() if unidade_api else ""
    
    # Se for quilo (Cenoura, Batata, etc)
    if "kg" in unidade or "quilo" in texto_completo or "kg" in texto_completo:
        return f"R$ {preco_valor:.2f}/kg"
    
    # Se for unidade
    if "un" in unidade or "unit" in unidade:
        return f"R$ {preco_valor:.2f}/un"

    return f"R$ {preco_valor:.2f}"

def buscar_nagumo(term):
    url = "https://nextgentheadless.instaleap.io/api/v3"
    headers = {"Content-Type": "application/json", "Origin": "https://www.nagumo.com", "User-Agent": "Mozilla/5.0"}
    payload = {
        "operationName": "SearchProducts",
        "variables": {"searchProductsInput": {"clientId": "NAGUMO", "storeReference": "22", "currentPage": 1, "pageSize": 50, "search": [{"query": term}], "filters": {}}},
        "query": """query SearchProducts($searchProductsInput: SearchProductsInput!) { 
            searchProducts(searchProductsInput: $searchProductsInput) { 
                products { name price photosUrl sku stock description unit 
                    promotion { isActive conditions { price } } 
                } 
            } 
        }"""
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        return r.json().get('data', {}).get('searchProducts', {}).get('products', []) or []
    except: return []

# --- INTERFACE ---
st.set_page_config(page_title="Preços Nagumo", layout="wide")

st.markdown("""<style>
    .block-container { padding-top: 1rem; }
    div, span, strong { font-size: 0.8rem !important; }
    .product-container { display: flex; align-items: center; gap: 12px; padding: 8px 0; border-bottom: 1px solid #eee; }
    .img-box { flex: 0 0 60px; position: relative; }
    .logo-overlay { position: absolute; bottom: 0; right: 0; width: 30px !important; border: 1px solid white; border-radius: 4px; }
</style>""", unsafe_allow_html=True)

termo = st.text_input("🔎 O que você procura hoje?", "Cenoura").strip()

if termo:
    palavras_chave = remover_acentos(termo).split()
    with st.spinner("Buscando..."):
        resultados = buscar_nagumo(termo)
        
        final_list = []
        vistos = set()

        for p in resultados:
            sku = p.get('sku')
            if sku and sku not in vistos:
                vistos.add(sku)
                nome = p.get('name', '')
                desc = p.get('description', '') or ""
                
                # Captura de Preço (Lógica corrigida para Hortifruti)
                promo = p.get('promotion') or {}
                cond = promo.get('conditions') or []
                preco_api = p.get('price', 0)
                
                # Se o preço principal for 0, tenta pegar o preço da condição promocional
                preco_final = cond[0].get('price') if cond else preco_api
                
                # Filtro de palavras-chave no nome e descrição
                if all(k in remover_acentos(f"{nome} {desc}") for k in palavras_chave):
                    if preco_final > 0:
                        p['preco_exibicao'] = preco_final
                        p['unit_label'] = calcular_preco_unitario_nagumo(preco_final, desc, nome, p.get('unit'))
                        p['url'] = f"https://www.nagumo.com.br/categoria/departamentos/p/{slugify(nome)}-{sku}.html"
                        final_list.append(p)

        # Ordenar por preço unitário
        final_list = sorted(final_list, key=lambda x: x['preco_exibicao'])

    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown(f"**{len(final_list)} produtos encontrados**")
        for p in final_list:
            img = p['photosUrl'][0] if p.get('photosUrl') else DEFAULT_IMAGE_URL
            st.markdown(f"""
                <div class="product-container">
                    <div class="img-box">
                        <img src="{img}" width="60">
                        <img src="{LOGO_NAGUMO_URL}" class="logo-overlay">
                    </div>
                    <div style="flex: 1;">
                        <a href="{p['url']}" target="_blank" style="text-decoration: none; color: #333;"><strong>{p['name']}</strong></a><br>
                        <span style="color: #2e7d32; font-weight: bold; font-size: 1rem !important;">R$ {p['preco_exibicao']:.2f}</span>
                        <span style="color: gray; margin-left: 10px;">({p['unit_label']})</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
