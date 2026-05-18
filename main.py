import streamlit as st
import requests
import json

# Configuração da página
st.set_page_config(page_title="Nagumo API Scraper", layout="wide")
st.title("📦 Capturar Dados de Produto - Nagumo")

# URL fixa solicitada
url = "https://www.nagumo.com.br/on/demandware.store/Sites-Nagumo-Site/pt_BR/Product-Show?pid=270354"

# Botão para disparar a captura
if st.button("Capturar Dados do JSON"):
    # Headers cruciais para simular AJAX e evitar redirecionamento para o HTML comum
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }

    with st.spinner("Buscando dados da API..."):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    st.success("JSON capturado com sucesso!")
                    
                    # Interface em abas para organizar as informações
                    tab1, tab2, tab3 = st.tabs(["📋 Dados Tratados", "📝 Descrição (HTML)", "🔍 JSON Bruto"])
                    
                    with tab1:
                        st.subheader("Informações Principais")
                        # Tentativa de extração de campos comuns do Commerce Cloud
                        product = data.get("product", {})
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric(label="ID do Produto", value=product.get("id", "Não encontrado"))
                            st.metric(label="Nome", value=product.get("productName", "Não encontrado"))
                        with col2:
                            price = product.get("price", {})
                            sales_price = price.get("sales", {}).get("formatted", "Não encontrado")
                            st.metric(label="Preço", value=sales_price)
                    
                    with tab2:
                        st.subheader("Descrição do Item")
                        # Na Salesforce, o HTML da descrição costuma vir na chave 'rendered' ou dentro de 'product.longDescription'
                        rendered_html = data.get("rendered", "")
                        long_desc = product.get("longDescription", "")
                        
                        if rendered_html:
                            st.info("HTML Renderizado encontrado no JSON:")
                            st.components.v1.html(rendered_html, height=400, scrolling=True)
                        elif long_desc:
                            st.info("Descrição longa encontrada:")
                            st.write(long_desc)
                        else:
                            st.warning("Chave de descrição padrão não encontrada. Verifique o JSON bruto para mapear o campo correto.")
                    
                    with tab3:
                        st.subheader("Estrutura Completa do JSON")
                        st.json(data)
                        
                except json.JSONDecodeError:
                    st.error("O servidor não retornou um JSON válido. Ele pode ter redirecionado para a página HTML.")
                    st.text_area("Resposta do Servidor (Início):", response.text[:1000], height=200)
            else:
                st.error(f"Erro na requisição. Status Code: {response.status_code}")
                
        except Exception as e:
            st.error(f"Erro ao conectar com a API: {e}")
