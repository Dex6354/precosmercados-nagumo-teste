import streamlit as st
import requests
import re
import unicodedata

st.set_page_config(page_title="Preço Nagumo", page_icon="🛒")

st.markdown("""
    <style>
        .block-container { padding-top: 0rem; }
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        div, span, strong, small {
            font-size: 0.75rem !important;
        }
        img {
            max-width: 100px;
            height: auto;
        }
        .info-cinza {
            color: gray;
            font-size: 0.8rem;
        }
        hr.product-separator {
            border: none;
            border-top: 1px solid #ccc;
            margin: 10px 0;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h5 style="display: flex; align-items: center;">
        <img src="https://institucional.nagumo.com.br/images/nagumo-2000.png" width="80" style="margin-right:8px; background-color: white; border-radius: 4px; padding: 2px;"/>
        Preço Nagumo
    </h5>
""", unsafe_allow_html=True)

termo = st.text_input("🛒Digite o nome do produto:")

def remover_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def contem_papel_toalha(texto):
    texto = remover_acentos(texto.lower())
    return "papel" in texto and "toalha" in texto

def extrair_info_papel_toalha(nome, descricao):
    texto_nome = remover_acentos(nome.lower())
    texto_desc = remover_acentos(descricao.lower())
    texto_completo = f"{texto_nome} {texto_desc}"

    if "200 folhas" in texto_nome:
        return None, None, 200, "200 folhas"

    if "2 rolos com 120 folhas" in texto_completo:
        return 2, None, 120, "2 rolos com 120 folhas"

    padroes = [
        r"(\d+)\s*rolos?.*?(\d+)\s*folhas",
        r"(\d+)\s*rolos?.*?cada.*?(\d+)\s*folhas",
        r"(\d+)\s*rolos?.*?contendo\s*(\d+)\s*folhas",
        r"(\d+)\s*rolos?.*?com\s*(\d+)\s*folhas",
        r"(\d+)\s*rolos?.*?e\s*(\d+)\s*folhas",
    ]
    for padrao in padroes:
        m = re.search(padrao, texto_completo)
        if m:
            rolos = int(m.group(1))
            folhas_por_rolo = int(m.group(2))
            total_folhas = rolos * folhas_por_rolo
            return rolos, folhas_por_rolo, total_folhas, f"{rolos} rolos, {folhas_por_rolo} folhas por rolo"

    m_folhas = re.search(r"(\d+)\s*folhas", texto_completo)
    if m_folhas:
        total_folhas = int(m_folhas.group(1))
        return None, None, total_folhas, f"{total_folhas} folhas"

    m_un = re.search(r"(\d+)\s*(un|unidades?)", texto_nome)
    if m_un:
        total = int(m_un.group(1))
        return None, None, total, f"{total} unidades"

    return None, None, None, None

def calcular_preco_unitario(preco_valor, descricao, nome, unidade_api=None):
    preco_unitario = "Sem unidade"
    texto_completo = f"{descricao} {nome}".lower()

    if contem_papel_toalha(texto_completo):
        rolos, folhas_por_rolo, total_folhas, texto_exibicao = extrair_info_papel_toalha(nome, descricao)
        if total_folhas and total_folhas > 0:
            preco_por_item = preco_valor / total_folhas
            return f"R$ {preco_por_item:.3f}/folha"
        return "Preço por folha: n/d"

    if "papel higi" in texto_completo:
        match_rolos = re.search(r"leve\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"\blv?\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"\blv?(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"\bl\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"c/\s*0*(\d+)", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"(\d+)\s*rolos?", texto_completo)
        if not match_rolos:
            match_rolos = re.search(r"(\d+)\s*(un|unidades?)", texto_completo)

        match_metros = re.search(r"(\d+[.,]?\d*)\s*(m|metros?|mt)", texto_completo)
        if match_rolos and match_metros:
            try:
                rolos = int(match_rolos.group(1))
                metros = float(match_metros.group(1).replace(',', '.'))
                if rolos > 0 and metros > 0:
                    preco_por_metro = preco_valor / rolos / metros
                    return f"R$ {preco_por_metro:.3f}/m"
            except:
                pass

    fontes = [descricao.lower(), nome.lower()]
    for fonte in fontes:
        match_g = re.search(r"(\d+[.,]?\d*)\s*(g|gramas?)", fonte)
        if match_g:
            gramas = float(match_g.group(1).replace(',', '.'))
            if gramas > 0:
                return f"R$ {preco_valor / (gramas / 1000):.2f}/kg"

        match_kg = re.search(r"(\d+[.,]?\d*)\s*(kg|quilo)", fonte)
        if match_kg:
            kg = float(match_kg.group(1).replace(',', '.'))
            if kg > 0:
                return f"R$ {preco_valor / kg:.2f}/kg"

        match_ml = re.search(r"(\d+[.,]?\d*)\s*(ml|mililitros?)", fonte)
        if match_ml:
            ml = float(match_ml.group(1).replace(',', '.'))
            if ml > 0:
                return f"R$ {preco_valor / (ml / 1000):.2f}/L"

        match_l = re.search(r"(\d+[.,]?\d*)\s*(l|litros?)", fonte)
        if match_l:
            litros = float(match_l.group(1).replace(',', '.'))
            if litros > 0:
                return f"R$ {preco_valor / litros:.2f}/L"

        match_un = re.search(r"(\d+[.,]?\d*)\s*(un|unidades?)", fonte)
        if match_un:
            unidades = float(match_un.group(1).replace(',', '.'))
            if unidades > 0:
                return f"R$ {preco_valor / unidades:.2f}/un"

    if unidade_api:
        unidade_api = unidade_api.lower()
        if unidade_api == 'kg':
            return f"R$ {preco_valor:.2f}/kg"
        elif unidade_api == 'g':
            return f"R$ {preco_valor * 1000:.2f}/kg"
        elif unidade_api == 'l':
            return f"R$ {preco_valor:.2f}/L"
        elif unidade_api == 'ml':
            return f"R$ {preco_valor * 1000:.2f}/L"
        elif unidade_api == 'un':
            return f"R$ {preco_valor:.2f}/un"

    return preco_unitario

def extrair_valor_unitario(preco_unitario):
    match = re.search(r"R\$ (\d+[.,]?\d*)", preco_unitario)
    if match:
        return float(match.group(1).replace(',', '.'))
    return float('inf')

def buscar_nagumo(term="banana"):
    url = "https://nextgentheadless.instaleap.io/api/v3"
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://www.nagumo.com",
        "Referer": "https://www.nagumo.com/",
        "User-Agent": "Mozilla/5.0",
        "apollographql-client-name": "Ecommerce SSR",
        "apollographql-client-version": "0.11.0"
    }
    payload = {
        "operationName": "SearchProducts",
        "variables": {
            "searchProductsInput": {
                "clientId": "NAGUMO",
                "storeReference": "22",
                "currentPage": 1,
                "minScore": 1,
                "pageSize": 100,
                "search": [{"query": term}],
                "filters": {},
                "googleAnalyticsSessionId": ""
            }
        },
        "query": """
        query SearchProducts($searchProductsInput: SearchProductsInput!) {
          searchProducts(searchProductsInput: $searchProductsInput) {
            products {
              name
              price
              photosUrl
              sku
              stock
              description
              unit
              promotion {
                isActive
                type
                conditions {
                  price
                  priceBeforeTaxes
                }
              }
            }
          }
        }
        """
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    return data.get("data", {}).get("searchProducts", {}).get("products", [])

if termo:
    with st.spinner("🔍 Buscando produtos..."):
        # Fazer 2 buscas separadas
        palavras_busca = remover_acentos(termo).split()
        produtos_todos = []

        for palavra in palavras_busca:
            produtos_todos.extend(buscar_nagumo(palavra))

        # Remover duplicatas (por SKU)
        produtos_unicos = {p['sku']: p for p in produtos_todos}.values()

        # Filtrar manualmente os que contêm TODAS as palavras no nome+descrição
        produtos_filtrados = []
        for produto in produtos_unicos:
            texto = f"{produto['name']} {produto.get('description', '')}"
            texto_normalizado = remover_acentos(texto)
            if all(p in texto_normalizado for p in palavras_busca):
                produtos_filtrados.append(produto)

        produtos = produtos_filtrados


    st.markdown(f"<small>🔎 {len(produtos)} produto(s) encontrado(s).</small>", unsafe_allow_html=True)

    for p in produtos:
        preco_normal = p.get("price", 0)
        promocao = p.get("promotion") or {}
        cond = promocao.get("conditions") or []
        preco_desconto = None
        if promocao.get("isActive") and isinstance(cond, list) and len(cond) > 0:
            preco_desconto = cond[0].get("price")

        preco_exibir = preco_desconto if preco_desconto else preco_normal

        p['preco_unitario_str'] = calcular_preco_unitario(preco_exibir, p['description'], p['name'], p.get("unit"))
        p['preco_unitario_valor'] = extrair_valor_unitario(p['preco_unitario_str'])

        titulo = p['name']
        texto_completo = p['name'] + " " + p['description']
        if contem_papel_toalha(texto_completo):
            rolos, folhas_por_rolo, total_folhas, texto_exibicao = extrair_info_papel_toalha(p['name'], p['description'])
            if texto_exibicao:
                titulo += f" <span class='info-cinza'>({texto_exibicao})</span>"

        if "papel higi" in remover_acentos(titulo.lower()):
            titulo_lower = remover_acentos(titulo.lower())
            if "folha simples" in titulo_lower:
                titulo = re.sub(r"(folha simples)", r"<span style='color:red; font-weight:bold;'>\1</span>", titulo, flags=re.IGNORECASE)
            if "folha dupla" in titulo_lower or "folha tripla" in titulo_lower:
                titulo = re.sub(r"(folha dupla|folha tripla)", r"<span style='color:green; font-weight:bold;'>\1</span>", titulo, flags=re.IGNORECASE)

        p['titulo_exibido'] = titulo

    produtos = sorted(produtos, key=lambda x: x['preco_unitario_valor'])

    for p in produtos:
        imagem = p['photosUrl'][0] if p.get('photosUrl') else ""
        preco_unitario = p['preco_unitario_str']
        preco = p['price']
        promocao = p.get("promotion") or {}
        cond = promocao.get("conditions") or []
        preco_desconto = None
        if promocao.get("isActive") and isinstance(cond, list) and len(cond) > 0:
            preco_desconto = cond[0].get("price")

        if preco_desconto and preco_desconto < preco:
            desconto_percentual = ((preco - preco_desconto) / preco) * 100
            preco_html = f"""
                <span style='font-weight: bold; font-size: 1rem;'>R$ {preco_desconto:.2f}</span>
                <span style='color: red; font-size: 0.9rem;'> ({desconto_percentual:.0f}% OFF)</span><br>
                <span style='text-decoration: line-through; color: gray;'>R$ {preco:.2f}</span>
            """
        else:
            preco_html = f"R$ {preco:.2f}"

        st.markdown(f"""
            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 1rem; flex-wrap: wrap;">
                <div style="flex: 0 0 auto;">
                    <img src="{imagem}" width="100" style="border-radius:8px;">
                </div>
                <div style="flex: 1; word-break: break-word; overflow-wrap: anywhere;">
                    <strong>{p['titulo_exibido']}</strong><br>
                    <strong>{preco_html}</strong><br>
                    <div style="margin-top: 4px; font-size: 0.9em; color: #666;">{preco_unitario}</div>
                    <div style="color: gray; font-size: 0.8em;">Estoque: {p['stock']}</div>
                </div>
            </div>
            <hr class='product-separator' />
        """, unsafe_allow_html=True)
