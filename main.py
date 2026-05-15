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
    
    fontes = [descricao.lower(), nome.lower()]
    for fonte in fontes:
        match_kg = re.search(r"(\d+[.,]?\d*)\s*(kg|quilo)", fonte)
        if match_kg and float(match_kg.group(1).replace(',', '.')) > 0: 
            return f"R$ {preco_valor / float(match_kg.group(1).replace(',', '.')):.2f}/kg"
        
        match_g = re.search(r"(\d+[.,]?\d*)\s*(g|gramas?)", fonte)
        if match_g and float(match_g.group(1).replace(',', '.')) > 0: 
            return f"R$ {preco_valor / (float(match_g.group(1).replace(',', '.')) / 1000):.2f}/kg"
            
        match_un = re.search(r"(\d+[.,]?\d*)\s*(un|unidades?)", fonte)
        if match_un and float(match_un.group(1).replace(',', '.')) > 0: 
            return f"R$ {preco_valor / float(match_un.group(1).replace(',', '.')):.2f}/un"

    if unidade_api:
        u = unidade_api.lower()
        if u == 'kg': return f"R$ {preco_valor:.2f}/kg"
        elif u == 'un': return f"R$ {preco_valor:.2f}/un"
    return "Sem unidade"

def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)
    if match: return float(match.group(1).replace(',', '.'))
    return float('inf')

# --- REQUISIÇÃO NAGUMO ---
def buscar_nagumo(term, categoria_id=None):
    url = "https://nextgentheadless.instaleap.io/api/v3"
    headers = {"Content-Type": "application/json", "Origin": "https://www.nagumo.com", "User-Agent": "Mozilla/5.0"}
    
    # Se o termo for especificamente cenoura ou tomate, podemos forçar o ID que achamos no HAR
    filtros = {}
    termo_limpo = remover_acentos(term)
    if "cenoura" in termo_limpo: filtros = {"categories": ["13772"]}
    elif "tomate" in termo_limpo: filtros = {"categories": ["13761"]}

    produtos = []
    for page in range(1, 6): # Varre até 500 itens
        payload = {
            "operationName": "SearchProducts",
            "variables": {
                "searchProductsInput": {
                    "clientId": "NAGUMO", 
                    "storeReference": "22", 
                    "currentPage": page, 
                    "pageSize": 100, 
                    "search": [{"query": term}], 
                    "filters": filtros
                }
            },
            "query": "query SearchProducts($searchProductsInput: SearchProductsInput!) { searchProducts(searchProductsInput: $searchProductsInput) { products { name price photosUrl sku stock description unit promotion { isActive conditions { price priceBeforeTaxes } } } } }"
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            data = r.json().get('data', {}).get('searchProducts', {}).get('products', [])
            if not data: break
            produtos.extend(data)
            if len(data) < 100: break
        except: break
    return produtos

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 0rem; }
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        div, span, strong, small { font-size: 0.75rem !important; }
        [data-testid="stColumn"] {
            overflow-y: auto; max-height: 90vh; padding: 10px; border: 1px solid #f0f2f6; border-radius: 8px;
            max-width: 600px; margin-left: auto; margin-right: auto; background: transparent;
        }
        header[data-testid="stHeader"] { display: none; }
        .product-container { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0rem; }
        hr.product-separator { border: none; border-top: 1px solid #eee; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h6>🛒 Preços Nagumo</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Digite o nome do produto:", "Cenoura").strip()

if termo:
    termo_limpo = remover_acentos(termo)
    termos_busca = gerar_formas_variantes(termo_limpo)
    palavras_chave = termo_limpo.split()

    with st.spinner("🔍 Buscando no Nagumo..."):
        raw_nagumo = []
        for t in termos_busca: raw_nagumo.extend(buscar_nagumo(t))
        
        vistos_nagumo = set()
        nagumo_final = []
        for p in raw_nagumo:
            sku = p.get('sku')
            if sku and sku not in vistos_nagumo:
                vistos_nagumo.add(sku)
                nome = p.get('name', '')
                nome_limpo = remover_acentos(nome)
                
                # Validação de palavras-chave
                if all(k in remover_acentos(f"{nome} {p.get('description', '')}") for k in palavras_chave):
                    promo = p.get('promotion') or {}
                    cond = promo.get('conditions') or []
                    preco_normal = p.get('price', 0)
                    preco_final = cond[0].get('price') if (promo.get('isActive') and cond) else preco_normal
                    
                    label = calcular_preco_unitario_nagumo(preco_final, p.get('description', ''), nome, p.get('unit'))
                    p['url_final'] = f"https://www.nagumo.com.br/categoria/departamentos/p/{slugify(nome)}-{sku}.html"
                    p['unit_label'] = label
                    p['sort_val'] = extrair_valor_unitario(label)
                    p['preco_final'] = preco_final
                    
                    # Prioridade: 1. Nome exato | 2. Começa com o nome | 3. Contém no nome
                    if nome_limpo == termo_limpo: p['score'] = 1
                    elif nome_limpo.startswith(termo_limpo): p['score'] = 2
                    else: p['score'] = 3
                    
                    nagumo_final.append(p)
        
        # Ordenação por Relevância + Preço Unitário
        nagumo_final = sorted(nagumo_final, key=lambda x: (x['score'], x['sort_val']))

    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(f"<p align='center'><small>🔎 {len(nagumo_final)} produto(s) encontrado(s).</small></p>", unsafe_allow_html=True)
        for p in nagumo_final:
            img = p.get('photosUrl')[0] if p.get('photosUrl') else DEFAULT_IMAGE_URL
            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['url_final']}' target='_blank'>
                        <img src="{img}" width="80" style="border-radius: 6px; border: 1px solid #eee;"/>
                    </a>
                    <div style='flex: 1; margin-left: 10px;'>
                        <a href='{p['url_final']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['name']}</strong></a><br>
                        <span style='font-size: 1.1rem; font-weight: bold;'>R$ {p['preco_final']:.2f}</span><br>
                        <small style='color: #666;'>{p['unit_label']}</small>
                    </div>
                </div>
                <hr class='product-separator' />
            """, unsafe_allow_html=True)
