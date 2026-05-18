import json
import re
import requests
import streamlit as st
from bs4 import BeautifulSoup


def extrair_descricao_produto(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "pt-BR,pt;q=0.9",
    }

    try:
        # Faz a requisição para a página do produto
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return (
                f"Erro ao acessar o site. Código de status: {response.status_code}"
            )

        soup = BeautifulSoup(response.text, "html.parser")

        # Localiza o script que contém o JSON-LD com os metadados do produto
        script_tag = soup.find("script", type="application/ld+json")

        if script_tag:
            try:
                # Carrega o conteúdo de texto como um dicionário Python
                dados_produto = json.loads(script_tag.string.strip())

                # Extrai o campo description
                descricao = dados_produto.get("description", "")

                # Caso esteja no formato de dicionário vazio ou não preenchido adequadamente,
                # tenta buscar em meta tags ou alternativas comuns no HTML
                if not descricao or isinstance(descricao, dict):
                    meta_desc = soup.find("meta", attrs={"name": "description"})
                    if meta_desc and meta_desc.get("content"):
                        descricao = meta_desc["content"]
                    else:
                        descricao = "Descrição não preenchida no campo padrão do site."

                return descricao

            except json.JSONDecodeError:
                return "Falha ao decodificar os dados estruturados do produto."
        else:
            # Fallback caso não encontre a tag de script estruturada
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                return meta_desc["content"]
            return "Não foi possível encontrar a descrição estruturada do item."

    except Exception as e:
        return f"Ocorreu um erro durante a captura: {str(e)}"


# Configuração da página Streamlit
st.set_page_config(page_title="Captura de Descrição Nagumo", page_icon="🛒")

st.title("Captura de Descrição de Item")
st.write(
    "Esta aplicação captura a descrição de produtos diretamente do site Nagumo."
)

# URL padrão solicitada
url_padrao = "https://www.nagumo.com.br/categoria/higiene-e-perfumaria/higiene/papel-higienico/papel-higi%C3%AAnico-folha-dupla-sulleg-4un-270354.html"

# Input de texto para a URL do produto
url_produto = st.text_input("URL do Produto:", value=url_padrao)

if st.button("Capturar Descrição"):
    if url_produto:
        with st.spinner("Buscando dados do produto..."):
            descricao_capturada = extrair_descricao_produto(url_produto)

            st.subheader("Resultado da Captura:")
            st.info(descricao_capturada)
    else:
        st.warning("Por favor, insira uma URL válida.")
