import requests
import streamlit as st
from bs4 import BeautifulSoup

# Configuração da página
st.set_page_config(page_title="Captura Nagumo", layout="wide")
st.title("Capturador de Descrição Nagumo")

url_padrao = "https://www.nagumo.com.br/categoria/higiene-e-perfumaria/higiene/papel-higienico/papel-higi%C3%AAnico-folha-dupla-sulleg-4un-270354.html"
url_produto = st.text_input("URL do Produto:", value=url_padrao)

if st.button("Capturar Descrição"):
    if url_produto:
        with st.spinner("Buscando dados..."):
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            }

            try:
                response = requests.get(url_produto, headers=headers, timeout=15)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")

                    # Alvo exato identificado no HTML
                    tag_descricao = soup.find(
                        "p", class_="product-detail__longDescription"
                    )

                    if tag_descricao:
                        descricao_texto = tag_descricao.get_text(strip=True)
                        st.subheader("Resultado da Captura:")
                        st.success(descricao_texto)
                    else:
                        st.error(
                            "A classe 'product-detail__longDescription' não foi localizada no HTML."
                        )

                    # Seção de Debug
                    st.divider()
                    st.subheader("🛠️ Debug do HTML")
                    with st.expander("Visualizar bloco 'productDetails__datasheet' recebido"):
                        bloco_detalhes = soup.find(
                            "div", class_="productDetails__datasheet"
                        )
                        if bloco_detalhes:
                            st.code(str(bloco_detalhes), language="html")
                        else:
                            st.warning(
                                "O bloco completo de especificações não foi encontrado."
                            )

                else:
                    st.error(
                        f"Falha na requisição. Status Code: {response.status_code}"
                    )

            except Exception as e:
                st.error(f"Erro ao conectar com o site: {e}")
    else:
        st.warning("Por favor, insira uma URL.")
