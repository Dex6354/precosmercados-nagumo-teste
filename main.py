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

def calcular_preco_unitario_nagumo(preco_valor, descricao, nome):
    if not preco_valor: return "Preço indisponível"
    texto_completo = f"{nome} {descricao}".lower()
    if contem_papel_toalha(texto_completo):
        _, _, total_folhas, _ = extrair_info_papel_toalha(nome, descricao)
        if total_folhas: return f"R$ {preco_valor / total_folhas:.3f}/folha"
    
    fontes = [descricao.lower(), nome.lower()]
    for fonte in fontes:
        m = re.search(r"(\d+[.,]?\d*)\s*(kg|l|g|ml|un)", fonte)
        if m:
            try:
                val = float(m.group(1).replace(',', '.'))
                uni = m.group(2)
                if val <= 0: continue
                if uni in ['kg', 'l']: return f"R$ {preco_valor / val:.2f}/{uni}"
                if uni in ['g', 'ml']: return f"R$ {preco_valor / (val/1000):.2f}/{'kg' if uni=='g' else 'L'}"
            except: continue
    return "Sem unidade"

def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)
    return float(match.group(1).replace(',', '.')) if match else float('inf')

# --- REQUISIÇÃO PAGINADA ---
def buscar_nagumo(term):
    all_products = []
    start = 0
    sz = 24  # O Nagumo geralmente usa 24 como padrão
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # Máximo de 5 páginas para evitar travamentos, ajuste se necessário
    for _ in range(5):
        url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={requests.utils.quote(term)}&start={start}&sz={sz}"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            # Regex ajustada para capturar o atributo 'data-props' ou 'products' de forma mais flexível
            match = re.search(r'products="([^"]+)"', r.text)
            
            if match:
                decoded_json = html.unescape(match.group(1))
                batch = json.loads(decoded_json)
                
                if not batch or len(batch) == 0:
                    break
                
                all_products.extend(batch)
                
                # Se vier menos que o tamanho da página, chegamos ao fim
                if len(batch) < sz:
                    break
                start += sz
            else:
                break
        except Exception as e:
            st.error(f"Erro na busca: {e}")
            break
            
    return all_products

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
termo = st.text_input("🔎 Digite o nome do produto:", "Cenoura").strip()

if termo:
    palavras_chave = remover_acentos(termo).split()
    with st.spinner(f"🔍 Buscando '{termo}' em todas as páginas..."):
        raw_data = buscar_nagumo(termo)
        nagumo_final = []
        vistos = set()

        for p in raw_data:
            sku = str(p.get('id') or p.get('sku') or '')
            nome = p.get('productName') or p.get('name', '')
            desc = p.get('description', '') or ''
            
            if sku and sku not in vistos and all(k in remover_acentos(f"{nome} {desc}") for k in palavras_chave):
                vistos.add(sku)
                
                # Extração de preço
                preco_obj = p.get('price', {})
                if isinstance(preco_obj, dict):
                    preco_final = preco_obj.get('sales', {}).get('value', 0)
                else:
                    try: preco_final = float(preco_obj or 0)
                    except: preco_final = 0
                
                label = calcular_preco_unitario_nagumo(preco_final, desc, nome)
                
                p_processado = {
                    'sku': sku,
                    'display_name': nome,
                    'preco_final': preco_final,
                    'unit_label': label,
                    'sort_val': extrair_valor_unitario(label),
                    'url_final': f"https://www.nagumo.com.br/p/{sku}/{slugify(nome)}",
                    'raw': p
                }
                nagumo_final.append(p_processado)
        
        nagumo_final = sorted(nagumo_final, key=lambda x: x['sort_val'])

    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='100'/></p>", unsafe_allow_html=True)
        st.markdown(f"<p align='center'><small>🔎 {len(nagumo_final)} itens encontrados.</small></p>", unsafe_allow_html=True)
        
        for p in nagumo_final:
            raw = p['raw']
            img = DEFAULT_IMAGE_URL
            
            # Lógica robusta de imagem
            items = raw.get('items', [])
            if isinstance(items, list) and len(items) > 0:
                imgs = items[0].get('images', [])
                if imgs: img = imgs[0].get('imageUrl', img)
            elif 'images' in raw and raw['images']:
                first_img = raw['images'][0]
                img = first_img.get('imageUrl', img) if isinstance(first_img, dict) else first_img

            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['url_final']}' target='_blank' style='text-decoration:none;'>
                        <img src="{img}" width="80" style="border-radius: 6px; border: 1px solid #eee; background: white;"/>
                    </a>
                    <div class='product-info'>
                        <a href='{p['url_final']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['display_name']}</strong></a><br>
                        <span style='font-weight: bold; font-size: 1rem !important;'>R$ {p['preco_final']:.2f}</span><br>
                        <div style="color: #666;">{p['unit_label']}</div>
                    </div>
                </div>
                <hr class='product-separator' />
            """, unsafe_allow_html=True)

    components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
