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

def calcular_preco_unitario_nagumo(preco_valor, descricao, nome):
    if not preco_valor: return "Preço indisponível"
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

# --- REQUISIÇÃO CORRIGIDA ---
def buscar_nagumo(term, start=0, sz=20):
    term_encoded = requests.utils.quote(term)
    # URL de busca que o Nagumo usa para carregar o grid
    url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={term_encoded}&start={start}&sz={sz}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest", # Essencial para UpdateGrid
        "Accept": "*/*"
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        # O Nagumo coloca o JSON em products="...". Usamos um regex mais flexível.
        match = re.search(r'products="([^"]+)"', r.text)
        if match:
            json_data = html.unescape(match.group(1))
            return json.loads(json_data)
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
    return []

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        footer, #MainMenu, header { visibility: hidden; }
        div, span, strong, small { font-size: 0.75rem !important; }
        .product-container { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0rem; flex-wrap: wrap; }
        .product-info { flex: 1; word-break: break-word; }
        hr.product-separator { border: none; border-top: 1px solid #eee; margin: 10px 0; }
        [data-testid="stColumn"] {
            overflow-y: auto; max-height: 85vh; padding: 15px; border: 1px solid #f0f2f6; border-radius: 8px;
            max-width: 600px; margin-left: auto; margin-right: auto;
        }
        .stButton button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# Estado da sessão
if 'produtos' not in st.session_state: st.session_state.produtos = []
if 'offset' not in st.session_state: st.session_state.offset = 0
if 'termo_atual' not in st.session_state: st.session_state.termo_atual = ""

st.markdown("<h6>🛒 Preços Nagumo</h6>", unsafe_allow_html=True)
termo_input = st.text_input("🔎 Digite o nome do produto:", value="Banana").strip()

# Resetar se o termo mudar
if termo_input != st.session_state.termo_atual:
    st.session_state.produtos = []
    st.session_state.offset = 0
    st.session_state.termo_atual = termo_input

def executar_busca():
    if not st.session_state.termo_atual: return
    
    novos_raw = buscar_nagumo(st.session_state.termo_atual, start=st.session_state.offset, sz=ITENS_POR_PAGINA)
    
    if novos_raw:
        palavras_filtro = remover_acentos(st.session_state.termo_atual).split()
        vistos = {p['sku'] for p in st.session_state.produtos}
        
        for p in novos_raw:
            sku = p.get('id') or p.get('sku')
            nome = p.get('productName') or ""
            desc = p.get('description') or ""
            
            # Filtro básico de relevância
            if sku not in vistos and all(k in remover_acentos(f"{nome} {desc}") for k in palavras_filtro):
                vistos.add(sku)
                
                preco_obj = p.get('price', {})
                if isinstance(preco_obj, dict):
                    preco_final = preco_obj.get('sales', {}).get('value', 0)
                else:
                    try: preco_final = float(preco_obj)
                    except: preco_final = 0
                
                label = calcular_preco_unitario_nagumo(preco_final, desc, nome)
                
                st.session_state.produtos.append({
                    'sku': sku,
                    'nome': nome,
                    'preco': preco_final,
                    'unidade': label,
                    'sort_val': extrair_valor_unitario(label),
                    'url': f"https://www.nagumo.com.br/p/{sku}/{slugify(nome)}",
                    'raw': p
                })
        
        st.session_state.offset += ITENS_POR_PAGINA
        st.session_state.produtos.sort(key=lambda x: x['sort_val'])
    else:
        if st.session_state.offset == 0:
            st.warning("Nenhum produto encontrado.")

# Busca inicial
if st.session_state.termo_atual and not st.session_state.produtos:
    executar_busca()

# Renderização
if st.session_state.produtos:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='100'/></p>", unsafe_allow_html=True)
        
        for p in st.session_state.produtos:
            # Lógica de imagem
            img = DEFAULT_IMAGE_URL
            raw = p['raw']
            items = raw.get('items', [])
            if items and isinstance(items, list):
                imgs = items[0].get('images', [])
                if imgs: img = imgs[0].get('imageUrl', img)
            
            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['url']}' target='_blank'><img src="{img}" width="70" style="border-radius:5px; border:1px solid #eee;"/></a>
                    <div class='product-info'>
                        <strong>{p['nome']}</strong><br>
                        <span style='font-size:1rem !important; font-weight:bold;'>R$ {p['preco']:.2f}</span><br>
                        <span style='color:#666;'>{p['unidade']}</span>
                    </div>
                </div>
                <hr class='product-separator'/>
            """, unsafe_allow_html=True)

        if st.button("🔽 Carregar Mais Itens"):
            executar_busca()
            st.rerun()

components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
