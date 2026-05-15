import streamlit as st
import requests
import re
import html
import json
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Nagumo Search", page_icon="🥕")

def buscar_produtos_nagumo(termo_busca):
    """
    Faz o scraping em tempo real da página de busca do Nagumo extraindo o JSON do componente.
    """
    # Formata o termo para a URL
    termo_url = requests.utils.quote(termo_busca)
    url = f"https://www.nagumo.com.br/busca?q={termo_url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9"
    }
    
    logs = []
    products_list = []
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        logs.append(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            # Regex específica para capturar o conteúdo do atributo products
            match = re.search(r'products="([^"]+)"', content)
            
            if match:
                # Decodifica entidades HTML e carrega o JSON
                json_raw = html.unescape(match.group(1))
                data = json.loads(json_raw)
                
                for p in data:
                    # No JSON injetado, os campos costumam ser 'name' e 'price' direto
                    # ou estruturas internas dependendo da versão do card.
                    nome = p.get("name") or p.get("productName") or "Sem nome"
                    
                    # Trata o preço que pode vir como float ou dicionário
                    preco_raw = p.get("price")
                    if isinstance(preco_raw, dict):
                        preco = preco_raw.get("sales", {}).get("formatted", "N/A")
                    else:
                        preco = f"R$ {preco_raw:.2f}" if preco_raw else "N/A"

                    products_list.append({
                        "Nome": nome,
                        "Preço": preco,
                        "Marca": p.get("brand", "N/A"),
                        "ID": p.get("id") or p.get("sku")
                    })
                logs.append(f"Sucesso: {len(products_list)} itens encontrados.")
            else:
                logs.append("Aviso: Atributo 'products' não encontrado no HTML.")
        else:
            logs.append(f"Erro na requisição: {response.status_code}")
            
    except Exception as e:
        logs.append(f"Erro de conexão/processamento: {str(e)}")
        
    return products_list, logs

# --- Interface Streamlit ---
st.title("🥕 Nagumo Real-Time Search")

# Campo de busca
query = st.text_input("O que você deseja buscar no Nagumo?", placeholder="Ex: cenoura, leite, arroz...")

if query:
    with st.spinner(f"Buscando '{query}' no Nagumo..."):
        resultados, debug_info = buscar_produtos_nagumo(query)
    
    # Debugger lateral
    with st.sidebar:
        st.header("🐞 Debugger")
        for log in debug_info:
            st.write(f"- {log}")

    if resultados:
        st.success(f"Resultados para: {query}")
        
        # Exibe em tabela
        df = pd.DataFrame(resultados)
        st.dataframe(df, use_container_width=True)
        
        # Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("Baixar Resultados (CSV)", csv, f"busca_{query}.csv", "text/csv")
    else:
        st.error("Nenhum item encontrado. Verifique o Debugger na lateral para detalhes.")
else:
    st.info("Digite um termo acima para iniciar a busca.")
