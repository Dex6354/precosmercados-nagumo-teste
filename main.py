import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"
ID_LOJA = "22" 

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def gerar_formas_variantes(termo):
    variantes = {termo}
    if termo.endswith("s"): variantes.add(termo[:-1])
    else: variantes.add(termo + "s")
    return list(variantes)

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

# --- BUSCA INTELIGENTE E RÁPIDA ---
def buscar_smart_nagumo(termo_completo):
    palavras = remover_acentos(termo_completo).split()
    if not palavras: return []
    
    # Buscamos apenas pelo primeiro termo para "abrir" a busca na API
    termo_busca = palavras[0]
    all_filtered = []
    vistos = set()
    
    cookies = {"dw_store": ID_LOJA, "hasSelectedStore": ID_LOJA}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    
    # Começamos a paginação
    start = 0
    step = 24
    max_tentativas = 4 # Analisar até ~100 itens da API costuma ser suficiente e rápido
    
    for _ in range(max_tentativas):
        url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={termo_busca}&start={start:02d}&sz={step}"
        try:
            r = requests.get(url, headers=headers, cookies=cookies, timeout=5)
            if r.status_code != 200: break
            
            data = r.json()
            products = data.get('productsSearchResult', [])
            if not products: break
            
            for p in products:
                pid = p.get('id')
                nome = p.get('productName', '')
                nome_norm = remover_acentos(nome)
                
                # Filtro rigoroso: todas as palavras da busca devem estar no nome
                if pid not in vistos and p.get('available') and all(k in nome_norm for k in palavras):
                    vistos.add(pid)
                    
                    # Processamento de preço
                    sales = p.get('price', {}).get('sales', {})
                    preco_venda = float(sales.get('value', 0)) if sales.get('value') else 0.0
                    
                    preco_final = preco_venda
                    has_promo = False
                    for flag in p.get('flagtypes', []):
                        if flag.get('valueFlag'):
                            val = float(flag['valueFlag'])
                            if val < preco_final:
                                preco_final = val
                                has_promo = True
                    
                    label = calcular_preco_unitario_nagumo(preco_final, nome, p.get('productMeasureValue'))
                    
                    img_data = p.get('images', {}).get('large', [{}])
                    
                    all_filtered.append({
                        'productName': nome,
                        'preco_final': preco_final,
                        'preco_normal': preco_venda,
                        'has_promo': has_promo,
                        'calc_label': label,
                        'sort_val': extrair_valor_unitario(label),
                        'img_url': img_data[0].get('alt', DEFAULT_IMAGE_URL) if img_data else DEFAULT_IMAGE_URL,
                        'link': p.get('productShowFullUrl', '#'),
                        'brand': p.get('brand', 'N/A')
                    })
            
            # Se já achamos bastante coisa, não precisa continuar paginando
            if len(all_filtered) >= 12: break
            
            start += step
        except: break
            
    return sorted(all_filtered, key=lambda x: x['sort_val'])

# --- INTERFACE ---
st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")
st.markdown("<style>.block-container { padding-top: 0rem; } header {display: none;} div, span, strong { font-size: 0.75rem !important; } .price-tag { font-size: 1rem !important; font-weight: bold; } .off-tag { color: #d32f2f; font-weight: bold; }</style>", unsafe_allow_html=True)

st.markdown("<h6>🛒 Preços Nagumo - Loja 22</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Produto:", "Leite Integral").strip()

if termo:
    with st.spinner("⚡ Localizando ofertas..."):
        resultados = buscar_smart_nagumo(termo)
    
    if resultados:
        _, col, _ = st.columns([1, 2, 1])
        with col:
            st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='80'/><br><small>{len(resultados)} produtos encontrados.</small></p>", unsafe_allow_html=True)
            for p in resultados:
                preco_html = f"<span class='price-tag'>R$ {p['preco_final']:.2f}</span>"
                if p['has_promo'] and p['preco_normal'] > p['preco_final']:
                    desc = ((p['preco_normal'] - p['preco_final']) / p['preco_normal']) * 100
                    preco_html += f" <span class='off-tag'>({desc:.0f}% OFF)</span><br><span style='text-decoration:line-through; color:gray;'>R$ {p['preco_normal']:.2f}</span>"

                st.markdown(f"""
                    <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                        <a href='{p['link']}' target='_blank'><img src="{p['img_url']}" width="70" style="border-radius:5px; background:white;"/></a>
                        <div style="flex: 1;">
                            <a href='{p['link']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['productName']}</strong></a><br>
                            {preco_html}<br>
                            <div style="color: #666;">{p['calc_label']}</div>
                        </div>
                    </div>
                    <hr style='margin:8px 0; border:0; border-top:1px solid #eee;'/>
                """, unsafe_allow_html=True)
    else:
        st.warning("Nenhum produto encontrado com todos esses termos.")

components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
