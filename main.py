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
    termo = remover_acentos(termo)
    variantes = {termo}
    if termo.endswith("s"): 
        variantes.add(termo[:-1])
    else: 
        # Lógica simples para plural em português
        if termo.endswith(("r", "z")): variantes.add(termo + "es")
        else: variantes.add(termo + "s")
    return list(variantes)

def slugify(text):
    text = remover_acentos(text)
    text = re.sub(r'[^a-z0-9\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text

# --- LÓGICA DE CÁLCULO NAGUMO ---
def contem_papel_toalha(texto):
    texto = remover_acentos(texto.lower())
    return "papel" in texto and "toalha" in texto

def extrair_info_papel_toalha(nome, descricao):
    texto_nome = remover_acentos(nome.lower())
    texto_completo = f"{texto_nome} {remover_acentos(descricao.lower())}"

    for texto in [texto_nome, texto_completo]:
        match = re.search(r'(\d+)\s*(un|unidades?|rolos?)\s*.*?(\d+)\s*(folhas|toalhas)', texto)
        if match:
            rolos, folhas_por_rolo = int(match.group(1)), int(match.group(3))
            return rolos, folhas_por_rolo, rolos * folhas_por_rolo, f"{rolos} {match.group(2)}, {folhas_por_rolo} {match.group(4)}"
        match = re.search(r'(\d+)\s*(folhas|toalhas)', texto)
        if match: return None, None, int(match.group(1)), f"{match.group(1)} {match.group(2)}"
    
    m_un = re.search(r"(\d+)\s*(un|unidades?)", texto_completo)
    if m_un: return None, None, int(m_un.group(1)), f"{m_un.group(1)} unidades"
    return None, None, None, None

def calcular_preco_unitario_nagumo(preco_valor, descricao, nome, unidade_api=None):
    texto_completo = f"{nome} {descricao}".lower()
    if contem_papel_toalha(texto_completo):
        rolos, folhas, total_folhas, txt = extrair_info_papel_toalha(nome, descricao)
        if total_folhas and total_folhas > 0: return f"R$ {preco_valor / total_folhas:.3f}/folha"
        return "Preço por folha: n/d"

    if "papel higi" in texto_completo:
        m_rolos = re.search(r"(leve\s*0*|lv?\s*0*|lv?|l\s*0*|c/\s*0*)(\d+)", texto_completo)
        if not m_rolos: m_rolos = re.search(r"(\d+)\s*(rolos?|un|unidades?)", texto_completo)
        m_metros = re.search(r"(\d+[.,]?\d*)\s*(m|metros?|mt)", texto_completo)
        if m_rolos and m_metros:
            try:
                rolos = int(m_rolos.group(2) if m_rolos.lastindex > 1 else m_rolos.group(1))
                metros = float(m_metros.group(1).replace(',', '.'))
                if rolos > 0 and metros > 0: return f"R$ {preco_valor / rolos / metros:.3f}/m"
            except: pass

    fontes = [descricao.lower(), nome.lower()]
    for fonte in fontes:
        match_g = re.search(r"(\d+[.,]?\d*)\s*(g|gramas?)", fonte)
        if match_g and float(match_g.group(1).replace(',', '.')) > 0: return f"R$ {preco_valor / (float(match_g.group(1).replace(',', '.')) / 1000):.2f}/kg"
        match_kg = re.search(r"(\d+[.,]?\d*)\s*(kg|quilo)", fonte)
        if match_kg and float(match_kg.group(1).replace(',', '.')) > 0: return f"R$ {preco_valor / float(match_kg.group(1).replace(',', '.')):.2f}/kg"
        match_ml = re.search(r"(\d+[.,]?\d*)\s*(ml|mililitros?)", fonte)
        if match_ml and float(match_ml.group(1).replace(',', '.')) > 0: return f"R$ {preco_valor / (float(match_ml.group(1).replace(',', '.')) / 1000):.2f}/L"
        match_l = re.search(r"(\d+[.,]?\d*)\s*(l|litros?)", fonte)
        if match_l and float(match_l.group(1).replace(',', '.')) > 0: return f"R$ {preco_valor / float(match_l.group(1).replace(',', '.')):.2f}/L"
        match_un = re.search(r"(\d+[.,]?\d*)\s*(un|unidades?)", fonte)
        if match_un and float(match_un.group(1).replace(',', '.')) > 0: return f"R$ {preco_valor / float(match_un.group(1).replace(',', '.')):.2f}/un"

    if unidade_api:
        u = unidade_api.lower()
        if u == 'kg': return f"R$ {preco_valor:.2f}/kg"
        elif u == 'g': return f"R$ {preco_valor * 1000:.2f}/kg"
        elif u == 'l': return f"R$ {preco_valor:.2f}/L"
        elif u == 'ml': return f"R$ {preco_valor * 1000:.2f}/L"
        elif u == 'un': return f"R$ {preco_valor:.2f}/un"
    return "Sem unidade"

def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)
    if match: return float(match.group(1).replace(',', '.'))
    return float('inf')

# --- REQUISIÇÃO NAGUMO ---
def buscar_nagumo(term):
    url = "https://nextgentheadless.instaleap.io/api/v3"
    headers = {"Content-Type": "application/json", "Origin": "https://www.nagumo.com", "User-Agent": "Mozilla/5.0"}
    payload = {
        "operationName": "SearchProducts",
        "variables": {"searchProductsInput": {"clientId": "NAGUMO", "storeReference": "22", "currentPage": 1, "pageSize": 50, "search": [{"query": term}], "filters": {}}},
        "query": "query SearchProducts($searchProductsInput: SearchProductsInput!) { searchProducts(searchProductsInput: $searchProductsInput) { products { name price photosUrl sku stock description unit promotion { isActive conditions { price priceBeforeTaxes } } } } }"
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        return r.json().get('data', {}).get('searchProducts', {}).get('products', []) or []
    except: return []

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 0rem; }
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        div, span, strong, small { font-size: 0.75rem !important; }
        img { max-width: 100px; height: auto; }
        .product-container { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0rem; flex-wrap: wrap; }
        .product-image-box { flex: 0 0 auto; text-decoration:none; }
        .product-info { flex: 1; word-break: break-word; overflow-wrap: anywhere; }
        hr.product-separator { border: none; border-top: 1px solid #eee; margin: 10px 0; }
        [data-testid="stColumn"] {
            overflow-y: auto; max-height: 90vh; padding: 10px; border: 1px solid #f0f2f6; border-radius: 8px;
            max-width: 600px; margin-left: auto; margin-right: auto; background: transparent;
            scrollbar-width: thin; scrollbar-color: gray transparent;
        }
        header[data-testid="stHeader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h6>🛒 Preços Nagumo</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Digite o nome do produto:", "Cenoura").strip()

if termo:
    termos_busca = gerar_formas_variantes(termo)
    palavras_chave = remover_acentos(termo).split()

    with st.spinner("🔍 Buscando no Nagumo..."):
        raw_nagumo = []
        for t in termos_busca: 
            raw_nagumo.extend(buscar_nagumo(t))
        
        vistos_nagumo = set()
        nagumo_final = []
        
        for p in raw_nagumo:
            sku = p.get('sku')
            if sku and sku not in vistos_nagumo:
                vistos_nagumo.add(sku)
                nome = p.get('name', '')
                desc = p.get('description', '') or ""
                texto_comparar = remover_acentos(f"{nome} {desc}")
                
                # Filtro mais flexível: se a busca for "cenoura", 
                # aceita se o termo estiver contido, mesmo que existam outras palavras
                if any(t in texto_comparar for t in termos_busca):
                    promo = p.get('promotion') or {}
                    cond = promo.get('conditions') or []
                    preco_normal = p.get('price', 0)
                    preco_final = cond[0].get('price') if (promo.get('isActive') and cond) else preco_normal
                    
                    p['url_final'] = f"https://www.nagumo.com.br/categoria/departamentos/p/{slugify(nome)}-{sku}.html"
                    label = calcular_preco_unitario_nagumo(preco_final, desc, nome, p.get('unit'))
                    p['unit_label'] = label
                    p['sort_val'] = extrair_valor_unitario(label)
                    p['preco_final'] = preco_final
                    p['preco_normal'] = preco_normal
                    nagumo_final.append(p)
        
        nagumo_final = sorted(nagumo_final, key=lambda x: x['sort_val'] or 999)

    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(f"""
            <h5 style="display: flex; align-items: center; justify-content: center;">
                <img src="{LOGO_NAGUMO_URL}" width="100" alt="Nagumo" style="border-radius: 6px; border: 1.5px solid white; padding: 0px;"/>
            </h5>
        """, unsafe_allow_html=True)
        st.markdown(f"<p align='center'><small>🔎 {len(nagumo_final)} produto(s) encontrado(s).</small></p>", unsafe_allow_html=True)
        
        if not nagumo_final:
            st.warning("Nenhum produto encontrado.")
            
        for p in nagumo_final:
            imgs = p.get('photosUrl')
            img = imgs[0] if (isinstance(imgs, list) and imgs) else DEFAULT_IMAGE_URL
            
            titulo = p['name']
            texto_completo = p['name'] + " " + (p.get('description') or "")
            
            if contem_papel_toalha(texto_completo):
                _, _, _, texto_exibicao = extrair_info_papel_toalha(p['name'], p.get('description', ''))
                if texto_exibicao: titulo += f" <span style='color:gray; font-size:0.8rem;'>({texto_exibicao})</span>"
                
            if "papel higi" in remover_acentos(titulo.lower()):
                titulo = re.sub(r"(folha simples)", r"<span style='color:red; font-weight:bold;'>\1</span>", titulo, flags=re.IGNORECASE)
                titulo = re.sub(r"(folha dupla|folha tripla)", r"<span style='color:green; font-weight:bold;'>\1</span>", titulo, flags=re.IGNORECASE)

            preco_normal = p['preco_normal']
            preco_final = p['preco_final']
            if preco_final < preco_normal:
                desconto_percentual = ((preco_normal - preco_final) / preco_normal) * 100
                preco_html = f"<span style='font-weight: bold; font-size: 1rem;'>R$ {preco_final:.2f}</span> <span style='color: red; font-weight: bold;'> ({desconto_percentual:.0f}% OFF)</span><br><span style='text-decoration: line-through; color: gray;'>R$ {preco_normal:.2f}</span>"
            else:
                preco_html = f"<span style='font-weight: bold; font-size: 1rem;'>R$ {preco_normal:.2f}</span>"

            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['url_final']}' target='_blank' class='product-image-box'>
                        <img src="{img}" width="80" style="background-color: white; border-top-left-radius: 6px; border-top-right-radius: 6px; display: block;"/>
                        <img src="{LOGO_NAGUMO_URL}" width="80" style="border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; border: 1.5px solid white; display: block;"/>
                    </a>
                    <div class='product-info'>
                        <a href='{p['url_final']}' target='_blank' style='text-decoration:none; color:inherit;'><strong>{titulo}</strong></a><br>
                        <strong>{preco_html}</strong><br>
                        <div style="margin-top: 4px; font-size: 0.9em; color: #666;">{p['unit_label']}</div>
                        <div style="color: gray; font-size: 0.8em;">Estoque: {p.get('stock', 0)}</div>
                    </div>
                </div>
                <hr class='product-separator' />
            """, unsafe_allow_html=True)

    components.html(
        f"""
        <script>
            const cols = window.parent.document.querySelectorAll('[data-testid="stColumn"]');
            cols.forEach(col => col.scrollTop = 0);
        </script>
        """, height=0, width=0
    )
