import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re
import html
import json
import pandas as pd

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

# --- LÓGICA DE BUSCA NAGUMO (CORRIGIDA) ---
def buscar_produtos_nagumo(termo_busca):
    url = f"https://www.nagumo.com.br/busca?q={termo_busca}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    produtos_formatados = []
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            # Extração via Regex do componente que contém o JSON de produtos
            match = re.search(r'products="([^"]+)"', response.text)
            if match:
                json_raw = html.unescape(match.group(1))
                dados_brutos = json.loads(json_raw)
                
                for p in dados_brutos:
                    # Mapeamento para o seu layout atual
                    img_data = p.get("images", {}).get("large", [{}])[0]
                    img_url = img_data.get("url", DEFAULT_IMAGE_URL)
                    
                    # Garantir que a URL da imagem seja absoluta
                    if img_url.startswith('/'):
                        img_url = f"https://www.nagumo.com.br{img_url}"

                    produtos_formatados.append({
                        "id": p.get("id"),
                        "productName": p.get("productName"),
                        "price_formatted": p.get("price", {}).get("sales", {}).get("formatted", "R$ 0,00"),
                        "price_value": p.get("price", {}).get("sales", {}).get("value", 0),
                        "image": img_url,
                        "brand": p.get("brand", "Nagumo"),
                        "url_final": f"https://www.nagumo.com.br/p/{p.get('id')}", # URL aproximada
                        "unit_label": "Unidade" # Campo padrão
                    })
    except Exception as e:
        st.error(f"Erro na busca: {e}")
        
    return produtos_formatados

# --- INTERFACE ---
st.title("🥕 Nagumo Search - Layout Final")

# CSS para manter o layout original
st.markdown("""
    <style>
    .product-container { display: flex; align-items: center; padding: 10px; }
    .product-image-box { margin-right: 15px; }
    .product-info { font-family: sans-serif; }
    .product-separator { border: 0; border-top: 1px solid #eee; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

query = st.text_input("Buscar no Nagumo:", placeholder="Ex: cenoura")

if query:
    with st.spinner("Buscando..."):
        resultados = buscar_produtos_nagumo(query)

    if resultados:
        for p in resultados:
            titulo = p['productName']
            preco_str = p['price_formatted']
            img = p['image']

            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['url_final']}' target='_blank' class='product-image-box'>
                        <img src="{img}" width="80" style="background-color: white; border-radius: 6px; display: block;"/>
                    </a>
                    <div class='product-info'>
                        <div style="font-size: 0.8em; color: gray;">{p['brand']}</div>
                        <a href='{p['url_final']}' target='_blank' style='text-decoration:none; color:inherit;'>
                            <strong>{titulo}</strong>
                        </a><br>
                        <span style='color: #2e7d32; font-weight: bold; font-size: 1.1rem;'>{preco_str}</span><br>
                        <div style="margin-top: 4px; font-size: 0.8em; color: #666;">ID: {p['id']}</div>
                    </div>
                </div>
                <hr class='product-separator' />
            """, unsafe_allow_html=True)
    else:
        st.warning("Nenhum produto encontrado.")

# Footer/Debugger Sidebar
with st.sidebar:
    st.header("Status")
    if query:
        st.write(f"Termo: {query}")
        st.write(f"Resultados: {len(resultados) if 'resultados' in locals() else 0}")
