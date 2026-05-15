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
ITENS_POR_PAGINA = 20

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

# --- REQUISIÇÃO COM PAGINAÇÃO ---
def buscar_nagumo(term, start=0, sz=20):
    term_encoded = requests.utils.quote(term)
    # Usando a URL de UpdateGrid para suportar a paginação (start e sz)
    url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={term_encoded}&start={start}&sz={sz}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        # O Nagumo injeta o JSON dos produtos em um atributo 'products' no HTML retornado
        match = re.search(r'products="([^"]+)"', r.text)
        if match:
            return json.loads(html.unescape(match.group(1)))
    except Exception as e:
        print(f"Erro na busca: {e}")
    return []

# --- INTERFACE ---
st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem; }
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

# Inicialização do estado para paginação
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []
if 'start_index' not in st.session_state:
    st.session_state.start_index = 0
if 'termo_anterior' not in st.session_state:
    st.session_state.termo_anterior = ""

termo = st.text_input("🔎 Digite o nome do produto:", "Banana").strip()

# Se o termo mudar, reseta a busca
if termo != st.session_state.termo_anterior:
    st.session_state.lista_produtos = []
    st.session_state.start_index = 0
    st.session_state.termo_anterior = termo

def processar_e_adicionar():
    palavras_chave = remover_acentos(termo).split()
    with st.spinner("🔍 Buscando itens..."):
        raw_data = buscar_nagumo(termo, start=st.session_state.start_index, sz=ITENS_POR_PAGINA)
        
        novos_itens = []
        vistos = {p['sku'] for p in st.session_state.lista_produtos}

        for p in raw_data:
            sku = p.get('id') or p.get('sku') or str(p.get('productName', ''))
            nome = p.get('productName') or p.get('name', '')
            desc = p.get('description', '') or ''
            
            if sku not in vistos and all(k in remover_acentos(f"{nome} {desc}") for k in palavras_chave):
                vistos.add(sku)
                
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
                novos_itens.append(p_processado)
        
        st.session_state.lista_produtos.extend(novos_itens)
        # Ordena a lista global pelo valor unitário
        st.session_state.lista_produtos.sort(key=lambda x: x['sort_val'])
        st.session_state.start_index += ITENS_POR_PAGINA

# Executa busca inicial se a lista estiver vazia
if termo and not st.session_state.lista_produtos:
    processar_e_adicionar()

if st.session_state.lista_produtos:
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='100'/></p>", unsafe_allow_html=True)
        st.markdown(f"<p align='center'><small>🔎 Mostrando {len(st.session_state.lista_produtos)} itens.</small></p>", unsafe_allow_html=True)
        
        for p in st.session_state.lista_produtos:
            raw = p['raw']
            img = DEFAULT_IMAGE_URL
            items = raw.get('items', [])
            
            if isinstance(items, list) and len(items) > 0:
                first_item_images = items[0].get('images', [])
                if first_item_images and isinstance(first_item_images, list):
                    img = first_item_images[0].get('imageUrl', img)
            elif 'images' in raw and isinstance(raw['images'], list) and len(raw['images']) > 0:
                img = raw['images'][0] if isinstance(raw['images'][0], str) else raw['images'][0].get('imageUrl', img)
            elif 'photosUrl' in raw and isinstance(raw['photosUrl'], list) and len(raw['photosUrl']) > 0:
                img = raw['photosUrl'][0]

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

        if st.button("🔽 Carregar mais itens"):
            processar_e_adicionar()
            st.rerun()

    components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
