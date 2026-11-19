
"""
Mercadinho da Vila - API principal do chatbot.

Responsabilidades:
- Inicializar o banco de dados SQLite.
- Disponibilizar a interface web.
- Consultar produtos, preços e estoque.
- Integrar o atendimento com a API Gemini.
- Interpretar listas de compras com inteligência artificial.
- Calcular compras utilizando o módulo Python.
- Validar mensagens e tratar possíveis erros.
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from google import genai
from pydantic import BaseModel, Field

from calculadora import calcular_compra, formatar_moeda, formatar_quantidade
from database import (
    adicionar_novos_produtos,
    criar_banco,
    listar_produtos,
)


# ============================================================
# CONFIGURAÇÕES DA APLICAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

# Carrega a chave da API armazenada no arquivo .env.
load_dotenv(BASE_DIR / ".env")

# Configura os registros de erros do servidor.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modelo Gemini utilizado no atendimento.
MODELO_GEMINI = "gemini-3.5-flash-lite"

# Inicializa a aplicação FastAPI.
app = FastAPI(
    title="Mercadinho da Vila",
    description="Chatbot inteligente para atendimento de clientes.",
    version="1.1.0",
)


# ============================================================
# INICIALIZAÇÃO DO BANCO DE DADOS
# ============================================================

# Cria a tabela e cadastra os produtos sem duplicações.
criar_banco()
adicionar_novos_produtos()


# ============================================================
# CONFIGURAÇÃO DO GEMINI
# ============================================================

api_key = os.getenv("GEMINI_API_KEY")

# A chave nunca deve ser escrita diretamente no código.
client = genai.Client(api_key=api_key) if api_key else None


# ============================================================
# MODELO DE ENTRADA DO CHAT
# ============================================================

class MensagemChat(BaseModel):
    """
    Representa a mensagem enviada pelo cliente.
    """

    mensagem: str = Field(
        ...,
        min_length=1,
        max_length=1000,
    )


# ============================================================
# CONSULTA AO GEMINI
# ============================================================

def consultar_gemini(contexto: str) -> str:
    """
    Envia uma solicitação ao Gemini.

    Retorna o texto produzido pela inteligência artificial.
    """
    resposta = client.models.generate_content(
        model=MODELO_GEMINI,
        contents=contexto,
    )

    if not resposta.text:
        raise ValueError("O Gemini retornou uma resposta vazia.")

    return resposta.text.strip()


# ============================================================
# CONTEXTO DO ATENDIMENTO
# ============================================================

def criar_contexto(mensagem: str) -> str:
    """
    Prepara as informações necessárias para o atendimento.

    Os dados são consultados diretamente no SQLite.
    """

    estoque = listar_produtos()

    return f"""
Você é o assistente virtual do Mercadinho da Vila,
um mercadinho brasileiro.

Responda em português do Brasil, de forma simpática,
clara, objetiva e profissional.

ESTOQUE ATUAL:
{json.dumps(estoque, ensure_ascii=False)}

INFORMAÇÕES DA LOJA:
Nome: Mercadinho da Vila
Endereço: Rua das Flores, 123, Centro
Horário: Segunda a sábado, das 8h às 19h.

REGRAS:
1. Utilize somente os produtos e preços cadastrados.
2. Informe a unidade de venda ao apresentar preços.
3. Se o estoque for zero, informe que está esgotado.
4. Nunca invente produtos ou quantidades.
5. Responda sobre todos os produtos solicitados.
6. Não confirme compras ou reservas.
7. Não invente informações sobre a loja.
8. Evite Markdown, asteriscos e títulos.
9. Seja breve, educado e natural.

MENSAGEM DO CLIENTE:
{mensagem}
"""


# ============================================================
# IDENTIFICAÇÃO DE LISTAS DE COMPRAS
# ============================================================

def identificar_compra(mensagem: str):
    """
    Utiliza o Gemini para identificar se a mensagem
    contém uma solicitação de cálculo de compras.

    Retorna:
        - Lista de produtos e quantidades, quando houver.
        - None, quando a mensagem não solicitar um cálculo.

    O Gemini interpreta a linguagem natural.
    Os valores são calculados posteriormente pelo Python.
    """

    # Envia apenas nomes e unidades para a interpretação.
    catalogo = [
        {
            "nome": produto["nome"],
            "unidade": produto["unidade"],
        }
        for produto in listar_produtos()
    ]

    instrucao = f"""
Analise a mensagem do cliente do Mercadinho da Vila.

Identifique se ele está solicitando o cálculo do valor
de uma compra ou orçamento com produtos e quantidades.

CATÁLOGO:
{json.dumps(catalogo, ensure_ascii=False)}

REGRAS:
- Responda exclusivamente com um objeto JSON válido.
- Não utilize Markdown.
- Não calcule preços ou totais.
- Utilize os nomes exatos do catálogo.
- Não invente produtos.
- Não invente quantidades.
- Se a quantidade não for informada, use 1 somente
  quando o cliente estiver claramente pedindo uma compra.
- Se a mensagem não solicitar cálculo, retorne:
  {{"compra": false, "itens": []}}
- Se solicitar cálculo, retorne:
  {{"compra": true, "itens": [
    {{"nome": "Arroz", "quantidade": 2, "unidade": "pacote"}}
  ]}}
- Se houver produto desconhecido, mantenha seu nome
  original para que o sistema informe o erro.
- Não confunda o peso da embalagem com a quantidade
  de embalagens solicitadas.

- Para cada produto, informe nome, quantidade e unidade.
- A unidade deve representar o que o cliente pediu,
  como kg, g, pacote, bandeja, garrafa ou unidade.
- Se o cliente não informar a unidade, utilize
  uma string vazia no campo unidade.
- Não converta unidades nem calcule preços.
  O Python será responsável por essas operações.

- Para produtos vendidos por kg, a quantidade representa kg.

MENSAGEM:
{mensagem}
"""

    resposta = client.models.generate_content(
        model=MODELO_GEMINI,
        contents=instrucao,
        config={
            "response_mime_type": "application/json",
        },
    )

    if not resposta.text:
        raise ValueError("O Gemini não retornou a interpretação.")

    # Converte o JSON retornado pela IA em dados Python.
    dados = json.loads(resposta.text)

    # Verifica se a mensagem realmente solicita um cálculo.
    if not isinstance(dados, dict):
        raise ValueError("Formato inválido da interpretação.")

    if dados.get("compra") is not True:
        return None

    itens = dados.get("itens")

    if not isinstance(itens, list) or not itens:
        raise ValueError("Lista de compras inválida.")

    # Valida a estrutura dos itens antes do cálculo.
    for item in itens:
        if not isinstance(item, dict):
            raise ValueError("Item de compra inválido.")

        if not isinstance(item.get("nome"), str):
            raise ValueError("Nome do produto inválido.")

        if "quantidade" not in item:
            raise ValueError("Quantidade não informada.")

    return itens


# ============================================================
# FORMATAÇÃO DO RESUMO DA COMPRA
# ============================================================

def montar_resumo_compra(itens, mostrar_estoque=False):
    """
    Organiza o resumo da compra para apresentar ao cliente.

    Os cálculos e as validações de estoque são realizados
    pelo módulo calculadora.py.

    Parâmetros:
        itens: produtos e quantidades solicitados.
        mostrar_estoque: indica se a quantidade disponível
        deve aparecer no resumo.

    O Gemini não realiza as operações matemáticas.
    """

    # Calcula os valores e verifica a disponibilidade.
    resultado = calcular_compra(itens)

    linhas = ["Aqui está o resumo da sua compra:", ""]

    # ========================================================
    # PRODUTOS E VALORES
    # ========================================================

    for item in resultado["itens"]:

        # Apresenta o produto, a quantidade e o subtotal.
        linhas.append(
            f"- {item['nome']} "
            f"({item['unidade']}): "
            f"{item['quantidade']} x "
            f"{formatar_moeda(item['preco_unitario'])} "
            f"= {formatar_moeda(item['subtotal'])}"
        )

        # Mostra o estoque apenas quando solicitado.
       
        # Apresenta o estoque com a unidade no plural,
        # quando necessário.
        if mostrar_estoque:
            quantidade_estoque = formatar_quantidade(
                item["estoque"]
            )

            unidade = item["unidade"]

            # Ajusta a descrição de embalagens.
            if quantidade_estoque != "1":
                plurais = {
                    "pacote 5 kg": "pacotes de 5 kg",
                    "pacote 1 kg": "pacotes de 1 kg",
                    "pacote 500 g": "pacotes de 500 g",
                    "garrafa 900 ml": "garrafas de 900 ml",
                    "garrafa 500 ml": "garrafas de 500 ml",
                    "bandeja 500 g": "bandejas de 500 g",
                    "caixa 1 L": "caixas de 1 L",
                    "unidade": "unidades",
                    "dúzia": "dúzias",
                    "maço": "maços",
                }
                unidade = plurais.get(unidade, unidade)
            else:
                if unidade.startswith(
                    ("pacote ", "garrafa ", "bandeja ", "caixa ")
                ):
                    partes = unidade.split(" ", 1)
                    unidade = f"{partes[0]} de {partes[1]}"

            linhas.append(
                f"  Estoque disponível: "
                f"{quantidade_estoque} {unidade}"
            )


        # Separa visualmente os produtos.
        linhas.append("")

    # ========================================================
    # ERROS E ESTOQUE INSUFICIENTE
    # ========================================================

    if resultado["erros"]:
        linhas.append("Atenção:")

        for erro in resultado["erros"]:
            linhas.append(f"- {erro}")

        linhas.append("")

    # ========================================================
    # TOTAL DA COMPRA
    # ========================================================

    if resultado["itens"]:

        # Quando existem erros, o total é apenas parcial.
        if resultado["erros"]:
            linhas.append(
                "Subtotal dos itens válidos: "
                + formatar_moeda(resultado["total"])
            )

        else:
            linhas.append(
                "Total da compra: "
                + formatar_moeda(resultado["total"])
            )

    elif resultado["erros"]:
        linhas.append(
            "Não foi possível calcular os itens solicitados."
        )

    return "\n".join(linhas)


# ============================================================
# ROTAS DA APLICAÇÃO
# ============================================================

@app.get("/")
def inicio():
    """
    Apresenta a interface web do chatbot.
    """
    return FileResponse(BASE_DIR / "index.html")


@app.get("/produtos")
def produtos():
    """
    Retorna os produtos cadastrados no SQLite.
    """
    return listar_produtos()


@app.post("/chat")
def conversar(dados: MensagemChat):
    """
    Recebe a mensagem do cliente.

    Fluxo:
    1. Valida a mensagem.
    2. Verifica se existe uma solicitação de compra.
    3. Se houver compra, calcula os valores em Python.
    4. Caso contrário, utiliza o Gemini no atendimento.
    """

    mensagem = dados.mensagem.strip()

    # Impede mensagens vazias.
    if not mensagem:
        raise HTTPException(
            status_code=400,
            detail="Digite uma mensagem para continuar.",
        )

    # Confirma a configuração da API Gemini.
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="A chave do Gemini não está configurada.",
        )

    try:
        # O Gemini identifica os produtos e quantidades.
        itens = identificar_compra(mensagem)

        # Quando existe uma compra, Python calcula os valores.
        
        if itens is not None:
            # Apresenta sempre o estoque disponível
            # junto com os valores da compra.
            return {
                "resposta": montar_resumo_compra(
                    itens,
                    mostrar_estoque=True
                )
            }


        # Para outras perguntas, utiliza o atendimento normal.
        contexto = criar_contexto(mensagem)

        return {
            "resposta": consultar_gemini(contexto)
        }

    except Exception:
        # Registra o erro no servidor para diagnóstico.
        logger.exception("Erro no atendimento do chatbot")

        # Não expõe detalhes internos ao cliente.
        raise HTTPException(
            status_code=503,
            detail=(
                "Não foi possível consultar o assistente agora. "
                "Tente novamente em alguns instantes."
            ),
        )
