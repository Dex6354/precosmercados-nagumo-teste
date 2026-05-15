import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re
import json
import html

# --- CONFIGURAÇÕES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"

def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def slugify(text):
    text = remover_acentos(text)
    text = re.sub(r'[^a-z0-9\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text

def calcular_preco_unitario(preco, desc, nome):
    if not preco: return "N/D"
    texto = remover_acentos(f"{nome} {desc}")
    m = re.search(r"(\d+[.,]?\d*)\s*(kg|l|g|ml|un)", texto)
    if m:
        try:
            val = float(m.group(1).replace(',', '.'))
            uni = m.group(2)
            if val > 0:
                if uni in ['kg', 'l']: return f"R$ {preco / val:.2f}/{uni}"
                if uni in ['g', 'ml']: return f"R$ {preco / (val/1000):.2f}/{'kg' if uni=='g' else 'L'}"
        except: pass
    return "Sem unidade"

def buscar_nagumo_grid(term, start=0):
    term_enc = requests.utils.quote(term)
    # Rota otimizada para o Grid de busca
    url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={term_enc}&start={start}&sz=20"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            # O Nagumo injeta o JSON dos produtos no atributo 'products' da tag search-card-grid neste HTML
            match = re.search(r'products="([^"]+)"', r.text)
            if match:
                return json.loads(html.unescape(match.group(1)))
    except: pass
    return []

st.set_page_config(page_title="Preços Nagumo", page_icon="🛒", layout="wide")

# CSS para esconder elementos desnecessários e centralizar layout
st.markdown("""
    <style>
        .block-container { padding-top: 0rem; }
        footer, #MainMenu, header { visibility: hidden; }
        div, span, strong, small { font-size: 0.75rem !important; }
        .product-container { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 0rem; }
        .product-info { flex: 1; word-break: break-word; }
        hr { border: none; border-top: 1px solid #eee; margin: 10px 0; }
        [data-testid="stColumn"] {
            overflow-y: auto; max-height: 90vh; padding: 10px; border: 1px solid #f0f2f6; border-radius: 8px;
            max-width: 600px; margin: auto;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h6>🛒 Nagumo Search Grid</h6>", unsafe_allow_html=True)
termo = st.text_input("🔎 Produto:", "Cenoura").strip()

if termo:
    palavras_chave = remover_acentos(termo).split()
    with st.spinner("🔍 Coletando todos os itens..."):
        # Busca a primeira e a segunda página (start 0 e 20) para pegar os 24+ itens
        raw_data = buscar_nagumo_grid(termo, start=0) + buscar_nagumo_grid(termo, start=20)
        
        final_list = []
        vistos = set()

        for p in raw_data:
            sku = str(p.get('id') or p.get('sku'))
            nome = p.get('productName') or p.get('name', '')
            if sku not in vistos and all(k in remover_acentos(nome) for k in palavras_chave):
                vistos.add(sku)
                
                # Preço
                preco = p.get('price', {})
                val_final = preco.get('sales', {}).get('value', 0) if isinstance(preco, dict) else float(preco or 0)
                
                # Cálculo unitário
                label = calcular_preco_unitario(val_final, p.get('description', ''), nome)
                
                # Imagem segura
                img = DEFAULT_IMAGE_URL
                try:
                    items = p.get('items', [])
                    if items: 
                        img = items[0].get('images', [{}])[0].get('imageUrl', img)
                except: pass

                final_list.append({
                    'nome': nome, 
                    'preco': val_final, 
                    'unit': label, 
                    'img': img,
                    'url': f"https://www.nagumo.com.br/p/{sku}/{slugify(nome)}"
                })

    col_esq, col_central, col_dir = st.columns([1, 2, 1])
    
    with col_central:
        st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='80'/><br><small>{len(final_list)} itens encontrados</small></p>", unsafe_allow_html=True)
        for p in final_list:
            st.markdown(f"""
                <div class='product-container'>
                    <a href='{p['url']}' target='_blank'><img src="{p['img']}" width="70" style="background:white; border-radius:5px; border: 1px solid #f0f0f0;"/></a>
                    <div class='product-info'>
                        <a href='{p['url']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['nome']}</strong></a><br>
                        <span style='font-weight:bold; font-size:1rem;'>R$ {p['preco']:.2f}</span><br>
                        <div style='color:gray;'>{p['unit']}</div>
                    </div>
                </div><hr>
            """, unsafe_allow_html=True)

    components.html("<script>window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]').forEach(c => c.scrollTop = 0);</script>", height=0)
