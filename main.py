import streamlit as st
import requests
import json
import unicodedata
import re

# --- CONFIGURAÇÕES ---
LOGO_NAGUMO_URL = "https://rawcdn.githack.com/gymbr/precosmercados/main/logo-nagumo2.png"

def remover_acentos(texto):
    if not texto: return ""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def buscar_raw_nagumo(term):
    url = "https://nextgentheadless.instaleap.io/api/v3"
    headers = {"Content-Type": "application/json", "Origin": "https://www.nagumo.com", "User-Agent": "Mozilla/5.0"}
    payload = {
        "operationName": "SearchProducts",
        "variables": {
            "searchProductsInput": {
                "clientId": "NAGUMO",
                "storeReference": "22", # Verifique se sua loja física é a 22
                "currentPage": 1,
                "pageSize": 50,
                "search": [{"query": term}],
                "filters": {}
            }
        },
        "query": """query SearchProducts($searchProductsInput: SearchProductsInput!) { 
            searchProducts(searchProductsInput: $searchProductsInput) { 
                products { 
                    name price photosUrl sku stock description unit 
                    promotion { isActive conditions { price priceBeforeTaxes } } 
                } 
            } 
        }"""
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# --- INTERFACE DE DEBUG ---
st.set_page_config(page_title="Nagumo Debugger", layout="wide")
st.title("🐞 Nagumo API Debugger")

termo_busca = st.text_input("Termo de busca para teste:", "Cenoura")

if st.button("Executar Debug"):
    raw_data = buscar_raw_nagumo(termo_busca)
    
    st.divider()
    
    # 1. VISÃO GERAL DOS PRODUTOS ENCONTRADOS
    products = raw_data.get('data', {}).get('searchProducts', {}).get('products', [])
    
    if not products:
        st.error("A API não retornou NENHUM produto para este termo.")
        st.json(raw_data)
    else:
        st.success(f"A API retornou {len(products)} produtos.")
        
        # Tabela de inspeção rápida
        debug_list = []
        for p in products:
            promo = p.get('promotion') or {}
            cond = promo.get('conditions') or []
            
            debug_list.append({
                "SKU": p.get('sku'),
                "Nome": p.get('name'),
                "Preço Base": p.get('price'),
                "Promo Ativa": promo.get('isActive'),
                "Preço Promo": cond[0].get('price') if cond else "N/A",
                "Estoque": p.get('stock'),
                "Unidade": p.get('unit')
            })
        
        st.subheader("Lista de Itens (Sem Filtros)")
        st.table(debug_list)
        
        # 2. BUSCA ESPECÍFICA PELO SKU DA CENOURA
        sku_alvo = "13772"
        item_alvo = next((p for p in products if str(p.get('sku')) == sku_alvo), None)
        
        st.divider()
        if item_alvo:
            st.info(f"✅ O item '{sku_alvo}' FOI ENCONTRADO na resposta da API!")
            st.subheader("Dados Brutos do Item Alvo:")
            st.json(item_alvo)
        else:
            st.warning(f"❌ O SKU {sku_alvo} NÃO ESTÁ na lista acima.")
            st.write("Verifique se o termo de busca ou o 'storeReference' (Loja) estão corretos.")

    # 3. JSON COMPLETO PARA ANÁLISE
    with st.expander("Ver JSON Completo da Resposta"):
        st.json(raw_data)
