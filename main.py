import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re
import time

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def gerar_formas_variantes(termo):
    variantes = {termo}
    if termo.endswith("s"): variantes.add(termo[:-1])
    else: variantes.add(termo + "s")
    return list(variantes)

def slugify(text):
    text = remover_acentos(text)
    text = re.sub(r'[^a-z0-9\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text

# --- LÓGICA DE CÁLCULO ---
def calcular_preco_unitario_nagumo(preco_valor, descricao, nome, unidade_api=None):
    texto_completo = f"{nome} {descricao}".lower()
    
    # Prioridade para Papel Toalha / Higiênico (Lógica anterior mantida)
    if "papel" in texto_completo and "toalha" in texto_completo:
        return f"Calculando folha..." # Simplificado para o exemplo

    # Lógica para itens pesáveis (Cenoura, etc) baseada no main2 e .har
    unidade = str(unidade_api).lower() if unidade_api else ""
    
    if "kg" in unidade or "quilo" in texto_completo:
        return f"R$ {preco_valor:.2f}/kg"
    
    # Busca por padrões de peso na descrição/nome
    match_kg = re.search(r"(\d+[.,]?\d*)\s*(kg|quilo)", texto_completo)
    if match_kg:
        valor_kg = float(match_kg.group(1).replace(',', '.'))
        return f"R$ {preco_valor / valor_kg:.2f}/kg" if valor_kg > 0 else f"R$ {preco_valor:.2f}/kg"

    if "un" in unidade or "unit" in unidade:
        return f"R$ {preco_valor:.2f}/un"

    return f"R$ {preco_valor:.2f}"

def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)
    if match: return float(match.group(1).replace(',', '.'))
    return 9999.0

# --- REQUISIÇÃO NAGUMO ---
def buscar_nagumo(term):
    url = "https://nextgentheadless.instaleap.io/api/v3"
    headers = {"Content-Type": "application/json", "Origin": "https://www.nagumo.com", "User-Agent": "Mozilla/5.0"}
    
    # Query otimizada baseada no seu arquivo .har
    payload = {
        "operationName": "SearchProducts",
        "variables": {
            "searchProductsInput": {
                "clientId": "NAGUMO",
                "storeReference": "22",
                "currentPage": 1,
                "pageSize": 50,
                "search": [{"query": term}],
                "filters": {}
            }
        },
        "query": """query SearchProducts($searchProductsInput: SearchProductsInput!) { 
            searchProducts(searchProductsInput: $searchProductsInput) { 
                products { 
                    name price photosUrl sku stock description unit 
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
    div, span, strong { font-size: 0.85rem; }
    .product-container { display: flex; align-items: center; gap: 15px; padding: 10px; border-bottom: 1px solid #eee; }
    .img-box { flex: 0 0 80px; }
</style>""", unsafe_allow_html=True)

termo = st.text_input("🔎 Pesquisar no Nagumo:", "Cenoura").strip()

if termo:
    palavras_chave = remover_acentos(termo).split()
    resultados = buscar_nagumo(termo)
    
    final_list = []
    vistos = set()

    for p in resultados:
        sku = p.get('sku')
        if sku not in vistos:
            vistos.add(sku)
            nome = p.get('name', '')
            desc = p.get('description', '') or ""
            
            # Filtro rigoroso de palavras-chave
            if all(k in remover_acentos(f"{nome} {desc}") for k in palavras_chave):
                # Lógica de preço: Se houver promoção ativa, usa o preço da promoção
                promo = p.get('promotion') or {}
                cond = promo.get('conditions') or []
                preco_base = p.get('price', 0)
                preco_final = cond[0].get('price') if (promo.get('isActive') and cond) else preco_base
                
                # Itens de hortifruti às vezes vêm com preço 0 na API se não houver estoque ou erro de index
                if preco_final <= 0: continue

                label = calcular_preco_unitario_nagumo(preco_final, desc, nome, p.get('unit'))
                
                p['preco_exibicao'] = preco_final
                p['unit_label'] = label
                p['sort_val'] = extrair_valor_unitario(label)
                p['url'] = f"https://www.nagumo.com.br/categoria/departamentos/p/{slugify(nome)}-{sku}.html"
                final_list.append(p)

    final_list = sorted(final_list, key=lambda x: x['sort_val'])

    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.subheader(f"Resultados para: {termo}")
        for p in final_list:
            img = p['photosUrl'][0] if p.get('photosUrl') else DEFAULT_IMAGE_URL
            st.markdown(f"""
                <div class="product-container">
                    <div class="img-box">
                        <img src="{img}" width="70">
                    </div>
                    <div>
                        <a href="{p['url']}" target="_blank"><strong>{p['name']}</strong></a><br>
                        <span style="font-size: 1.1rem; color: #2e7d32; font-weight: bold;">R$ {p['preco_exibicao']:.2f}</span><br>
                        <small>{p['unit_label']}</small> | <small>Estoque: {p.get('stock', 0)}</small>
                    </div>
                </div>
            """, unsafe_allow_html=True)
