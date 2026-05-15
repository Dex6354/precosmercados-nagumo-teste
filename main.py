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

def gerar_formas_variantes(termo):
    variantes = {termo}
    if termo.endswith("s"): variantes.add(termo[:-1])
    else: variantes.add(termo + "s")
    return list(variantes)

# --- LÓGICA DE CÁLCULO ---
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

# --- REQUISIÇÃO NAGUMO ---
def buscar_nagumo(term):
    all_products = []
    for start in [0, 20]:
        url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={term}&start={start:02d}&sz=20"
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                products = data.get('productsSearchResult', [])
                if not products: break
                all_products.extend(products)
            else: break
        except: break
    return all_products

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 0rem; }
        div, span, strong, small { font-size: 0.75rem !important; }
        .product-container { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; }
        .product-info { flex: 1; }
        .price-tag { font-size: 1rem !important; font-weight: bold; }
        .off-tag { color: #d32f2f; font-weight: bold; font-size: 0.7rem !important; }
        header[data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h6>🛒 Preços Nagumo</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Digite o nome do produto:", "Cenoura").strip()

if termo:
    termos_busca = gerar_formas_variantes(remover_acentos(termo))
    palavras_chave = remover_acentos(termo).split()

    with st.spinner("🔍 Buscando no Nagumo..."):
        raw_nagumo = []
        for t in termos_busca: raw_nagumo.extend(buscar_nagumo(t))
        
        vistos = set()
        nagumo_final = []
        for p in raw_nagumo:
            pid = p.get('id')
            
            # FILTRO: Disponibilidade e Duplicidade
            if pid and pid not in vistos and p.get('available') is True:
                vistos.add(pid)
                nome = p.get('productName', '')
                
                if all(k in remover_acentos(nome) for k in palavras_chave):
                    # Preço de Venda
                    price_obj = p.get('price', {}).get('sales', {})
                    try:
                        preco_venda = float(price_obj.get('value', 0))
                    except (TypeError, ValueError):
                        preco_venda = 0.0

                    # Preço "Meu Nagumo"
                    preco_final = preco_venda
                    has_promo = False
                    flags = p.get('flagtypes', [])
                    if flags and isinstance(flags, list):
                        val_flag = flags[0].get('valueFlag')
                        if val_flag:
                            try:
                                preco_final = float(val_flag)
                                has_promo = preco_final < preco_venda
                            except: pass

                    label = calcular_preco_unitario_nagumo(preco_final, nome, p.get('productMeasureValue'))
                    
                    p['calc_label'] = label
                    p['sort_val'] = extrair_valor_unitario(label)
                    p['preco_final'] = preco_final
                    p['preco_normal'] = preco_venda
                    p['has_promo'] = has_promo
                    
                    img_data = p.get('images', {}).get('medium', [{}])
                    p['img_url'] = img_data[0].get('absURL', DEFAULT_IMAGE_URL) if img_data else DEFAULT_IMAGE_URL
                    p['link'] = p.get('productShowFullUrl', '#')
                    
                    nagumo_final.append(p)
        
        nagumo_final = sorted(nagumo_final, key=lambda x: x['sort_val'])

    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='100'/><br><small>🔎 {len(nagumo_final)} itens disponíveis encontrados.</small></p>", unsafe_allow_html=True)
        
        for p in nagumo_final:
            preco_html = f"<span class='price-tag'>R$ {p['preco_final']:.2f}</span>"
            if p['has_promo']:
                desc = ((p['preco_normal'] - p['preco_final']) / p['preco_normal']) * 100
                preco_html += f" <span class='off-tag'>({desc:.0f}% OFF Meu Nagumo)</span><br><span style='text-decoration:line-through; color:gray;'>R$ {p['preco_normal']:.2f}</span>"

            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['link']}' target='_blank'>
                        <img src="{p['img_url']}" width="80" style="border-radius:8px; border:1px solid #eee; background: white;"/>
                    </a>
                    <div class='product-info'>
                        <a href='{p['link']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['productName']}</strong></a><br>
                        {preco_html}<br>
                        <div style="color: #666; margin-top:2px;">{p['calc_label']}</div>
                        <div style="color: gray; font-size: 0.7rem;">Marca: {p.get('brand', 'N/A')}</div>
                    </div>
                </div>
                <hr style='margin:10px 0; border:0; border-top:1px solid #eee;'/>
            """, unsafe_allow_html=True)

    components.html("<script>const cols = window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]'); cols.forEach(col => col.scrollTop = 0);</script>", height=0)
