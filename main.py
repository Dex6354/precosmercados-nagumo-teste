import streamlit as st
import requests
import json
import pandas as pd
from urllib.parse import urlencode
import time

st.set_page_config(page_title="Nagumo Cenoura Scraper", layout="wide")
st.title("🥕 Nagumo Busca - Cenoura (e outros produtos)")
st.markdown("**API correta identificada:** `Search-UpdateGrid`")

# Sidebar controls
st.sidebar.header("Configurações")
query = st.sidebar.text_input("Termo de busca", value="cenoura")
sz = st.sidebar.number_input("Itens por página", value=20, min_value=1, max_value=100)
max_pages = st.sidebar.number_input("Máximo de páginas", value=5, min_value=1)

if st.sidebar.button("Buscar Produtos"):
    products = []
    base_url = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Search-UpdateGrid"
    
    for page in range(max_pages):
        params = {
            "q": query,
            "start": page * sz,
            "sz": sz
        }
        
        url = f"{base_url}?{urlencode(params)}"
        st.info(f"Buscando página {page+1} → {url}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml",
                "Referer": f"https://www.nagumo.com.br/busca?q={query}"
            }
            
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            
            # The response is HTML fragment with <search-card-grid> containing JSON data
            text = resp.text
            
            # Extract product JSON (it's embedded in data attributes or script)
            import re
            # Look for product data in JSON format inside the HTML
            json_matches = re.findall(r'(\[\s*\{[^}]+"productId"[^}]+\}\s*(?:,\s*\{[^}]*\})*\s*\])', text)
            
            found = False
            for match in json_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "productId" in item:
                                products.append({
                                    "ID": item.get("productId"),
                                    "Nome": item.get("productName", item.get("title")),
                                    "Preço": item.get("price", {}).get("sales", {}).get("formatted", "N/A"),
                                    "Preço Num": item.get("price", {}).get("sales", {}).get("value"),
                                    "URL": item.get("productShowFullUrl") or f"https://www.nagumo.com.br{item.get('url', '')}",
                                    "Imagem": item.get("image", {}).get("url") or item.get("image", [{}])[0].get("url"),
                                    "Disponível": item.get("ATSInCurrentStore", 0) > 0
                                })
                        found = True
                except:
                    continue
            
            if not found:
                # Fallback: try to find any JSON with products
                json_blocks = re.findall(r'\{[^{}]*(?:"productId"|"productName"|"price")[^{}]*\}', text)
                for block in json_blocks:
                    try:
                        item = json.loads(block + "}")
                        if "productId" in item or "productName" in item:
                            products.append({
                                "ID": item.get("productId"),
                                "Nome": item.get("productName") or item.get("title"),
                                "Preço": item.get("price", {}).get("sales", {}).get("formatted", "N/A"),
                                "Preço Num": item.get("price", {}).get("sales", {}).get("value"),
                                "URL": item.get("productShowFullUrl")
                            })
                    except:
                        pass
            
            st.success(f"Página {page+1}: {len(products) - (len(products)-len([p for p in products if 'page' not in locals()]))} itens")
            
            time.sleep(1)  # Be respectful
            
        except Exception as e:
            st.error(f"Erro na página {page+1}: {e}")
            break
    
    if products:
        df = pd.DataFrame(products)
        st.success(f"**Total de {len(df)} produtos encontrados**")
        
        # Display
        st.dataframe(df, use_container_width=True)
        
        # Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar CSV", csv, f"nagumo_{query}.csv", "text/csv")
        
        # Simple stats
        st.subheader("Estatísticas")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Preço médio", f"R$ {df['Preço Num'].mean():.2f}" if not df['Preço Num'].isna().all() else "N/A")
        with col2:
            st.metric("Itens em estoque", df["Disponível"].sum())
    else:
        st.warning("Nenhum produto encontrado.")
