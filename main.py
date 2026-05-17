import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re
import math
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"
ID_LOJA = "22" 
ITENS_POR_PAGINA = 24

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def calcular_preco_unitario_nagumo(preco_valor, nome, medida_venda):
    texto = remover_acentos(nome.lower())
    match = re.search(r'(\d+[.,]?\d*)\s*(kg|g|l|ml|un)', texto)
    if match:
        try:
            valor = float(match.group(1).replace(',', '.'))
            unid = match.group(2)
            if valor > 0:
                if unid == 'g': return f"R$ {preco_valor / (valor/1000):.2f}/kg"
                if unid == 'kg': return f"R$ {preco_valor / valor:.2f}/kg"
                if unid == 'ml': return f"R$ {preco_valor / (valor/1000):.2f}/L"
                if unid == 'l': return f"R$ {preco_valor / valor:.2f}/L"
                if unid == 'un': return f"R$ {preco_valor / valor:.2f}/un"
        except: pass
    if medida_venda == "unity": return f"R$ {preco_valor:.2f}/un"
    return "---"

def extrair_valor_unitario(label):
    match = re.search(r"R\$ (\d+[.,]?\d*)", label)
    return float(match.group(1).replace(',', '.')) if match else float('inf')

def fetch_api(url):
    cookies = {"dw_store": ID_LOJA, "hasSelectedStore": ID_LOJA}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if r.status_code == 200:
            return r.json()
    except: pass
    return {}

# --- BUSCA PARALELA TOTAL ---
def buscar_nagumo_turbo_total(termo_usuario):
    palavras_chave = remover_acentos(termo_usuario).split()
    if not palavras_chave: return []
    
    termo_api = palavras_chave[0]
    
    # 1. Descobrir o total de itens
    url_inicial = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={termo_api}&start=00&sz={ITENS_POR_PAGINA}"
    data_inicial = fetch_api(url_inicial)
    
    total_count = data_inicial.get('productSearch', {}).get('count', 0)
    if total_count == 0: return []
    
    # 2. Gerar todas as URLs de páginas
    num_paginas = math.ceil(total_count / ITENS_POR_PAGINA)
    urls = [
        f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={termo_api}&start={i*ITENS_POR_PAGINA:02d}&sz={ITENS_POR_PAGINA}"
        for i in range(num_paginas)
    ]
    
    # 3. Buscar tudo em paralelo (Threads limitadas a 10 para não ser bloqueado)
    all_raw_products = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        resultados = list(executor.map(fetch_api, urls))
        for res in resultados:
            all_raw_products.extend(res.get('productsSearchResult', []))
            
    # 4. Filtragem e Processamento
    vistos = set()
    final_list = []
    
    for p in all_raw_products:
        pid = p.get('id')
        if not pid or pid in vistos or not p.get('available'): continue
        
        nome = p.get('productName', '')
        nome_norm = remover_acentos(nome)
        
        if all(k in nome_norm for k in palavras_chave):
            vistos.add(pid)
            
            sales = p.get('price', {}).get('sales', {})
            preco_normal = float(sales.get('value', 0)) if sales.get('value') else 0.0
            preco_final = preco_normal
            has_promo = False
            
            for flag in p.get('flagtypes', []):
                if flag.get('valueFlag'):
                    try:
                        val = float(flag['valueFlag'])
                        if val < preco_final:
                            preco_final = val
                            has_promo = True
                    except: pass
            
            label = calcular_preco_unitario_nagumo(preco_final, nome, p.get('productMeasureValue'))
            img_data = p.get('images', {}).get('large', [{}])
            
            final_list.append({
                'productName': nome,
                'preco_final': preco_final,
                'preco_normal': preco_normal,
                'has_promo': has_promo,
                'calc_label': label,
                'sort_val': extrair_valor_unitario(label),
                'img_url': img_data[0].get('alt', DEFAULT_IMAGE_URL) if img_data else DEFAULT_IMAGE_URL,
                'link': p.get('productShowFullUrl', '#')
            })
            
    return sorted(final_list, key=lambda x: x['sort_val'])

# --- INTERFACE ---
st.set_page_config(page_title="Nagumo Ultra Fast", layout="wide")
st.markdown("<style>.block-container { padding-top: 0rem; } header {display: none;} div, span, strong { font-size: 0.75rem !important; } .price-tag { font-size: 1rem !important; font-weight: bold; } .off-tag { color: #d32f2f; font-weight: bold; }</style>", unsafe_allow_html=True)

st.markdown("<h6>🚀 Busca Exaustiva Paralela - Loja 22</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Produto:", "Leite Integral").strip()

if termo:
    with st.spinner("⚡ Analisando todo o catálogo em tempo recorde..."):
        resultados = buscar_nagumo_turbo_total(termo)
    
    if resultados:
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='80'/><br><small><b>{len(resultados)}</b> itens encontrados em todas as páginas.</small></p>", unsafe_allow_html=True)
            for p in resultados:
                preco_html = f"<span class='price-tag'>R$ {p['preco_final']:.2f}</span>"
                if p['has_promo']:
                    preco_html += f" <span class='off-tag'>PROMO</span>"

                st.markdown(f"""
                    <div style="display: flex; gap: 12px; margin-bottom: 10px;">
                        <img src="{p['img_url']}" width="75" style="border-radius:8px; border:1px solid #eee; background:white;"/>
                        <div style="flex: 1;">
                            <strong>{p['productName']}</strong><br>
                            {preco_html}<br>
                            <div style="color: #666;">{p['calc_label']}</div>
                        </div>
                    </div>
                    <hr style='margin:8px 0; border:0; border-top:1px solid #eee;'/>
                """, unsafe_allow_html=True)
    else:
        st.warning("Nenhum item encontrado.")

components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
