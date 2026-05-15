import streamlit as st
import json
import re
import html
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Nagumo Scraper Debugger", layout="wide")

def extract_products_from_har(har_data):
    """
    Localiza a entrada de busca no HAR e extrai os produtos do 
    componente <search-card-grid> injetado no HTML.
    """
    logs = []
    products_found = []
    
    entries = har_data.get('log', {}).get('entries', [])
    logs.append(f"Total de entradas encontradas no HAR: {len(entries)}")
    
    # Busca a entrada específica da URL de busca
    search_entry = None
    for entry in entries:
        url = entry.get('request', {}).get('url', '')
        if "busca?q=cenoura" in url and entry.get('response', {}).get('status') == 200:
            search_entry = entry
            logs.append(f"Entrada de busca identificada: {url}")
            break
            
    if not search_entry:
        logs.append("ERRO: Nenhuma entrada de busca encontrada no arquivo.")
        return [], logs

    # Extrai o HTML da resposta
    content = search_entry.get('response', {}).get('content', {}).get('text', '')
    if not content:
        logs.append("ERRO: O conteúdo da resposta está vazio.")
        return [], logs

    # Regex para capturar o JSON dentro do atributo 'products' do componente search-card-grid
    # Padrão: products="[{...}]"
    match = re.search(r'products="([^"]+)"', content)
    
    if match:
        logs.append("Componente <search-card-grid> localizado.")
        # O conteúdo do atributo está com entidades HTML (ex: &quot;)
        json_raw = html.unescape(match.group(1))
        
        try:
            raw_products = json.loads(json_raw)
            logs.append(f"JSON decodificado com sucesso. {len(raw_products)} itens brutos.")
            
            for p in raw_products:
                products_found.append({
                    "ID": p.get("id"),
                    "Nome": p.get("productName"),
                    "Preço": p.get("price", {}).get("sales", {}).get("formatted", "N/A"),
                    "Marca": p.get("brand"),
                    "Disponível": "Sim" if p.get("available") else "Não"
                })
        except Exception as e:
            logs.append(f"ERRO ao processar JSON: {str(e)}")
    else:
        logs.append("ERRO: Atributo 'products' não encontrado no HTML.")

    return products_found, logs

# Interface Streamlit
st.title("🥕 Nagumo HAR Search Extractor")
st.markdown("Extraia itens e preços diretamente do arquivo `.har` da busca.")

uploaded_file = st.file_uploader("Arraste o arquivo buscacenoura.har aqui", type=["har"])

if uploaded_file is not None:
    try:
        har_json = json.load(uploaded_file)
        
        # Execução da extração
        items, debug_logs = extract_products_from_har(har_json)
        
        # Seção de Debugger
        with st.expander("🐞 Debugger / Logs do Sistema", expanded=False):
            for log in debug_logs:
                st.code(log)
        
        if items:
            st.success(f"Foram encontrados {len(items)} produtos.")
            
            # Exibição em tabela
            df = pd.DataFrame(items)
            st.dataframe(df, use_container_width=True)
            
            # Botão para baixar CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Baixar Dados (CSV)", csv, "produtos_nagumo.csv", "text/csv")
        else:
            st.warning("Nenhum dado pôde ser extraído. Verifique o Debugger acima.")
            
    except Exception as e:
        st.error(f"Falha ao ler o arquivo: {e}")
else:
    st.info("Aguardando upload do arquivo HAR.")
