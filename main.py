import streamlit as st
import streamlit.components.v1 as components
import requests
import unicodedata
import re
from bs4 import BeautifulSoup
from urllib.parse import quote

# --- CONFIGURAÇÕES E CONSTANTES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"
DEFAULT_IMAGE_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/sem-imagem.png"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.nagumo.com.br",
    "Referer": "https://www.nagumo.com.br/"
}

# --- FUNÇÕES UTILITÁRIAS ---
def remover_acentos(texto):
    if not texto:
        return ""

    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def gerar_formas_variantes(termo):
    variantes = {termo}

    if termo.endswith("s"):
        variantes.add(termo[:-1])
    else:
        variantes.add(termo + "s")

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
            rolos = int(match.group(1))
            folhas_por_rolo = int(match.group(3))

            return (
                rolos,
                folhas_por_rolo,
                rolos * folhas_por_rolo,
                f"{rolos} {match.group(2)}, {folhas_por_rolo} {match.group(4)}"
            )

        match = re.search(r'(\d+)\s*(folhas|toalhas)', texto)

        if match:
            return None, None, int(match.group(1)), f"{match.group(1)} {match.group(2)}"

    m_un = re.search(r"(\d+)\s*(un|unidades?)", texto_completo)

    if m_un:
        return None, None, int(m_un.group(1)), f"{m_un.group(1)} unidades"

    return None, None, None, None


def calcular_preco_unitario_nagumo(preco_valor, descricao, nome, unidade_api=None):
    texto_completo = f"{nome} {descricao}".lower()

    if contem_papel_toalha(texto_completo):
        rolos, folhas, total_folhas, txt = extrair_info_papel_toalha(nome, descricao)

        if total_folhas and total_folhas > 0:
            return f"R$ {preco_valor / total_folhas:.3f}/folha"

        return "Preço por folha: n/d"

    if "papel higi" in texto_completo:
        m_rolos = re.search(r"(leve\s*0*|lv?\s*0*|lv?|l\s*0*|c/\s*0*)(\d+)", texto_completo)

        if not m_rolos:
            m_rolos = re.search(r"(\d+)\s*(rolos?|un|unidades?)", texto_completo)

        m_metros = re.search(r"(\d+[.,]?\d*)\s*(m|metros?|mt)", texto_completo)

        if m_rolos and m_metros:
            try:
                rolos = int(m_rolos.group(2) if m_rolos.lastindex > 1 else m_rolos.group(1))
                metros = float(m_metros.group(1).replace(',', '.'))

                if rolos > 0 and metros > 0:
                    return f"R$ {preco_valor / rolos / metros:.3f}/m"
            except:
                pass

    fontes = [descricao.lower(), nome.lower()]

    for fonte in fontes:
        match_g = re.search(r"(\d+[.,]?\d*)\s*(g|gramas?)", fonte)

        if match_g and float(match_g.group(1).replace(',', '.')) > 0:
            return f"R$ {preco_valor / (float(match_g.group(1).replace(',', '.')) / 1000):.2f}/kg"

        match_kg = re.search(r"(\d+[.,]?\d*)\s*(kg|quilo)", fonte)

        if match_kg and float(match_kg.group(1).replace(',', '.')) > 0:
            return f"R$ {preco_valor / float(match_kg.group(1).replace(',', '.')):.2f}/kg"

        match_ml = re.search(r"(\d+[.,]?\d*)\s*(ml|mililitros?)", fonte)

        if match_ml and float(match_ml.group(1).replace(',', '.')) > 0:
            return f"R$ {preco_valor / (float(match_ml.group(1).replace(',', '.')) / 1000):.2f}/L"

        match_l = re.search(r"(\d+[.,]?\d*)\s*(l|litros?)", fonte)

        if match_l and float(match_l.group(1).replace(',', '.')) > 0:
            return f"R$ {preco_valor / float(match_l.group(1).replace(',', '.')):.2f}/L"

        match_un = re.search(r"(\d+[.,]?\d*)\s*(un|unidades?)", fonte)

        if match_un and float(match_un.group(1).replace(',', '.')) > 0:
            return f"R$ {preco_valor / float(match_un.group(1).replace(',', '.')):.2f}/un"

    if unidade_api:
        u = unidade_api.lower()

        if u == 'kg':
            return f"R$ {preco_valor:.2f}/kg"
        elif u == 'g':
            return f"R$ {preco_valor * 1000:.2f}/kg"
        elif u == 'l':
            return f"R$ {preco_valor:.2f}/L"
        elif u == 'ml':
            return f"R$ {preco_valor * 1000:.2f}/L"
        elif u == 'un':
            return f"R$ {preco_valor:.2f}/un"

    return "Sem unidade"


def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)

    if match:
        return float(match.group(1).replace(',', '.'))

    return float('inf')


# --- BUSCA GRAPHQL ---
def buscar_nagumo_graphql(term):
    url = "https://nextgentheadless.instaleap.io/api/v3"

    payload = {
        "operationName": "SearchProducts",
        "variables": {
            "searchProductsInput": {
                "clientId": "NAGUMO",
                "storeReference": "22",
                "currentPage": 1,
                "pageSize": 100,
                "search": [{"query": term}],
                "filters": {}
            }
        },
        "query": "query SearchProducts($searchProductsInput: SearchProductsInput!) { searchProducts(searchProductsInput: $searchProductsInput) { products { name price photosUrl sku stock description unit promotion { isActive conditions { price priceBeforeTaxes } } } } }"
    }

    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=15)

        if r.status_code != 200:
            return []

        data = r.json()

        return data.get('data', {}).get('searchProducts', {}).get('products', []) or []

    except Exception:
        return []


# --- FALLBACK HTML ---
# Corrige casos como CENOURA onde o GraphQL não retorna todos os itens
# mas o produto existe normalmente no site.
def buscar_nagumo_html(term):
    produtos = []

    try:
        url = f"https://www.nagumo.com.br/search?q={quote(term)}"

        r = requests.get(url, headers=HEADERS, timeout=15)

        if r.status_code != 200:
            return []

        soup = BeautifulSoup(r.text, 'html.parser')

        html = soup.get_text(" ", strip=True)

        # Extrai URLs de produtos
        links = set(
            re.findall(
                r'https://www\.nagumo\.com\.br/categoria/[^\s\"\']+\.html',
                html
            )
        )

        for link in links:
            try:
                slug = link.split('-')[-1].replace('.html', '')

                nome = link.split('/')[-1]
                nome = nome.rsplit('-', 1)[0]
                nome = nome.replace('-', ' ').title()

                produtos.append({
                    'name': nome,
                    'description': '',
                    'price': 0,
                    'photosUrl': [DEFAULT_IMAGE_URL],
                    'sku': slug,
                    'stock': 1,
                    'unit': 'un',
                    'promotion': None,
                    'url_final': link,
                    'fallback_html': True
                })

            except:
                pass

    except:
        pass

    return produtos


# --- BUSCA PRINCIPAL ---
def buscar_produtos_completo(termo):
    termos_busca = gerar_formas_variantes(remover_acentos(termo))
    palavras_chave = remover_acentos(termo).split()

    raw_nagumo = []

    # Busca GraphQL
    for t in termos_busca:
        raw_nagumo.extend(buscar_nagumo_graphql(t))

    # Fallback HTML
    raw_nagumo.extend(buscar_nagumo_html(termo))

    vistos_nagumo = set()
    nagumo_final = []

    for p in raw_nagumo:
        sku = str(p.get('sku', '')).strip()

        if not sku or sku in vistos_nagumo:
            continue

        vistos_nagumo.add(sku)

        nome = p.get('name', '')
        desc = p.get('description', '')

        texto = remover_acentos(f"{nome} {desc}")

        # Corrigido:
        # Antes exigia TODAS as palavras exatas.
        # Agora aceita correspondência parcial.
        score = sum(1 for k in palavras_chave if k in texto)

        if palavras_chave and score == 0:
            continue

        promo = p.get('promotion') or {}
        cond = promo.get('conditions') or []

        preco_normal = p.get('price', 0)

        preco_final = (
            cond[0].get('price')
            if (promo.get('isActive') and cond)
            else preco_normal
        )

        if not p.get('url_final'):
            p['url_final'] = (
                f"https://www.nagumo.com.br/categoria/departamentos/p/"
                f"{slugify(nome)}-{sku}.html"
            )

        label = calcular_preco_unitario_nagumo(
            preco_final,
            desc,
            nome,
            p.get('unit')
        )

        p['unit_label'] = label
        p['sort_val'] = extrair_valor_unitario(label)
        p['preco_final'] = preco_final
        p['preco_normal'] = preco_normal

        nagumo_final.append(p)

    return sorted(nagumo_final, key=lambda x: x['sort_val'])


# --- INTERFACE STREAMLIT ---
st.set_page_config(
    page_title="Preços Nagumo",
    page_icon="🛒",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 0rem;
}

footer {
    visibility: hidden;
}

#MainMenu {
    visibility: hidden;
}

.product-container {
    display: flex;
    gap: 10px;
    margin-bottom: 10px;
}

.product-image-box {
    flex: 0 0 auto;
}

.product-info {
    flex: 1;
}

img {
    max-width: 100px;
    height: auto;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h4>🛒 Preços Nagumo</h4>", unsafe_allow_html=True)

termo = st.text_input(
    "🔎 Digite o nome do produto:",
    "cenoura"
).strip()

if termo:
    with st.spinner("🔍 Buscando produtos..."):
        produtos = buscar_produtos_completo(termo)

    st.markdown(
        f"<small>{len(produtos)} produto(s) encontrado(s)</small>",
        unsafe_allow_html=True
    )

    if not produtos:
        st.warning("Nenhum produto encontrado")

    for p in produtos:
        imgs = p.get('photosUrl')

        img = (
            imgs[0]
            if isinstance(imgs, list) and imgs
            else DEFAULT_IMAGE_URL
        )

        preco_normal = p['preco_normal']
        preco_final = p['preco_final']

        if preco_final < preco_normal:
            desconto = ((preco_normal - preco_final) / preco_normal) * 100

            preco_html = (
                f"<span style='font-weight:bold'>R$ {preco_final:.2f}</span> "
                f"<span style='color:red'>({desconto:.0f}% OFF)</span><br>"
                f"<span style='text-decoration:line-through;color:gray'>"
                f"R$ {preco_normal:.2f}</span>"
            )
        else:
            preco_html = f"<span style='font-weight:bold'>R$ {preco_final:.2f}</span>"

        st.markdown(f"""
        <div class='product-container'>
            <a href='{p['url_final']}' target='_blank' class='product-image-box'>
                <img src='{img}' width='80'>
            </a>

            <div class='product-info'>
                <a href='{p['url_final']}' target='_blank'
                   style='text-decoration:none;color:inherit;'>
                    <strong>{p['name']}</strong>
                </a><br>

                {preco_html}<br>

                <div style='color:#666;'>
                    {p['unit_label']}
                </div>

                <div style='color:gray;'>
                    Estoque: {p.get('stock', 0)}
                </div>
            </div>
        </div>
        <hr>
        """, unsafe_allow_html=True)

    components.html(
        """
        <script>
            window.parent.scrollTo(0, 0);
        </script>
        """,
        height=0
    )
