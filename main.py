import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re
import json
import html

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
def contem_papel_toalha(texto):
    texto = remover_acentos(texto.lower())
    return "papel" in texto and "toalha" in texto

def extrair_info_papel_toalha(nome, descricao):
    texto_nome = remover_acentos(nome.lower())
    texto_completo = f"{texto_nome} {remover_acentos(descricao.lower())}"
    for texto in [texto_nome, texto_completo]:
        match = re.search(r'(\d+)\s*(un|unidades?|rolos?)\s*.*?(\d+)\s*(folhas|toalhas)', texto)
        if match:
            rolos, folhas = int(match.group(1)), int(match.group(3))
            return rolos, folhas, rolos * folhas, f"{rolos} {match.group(2)}, {folhas} {match.group(4)}"
    return None, None, None, None

def calcular_preco_unitario_nagumo(preco_valor, descricao, nome, unidade_api=None):
    texto_completo = f"{nome} {descricao}".lower()
    if contem_papel_toalha(texto_completo):
        _, _, total_folhas, _ = extrair_info_papel_toalha(nome, descricao)
        if total_folhas: return f"R$ {preco_valor / total_folhas:.3f}/folha"
    
    # Lógica simplificada de KG/L/UN
    fontes = [descricao.lower(), nome.lower()]
    for fonte in fontes:
        m = re.search(r"(\d+[.,]?\d*)\s*(kg|l|g|ml|un)", fonte)
        if m:
            val = float(m.group(1).replace(',', '.'))
            uni = m.group(2)
            if uni == 'kg' or uni == 'l': return f"R$ {preco_valor / val:.2f}/{uni}"
            if uni == 'g' or uni == 'ml': return f"R$ {preco_valor / (val/1000):.2f}/{'kg' if uni=='g' else 'L'}"
    return "Sem unidade"

def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)
    return float(match.group(1).replace(',', '.')) if match else float('inf')

# --- REQUISIÇÃO VIA REGEX ---
def buscar_nagumo(term):
    term_encoded = requests.utils.quote(term)
    url = f"https://www.nagumo.com.br/busca?q={term_encoded}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'products="([^"]+)"', r.text)
        if match:
            return json.loads(html.unescape(match.group(1)))
    except: pass
    return []

# --- INTERFACE ---
st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 0rem; }
        footer, #MainMenu, header { visibility: hidden; }
        div, span, strong, small { font-size: 0.75rem !important; }
        .product-container { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0rem; flex-wrap: wrap; }
        .product-info { flex: 1; word-break: break-word; }
        hr.product-separator { border: none; border-top: 1px solid #eee; margin: 10px 0; }
        [data-testid="stColumn"] {
            overflow-y: auto; max-height: 90vh; padding: 10px; border: 1px solid #f0f2f6; border-radius: 8px;
            max-width: 600px; margin-left: auto; margin-right: auto;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h6>🛒 Preços Nagumo</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Digite o nome do produto:", "Banana").strip()

if termo:
    palavras_chave = remover_acentos(termo).split()
    with st.spinner("🔍 Buscando..."):
        raw_data = buscar_nagumo(termo)
        nagumo_final = []
        vistos = set()

        for p in raw_data:
            sku = p.get('sku') or p.get('id')
            nome = p.get('name', '')
            desc = p.get('description', '') or ''
            
            if sku not in vistos and all(k in remover_acentos(f"{nome} {desc}") for k in palavras_chave):
                vistos.add(sku)
                # Ajuste de Preço: o JSON injetado traz o preço direto ou em 'price'
                preco_final = float(p.get('price', 0))
                
                p['url_final'] = f"https://www.nagumo.com.br/p/{sku}/{slugify(nome)}"
                label = calcular_preco_unitario_nagumo(preco_final, desc, nome)
                p['unit_label'] = label
                p['sort_val'] = extrair_valor_unitario(label)
                p['preco_final'] = preco_final
                nagumo_final.append(p)
        
        nagumo_final = sorted(nagumo_final, key=lambda x: x['sort_val'])

    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='100'/></p>", unsafe_allow_html=True)
        st.markdown(f"<p align='center'><small>🔎 {len(nagumo_final)} itens.</small></p>", unsafe_allow_html=True)
        
        for p in nagumo_final:
            # Ajuste de Imagem: tenta 'images' ou 'photosUrl'
            imgs = p.get('images', []) or p.get('photosUrl', [])
            img = imgs[0] if (isinstance(imgs, list) and imgs) else DEFAULT_IMAGE_URL
            
            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['url_final']}' target='_blank' style='text-decoration:none;'>
                        <img src="{img}" width="80" style="border-radius: 6px; border: 1px solid #eee;"/>
                    </a>
                    <div class='product-info'>
                        <a href='{p['url_final']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['name']}</strong></a><br>
                        <span style='font-weight: bold; font-size: 1rem !important;'>R$ {p['preco_final']:.2f}</span><br>
                        <div style="color: #666;">{p['unit_label']}</div>
                        <div style="color: gray; font-size: 0.7rem;">Estoque: {p.get('stock', 'Várias')}</div>
                    </div>
                </div>
                <hr class='product-separator' />
            """, unsafe_allow_html=True)

    components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
