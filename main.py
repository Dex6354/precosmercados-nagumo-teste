import streamlit as st
import requests
from bs4 import BeautifulSoup
import json

def extrair_descricao_produto(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return f"Erro ao acessar o site. Status: {response.status_code}", None
            
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. Tenta capturar pelo container de descrição longa do produto (comum no layout do e-commerce)
        container_desc = soup.find("div", class_="product-detail__description") or soup.find("div", class_="description-and-detail")
        if container_desc:
            texto_desc = container_desc.get_text(separator="\n", strip=True)
            if texto_desc:
                return texto_desc, response.text
                
        # 2. Segunda tentativa: Localizar o bloco de scripts estruturados ou dados do Vue (JSON embutido no HTML)
        # O site usa uma div id="vueApp" ou estruturas similares que carregam metadados
        vue_app_div = soup.find("div", id="vueApp")
        if vue_app_div and vue_app_div.has_attr("data-pdict-forms"):
            # Exemplo de extração de atributos data que guardam JSONs internos
            pass
            
        # 3. Terceira tentativa: Buscar por tags de parágrafo específicas da área de detalhes
        especificacoes = soup.find_all("div", class_="value")
        if especificacoes:
            texto_especs = "\n".join([esp.get_text(strip=True) for esp in especificacoes])
            if len(texto_especs) > 10:
                return texto_especs, response.text

        # Fallback: Se não achar nada estruturado, procura qualquer texto longo no escopo principal do produto
        main_content = soup.find("div", id="maincontent")
        if main_content:
            # Captura textos puramente informativos excluindo menus/headers
            paragrafos = [p.get_text(strip=True) for p in main_content.find_all("p") if len(p.get_text(strip=True)) > 30]
            if paragrafos:
                return "\n".join(paragrafos), response.text

        return "Não foi possível isolar a descrição específica nas tags mapeadas.", response.text
        
    except Exception as e:
        return f"Ocorreu um erro: {str(e)}", None

# Configuração Streamlit
st.set_page_config(page_title="Scraper Nagumo", layout="wide")
st.title("Captura de Descrição de Produtos")

url_padrao = "https://www.nagumo.com.br/categoria/higiene-e-perfumaria/higiene/papel-higienico/papel-higi%C3%AAnico-folha-dupla-sulleg-4un-270354.html"
url_produto = st.text_input("URL do Produto:", value=url_padrao)

if st.button("Capturar Dados"):
    if url_produto:
        with st.spinner("Analisando página..."):
            descricao, html_bruto = extrair_descricao_produto(url_produto)
            
            # Exibição do Resultado Central
            st.subheader("Resultado Filtrado:")
            if "Erro" in descricao or "Não foi possível" in descricao:
                st.error(descricao)
            else:
                st.success(descricao)
            
            # SEÇÃO DE DEBUG
            st.divider()
            st.subheader("🛠️ Área de Debug (Desenvolvedor)")
            
            with st.expander("Verificar metadados básicos encontrados no HTML"):
                if html_bruto:
                    soup_debug = BeautifulSoup(html_bruto, "html.parser")
                    title_tag = soup_debug.find("title")
                    meta_desc = soup_debug.find("meta", attrs={"name": "description"})
                    
                    st.write(f"**Tag `<title>`:** {title_tag.text if title_tag else 'Não encontrada'}")
                    st.write(f"**Meta Description:** {meta_desc['content'] if meta_desc else 'Não encontrada'}")
            
            with st.expander("Visualizar Todo o HTML Bruto recebido pelo script"):
                if html_bruto:
                    st.code(html_bruto, language="html")
                else:
                    st.write("Nenhum HTML foi retornado.")
    else:
        st.warning("Por favor, preencha a URL.")
