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
    return f"R$ {preco_valor:.2f}/un" if medida_venda == "unity" else "---"

def extrair_valor_unitario(label):
    match = re.search(r"R\$ (\d+[.,]?\d*)", label)
    return float(match.group(1).replace(',', '.')) if match else float('inf')

# --- SISTEMA DE SESSÃO E DEBUG ---
def get_nagumo_session():
    if "nagumo_session" not in st.session_state:
        st.session_state.nagumo_session = requests.Session()
        st.session_state.nagumo_session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.nagumo.com.br/"
        })
    return st.session_state.nagumo_session

def listar_lojas():
    session = get_nagumo_session()
    url = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Stores-AvailableStores"
    try:
        r = session.get(url, timeout=10)
        return r.json().get('stores', [])
    except:
        return []

def selecionar_loja(store_id):
    session = get_nagumo_session()
    # Rota do HAR para atualizar a loja selecionada
    url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Stores-UpdateSelectedStore?storeID={store_id}&pickupStoreID={store_id}"
    session.get(url, timeout=10)
    # Forçar cookies manuais conforme o HAR
    session.cookies.set("dw_store", store_id, domain="www.nagumo.com.br")
    session.cookies.set("hasSelectedStore", store_id, domain="www.nagumo.com.br")

# --- REQUISIÇÃO DE BUSCA ---
def buscar_nagumo(term, store_id):
    session = get_nagumo_session()
    all_products = []
    for start in [0, 20]:
        start_str = f"{start:02d}"
        url = f"https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid?q={term}&start={start_str}&sz=20"
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                products = data.get('productsSearchResult', [])
                if not products: break
                all_products.extend(products)
            else: break
        except: break
    return all_products

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Debug Nagumo", page_icon="⚙️", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 1rem; }
        div, span, strong, small { font-size: 0.75rem !important; }
        header[data-testid="stHeader"] { display: none; }
        .stSelectbox label { font-weight: bold; color: red; }
    </style>
""", unsafe_allow_html=True)

# --- SEÇÃO DE DEBUG (SELEÇÃO DE LOJA) ---
with st.expander("🛠️ DEBUG: Configurar Loja e Sessão", expanded=True):
    lojas = listar_lojas()
    if lojas:
        opcoes_lojas = {f"{l['id']} - {l['name']}": l['id'] for l in lojas}
        # Localiza a loja 22 por padrão se estiver na lista
        default_idx = list(opcoes_lojas.values()).index("22") if "22" in opcoes_lojas.values() else 0
        
        loja_selecionada_label = st.selectbox("Selecione a Loja para fixar no Cookie:", list(opcoes_lojas.keys()), index=default_idx)
        store_id_atual = opcoes_lojas[loja_selecionada_label]
        
        if st.button("Fixar Loja Selecionada"):
            selecionar_loja(store_id_atual)
            st.success(f"Loja {store_id_atual} fixada com sucesso!")
            st.rerun()
    else:
        st.error("Não foi possível carregar a lista de lojas.")
        store_id_atual = "22"

# --- BUSCA DE PRODUTOS ---
termo = st.text_input("🔎 Pesquisar produto:", "Banana").strip()

if termo:
    termos_busca = gerar_formas_variantes(remover_acentos(termo))
    palavras_chave = remover_acentos(termo).split()

    with st.spinner(f"🔍 Buscando na Loja {store_id_atual}..."):
        raw_nagumo = []
        for t in termos_busca: raw_nagumo.extend(buscar_nagumo(t, store_id_atual))
        
        vistos = set()
        nagumo_final = []
        for p in raw_nagumo:
            if p.get('available') is not True:
                continue
            
            pid = p.get('id')
            if not pid or pid in vistos:
                continue
            
            price_data = p.get('price', {})
            sales_obj = price_data.get('sales')
            if not sales_obj or sales_obj.get('value') is None:
                continue

            nome = p.get('productName', '')
            if all(k in remover_acentos(nome) for k in palavras_chave):
                vistos.add(pid)
                
                preco_venda = float(sales_obj.get('value', 0))
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
                img_list = p.get('images', {}).get('medium', [])
                img_url = img_list[0].get('absURL', DEFAULT_IMAGE_URL) if img_list else DEFAULT_IMAGE_URL
                
                nagumo_final.append({
                    'name': nome,
                    'preco_final': preco_final,
                    'preco_normal': preco_venda,
                    'has_promo': has_promo,
                    'calc_label': label,
                    'sort_val': extrair_valor_unitario(label),
                    'img_url': img_url,
                    'link': p.get('productShowFullUrl', '#')
                })
        
        nagumo_final = sorted(nagumo_final, key=lambda x: x['sort_val'])

    # Exibição
    _, col_center, _ = st.columns([1, 2, 1])
    with col_center:
        st.markdown(f"<p align='center'><img src='{LOGO_NAGUMO_URL}' width='100'/><br><small>📍 Loja Ativa: {store_id_atual} | 🔎 {len(nagumo_final)} itens.</small></p>", unsafe_allow_html=True)
        
        for p in nagumo_final:
            preco_html = f"<span style='font-size: 1rem; font-weight: bold;'>R$ {p['preco_final']:.2f}</span>"
            if p['has_promo']:
                desc = ((p['preco_normal'] - p['preco_final']) / p['preco_normal']) * 100
                preco_html += f" <span style='color:red; font-weight:bold;'>({desc:.0f}% OFF)</span><br><span style='text-decoration:line-through; color:gray;'>R$ {p['preco_normal']:.2f}</span>"

            st.markdown(f"""
                <div style='display: flex; gap: 10px; margin-bottom: 10px;'>
                    <a href='{p['link']}' target='_blank'><img src="{p['img_url']}" width="80" style="border-radius:8px; border:1px solid #eee;"/></a>
                    <div style='flex: 1;'>
                        <a href='{p['link']}' target='_blank' style='text-decoration:none; color:black;'><strong>{p['name']}</strong></a><br>
                        {preco_html}<br>
                        <div style="color: #666;">{p['calc_label']}</div>
                    </div>
                </div>
                <hr style='margin:10px 0; border:0; border-top:1px solid #eee;'/>
            """, unsafe_allow_html=True)

# SCRIPT PARA ROLAR AO TOPO
components.html("<script>const cols = window.parent.document.querySelectorAll('[data-testid=\"stColumn\"]'); cols.forEach(col => col.scrollTop = 0);</script>", height=0)
