import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re
from concurrent.futures import ThreadPoolExecutor

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"
ID_LOJA = "22" 
MAX_PAGINAS_PARALELO = 6  # Define quantas páginas buscar de uma vez (ex: 0 a 144 itens)

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

# --- FUNÇÃO DE BUSCA DE PÁGINA ÚNICA ---
def buscar_pagina_nagumo(url):
    cookies = {"dw_store": ID_LOJA, "hasSelectedStore": ID_LOJA}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        r = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if r.status_code == 200:
            return r.json().get('productsSearchResult', [])
    except:
        pass
    return []

# --- BUSCA PARALELIZADA ---
def buscar_nagumo_paralelo(termo_usuario):
    palavras_chave = remover_acentos(termo_usuario).split()
    if not palavras_chave: return []
    
    termo_api = palavras_chave[0]
    urls = [
        f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={termo_api}&start={i*24:02d}&sz=24"
        for i in range(MAX_PAGINAS_PARALELO)
    ]
    
    all_raw_products = []
    
    # Executa as requisições em paralelo
    with ThreadPoolExecutor(max_workers=MAX_PAGINAS_PARALELO) as executor:
        resultados = list(executor.map(buscar_pagina_nagumo, urls))
        for lista in resultados:
            all_raw_products.extend(lista)
            
    # Processamento e Filtragem (agora local e rápido)
    vistos = set()
    final_list = []
    
    for p in all_raw_products:
        pid = p.get('id')
        if not pid or pid in vistos or not p.get('available'):
            continue
            
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
                'link': p.get('productShowFullUrl', '#'),
                'brand': p.get('brand', 'N/A')
            })
            
    return sorted(final_list, key=lambda x: x['sort_val'])

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Nagumo Turbo", page_icon="⚡", layout="wide")
st.markdown("<style>.block-container { padding-top: 0rem; } header {display: none;} div, span, strong { font-size: 0.75rem !important; } .price-tag { font-size: 1rem !important; font-weight: bold; } .off-tag { color: #d32f2f; font-weight: bold; }</style>", unsafe_allow_html=True)

st.markdown("<h6>⚡ Pesquisa Paralela Nagumo - Loja 22</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 O que você procura?", "Leite Integral").strip()

if termo:
    with st.spinner(f"🚀 Buscando em {MAX_PAGINAS_PARALELO} páginas simultaneamente..."):
        resultados = buscar_nagumo_paralelo(termo)
    
    if resultados:
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='80'/><br><small><b>{len(resultados)}</b> itens encontrados.</small></p>", unsafe_allow_html=True)
            for p in resultados:
                preco_html = f"<span class='price-tag'>R$ {p['preco_final']:.2f}</span>"
                if p['has_promo'] and p['preco_normal'] > p['preco_final']:
                    desc = ((p['preco_normal'] - p['preco_final']) / p['preco_normal']) * 100
                    preco_html += f" <span class='off-tag'>({desc:.0f}% OFF)</span><br><span style='text-decoration:line-through; color:gray;'>R$ {p['preco_normal']:.2f}</span>"

                st.markdown(f"""
                    <div style="display: flex; gap: 12px; margin-bottom: 10px; align-items: center;">
                        <a href='{p['link']}' target='_blank'><img src="{p['img_url']}" width="80" style="border-radius:8px; background:white; border:1px solid #eee;"/></a>
                        <div style="flex: 1;">
                            <a href='{p['link']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['productName']}</strong></a><br>
                            {preco_html}<br>
                            <div style="color: #666;">{p['calc_label']}</div>
                        </div>
                    </div>
                    <hr style='margin:8px 0; border:0; border-top:1px solid #eee;'/>
                """, unsafe_allow_html=True)
    else:
        st.warning("Nada encontrado. Tente termos menos específicos.")

components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
