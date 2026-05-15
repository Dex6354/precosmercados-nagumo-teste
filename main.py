import streamlit as st
import requests
import json
import html
from bs4 import BeautifulSoup

# --- CONFIGURAÇÕES ---
BASE_URL = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid"

def buscar_produtos_nagumo(termo, total_itens=40):
    todos_produtos = []
    itens_por_pagina = 20
    
    # Realiza múltiplas chamadas para carregar mais itens
    for start in range(0, total_itens, itens_por_pagina):
        params = {
            'q': termo,
            'start': start,
            'sz': itens_por_pagina,
            'srule': 'Relevance'
        }
        
        try:
            response = requests.get(BASE_URL, params=params, timeout=10)
            if response.status_status == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # O Nagumo retorna os dados em um atributo 'products' dentro desta tag específica
                grid_tag = soup.find('search-card-grid')
                
                if grid_tag and grid_tag.get('products'):
                    # Decodifica as entidades HTML e carrega o JSON
                    produtos_json = html.unescape(grid_tag.get('products'))
                    lista_produtos = json.loads(produtos_json)
                    todos_produtos.extend(lista_produtos)
                else:
                    break # Para se não encontrar mais a tag de produtos
            else:
                break
        except Exception as e:
            st.error(f"Erro na chamada start={start}: {e}")
            break
            
    return todos_produtos

# --- INTERFACE STREAMLIT ---
st.title("Monitor Nagumo - Carregar Mais Itens")
termo_busca = st.text_input("O que você procura?", "cenoura")
quantidade = st.sidebar.slider("Quantidade de itens", 20, 100, 40, step=20)

if st.button("Pesquisar"):
    resultados = buscar_produtos_nagumo(termo_busca, total_itens=quantidade)
    
    if resultados:
        st.write(def_found := f"Encontrados {len(resultados)} produtos.")
        
        for p in resultados:
            # Extração baseada na estrutura JSON do atributo 'products'
            nome = p.get('productName', 'Sem nome')
            preco = p.get('price', {}).get('sales', {}).get('value', 0.0)
            img_list = p.get('images', {}).get('medium', [])
            img_url = img_list[0].get('absURL') if img_list else ""
            link_final = p.get('productShowFullUrl', '#')

            with st.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    if img_url: st.image(img_url, width=100)
                with col2:
                    st.markdown(f"**[{nome}]({link_final})**")
                    st.write(f"R$ {preco:.2f}")
                st.divider()
    else:
        st.warning("Nenhum produto encontrado.")
