
"""
Mercadinho da Vila - Cálculo de compras.

Responsabilidades:
- Consultar preços e estoque no SQLite.
- Validar produtos e quantidades.
- Converter unidades de medida quando necessário.
- Calcular subtotais e total com precisão.
- Informar erros de produtos ou estoque.

Os valores monetários utilizam Decimal.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import unicodedata

from database import listar_produtos


# ============================================================
# CONFIGURAÇÕES
# ============================================================

CASAS_DECIMAIS = Decimal("0.01")

# Unidades que podem ser vendidas em quantidades fracionadas.
UNIDADES_FRACIONAVEIS = {"kg"}

# Conversões aceitas para produtos vendidos por peso.
PESOS_EM_KG = {
    "kg": Decimal("1"),
    "g": Decimal("0.001"),
}


# ============================================================
# FORMATAÇÃO
# ============================================================

def formatar_moeda(valor):
    """
    Converte um valor monetário para o padrão brasileiro.
    Exemplo: 54.42 -> R$ 54,42.
    """
    valor = Decimal(str(valor))
    return f"R$ {valor:.2f}".replace(".", ",")



def formatar_quantidade(valor):
    """
    Formata quantidades sem eliminar zeros importantes.

    Exemplos:
        10 -> 10
        20 -> 20
        2.500 -> 2,5
    """
    numero = Decimal(str(valor))
    texto = format(numero, "f")

    # Remove zeros finais apenas após a vírgula decimal.
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")

    return texto.replace(".", ",")



def normalizar_texto(texto):
    """
    Remove acentos e diferenças entre maiúsculas
    e minúsculas para facilitar a busca de produtos.
    """
    texto = unicodedata.normalize("NFKD", texto.casefold())

    return "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    ).strip()


# ============================================================
# CONSULTA AO BANCO DE DADOS
# ============================================================

def obter_produtos():
    """
    Consulta o catálogo e organiza os produtos pelo nome.
    """
    return {
        normalizar_texto(produto["nome"]): produto
        for produto in listar_produtos()
    }


# ============================================================
# CONVERSÃO DE UNIDADES
# ============================================================

def converter_quantidade(quantidade, unidade_pedida, unidade_venda):
    """
    Converte a quantidade solicitada para a unidade
    utilizada no estoque.

    Exemplos:
    - Produto vendido por kg: 500 g -> 0,5 kg.
    - Bandeja 500 g: 2 kg -> 4 bandejas.

    Se a unidade não for informada, considera que a
    quantidade já está na unidade de venda do produto.

    Não permite comprar frações de embalagens fechadas.
    """

    unidade_pedida = normalizar_texto(unidade_pedida or "")
    unidade_venda = normalizar_texto(unidade_venda)

    # Trata nomes equivalentes de unidades.
    equivalencias = {
        "quilo": "kg",
        "quilos": "kg",
        "kilo": "kg",
        "kilos": "kg",
        "grama": "g",
        "gramas": "g",
        "unidades": "unidade",
        "pacotes": "pacote",
        "bandejas": "bandeja",
        "garrafas": "garrafa",
        "macos": "maco",
        "duzias": "duzia",
    }

    unidade_pedida = equivalencias.get(
        unidade_pedida, unidade_pedida
    )

    # Sem unidade explícita: usa a unidade cadastrada.
    if not unidade_pedida:
        quantidade_convertida = quantidade

    # Produtos vendidos diretamente por quilo.
    elif unidade_venda == "kg":
        if unidade_pedida not in PESOS_EM_KG:
            raise ValueError("Unidade incompatível com o produto.")

        quantidade_convertida = (
            quantidade * PESOS_EM_KG[unidade_pedida]
        )

    # Produtos vendidos em embalagens de 500 g.
    elif unidade_venda == "bandeja 500 g":
        if unidade_pedida in PESOS_EM_KG:
            peso_solicitado = (
                quantidade * PESOS_EM_KG[unidade_pedida]
            )
            quantidade_convertida = (
                peso_solicitado / Decimal("0.5")
            )
        elif unidade_pedida in {"bandeja", "unidade"}:
            quantidade_convertida = quantidade
        else:
            raise ValueError("Unidade incompatível com o produto.")

    # Demais produtos vendidos em embalagens ou unidades.
    else:
        tipo_embalagem = unidade_venda.split()[0]

        if unidade_pedida in {
            tipo_embalagem, "unidade"
        }:
            quantidade_convertida = quantidade
        else:
            raise ValueError("Unidade incompatível com o produto.")

    # Apenas produtos vendidos diretamente por kg
    # podem ter quantidades fracionadas.
    if unidade_venda not in UNIDADES_FRACIONAVEIS:
        if quantidade_convertida != quantidade_convertida.to_integral_value():
            raise ValueError(
                "Este produto é vendido em embalagens inteiras."
            )

    return quantidade_convertida


# ============================================================
# CÁLCULO DA COMPRA
# ============================================================

def calcular_compra(itens):
    """
    Calcula os valores de todos os itens solicitados.

    Entrada:
        [
            {
                "nome": "Uva",
                "quantidade": 2,
                "unidade": "kg"
            }
        ]

    Retorno:
        Dicionário com itens, total e possíveis erros.
    """

    produtos = obter_produtos()

    # Listas utilizadas para organizar o resultado.
    resultado = []
    erros = []

    # Total acumulado da compra.
    total = Decimal("0.00")

    # ========================================================
    # PROCESSAMENTO DOS PRODUTOS
    # ========================================================

    for item in itens:

        # Identifica o produto e a quantidade solicitada.
        nome = str(item.get("nome", "")).strip()
        unidade_pedida = str(item.get("unidade", "")).strip()

        produto = produtos.get(normalizar_texto(nome))

        # Verifica se o produto existe no catálogo.
        if produto is None:
            erros.append(f"Produto não encontrado: {nome}.")
            continue

        # ====================================================
        # VALIDAÇÃO DA QUANTIDADE
        # ====================================================

        try:
            quantidade = Decimal(str(item.get("quantidade", 0)))

            if not quantidade.is_finite() or quantidade <= 0:
                raise ValueError("Quantidade inválida.")

            # Converte a quantidade para a unidade do estoque.
            quantidade = converter_quantidade(
                quantidade,
                unidade_pedida,
                produto["unidade"]
            )

        except (InvalidOperation, ValueError, TypeError) as erro:
            erros.append(
                f"Quantidade ou unidade inválida para "
                f"{nome}: {erro}"
            )
            continue

        # ====================================================
        # VALIDAÇÃO DO ESTOQUE
        # ====================================================

        estoque = Decimal(str(produto["quantidade"]))

       
        # Verifica se o produto está esgotado.
        if estoque == 0:
            erros.append(
                f"Infelizmente, {produto['nome']} "
                f"({produto['unidade']}) está esgotado "
                "no momento. Não temos unidades disponíveis."
            )
            continue

        if quantidade > estoque:
            # Informa a quantidade disponível de forma clara.
            # Não inclui o produto no cálculo da compra.
            unidade = produto["unidade"]

            plurais = {
                "pacote 5 kg": ("pacote de 5 kg", "pacotes de 5 kg"),
                "pacote 1 kg": ("pacote de 1 kg", "pacotes de 1 kg"),
                "pacote 500 g": ("pacote de 500 g", "pacotes de 500 g"),
                "garrafa 900 ml": ("garrafa de 900 ml", "garrafas de 900 ml"),
                "garrafa 500 ml": ("garrafa de 500 ml", "garrafas de 500 ml"),
                "bandeja 500 g": ("bandeja de 500 g", "bandejas de 500 g"),
                "caixa 1 L": ("caixa de 1 L", "caixas de 1 L"),
                "unidade": ("unidade", "unidades"),
                "dúzia": ("dúzia", "dúzias"),
                "maço": ("maço", "maços"),
            }

            singular, plural = plurais.get(unidade, (unidade, unidade))
            unidade_formatada = singular if estoque == 1 else plural

            erros.append(
                f"Estoque insuficiente para {nome}. "
                f"Você solicitou {formatar_quantidade(quantidade)} "
                f"{plural}, mas temos apenas "
                f"{formatar_quantidade(estoque)} "
                f"{unidade_formatada} disponíveis."
            )
            continue


        # ====================================================
        # CÁLCULO DO SUBTOTAL
        # ====================================================

        preco = Decimal(str(produto["preco"]))

        subtotal = (preco * quantidade).quantize(
            CASAS_DECIMAIS,
            rounding=ROUND_HALF_UP
        )

        # Acrescenta o subtotal ao valor total.
        total += subtotal

        # ====================================================
        # REGISTRO DO ITEM CALCULADO
        # ====================================================

        # IMPORTANTE:
        # Este bloco deve permanecer dentro do for.
        # Assim, todos os produtos serão apresentados.
        resultado.append({
            "nome": produto["nome"],
            "quantidade": formatar_quantidade(quantidade),
            "unidade": produto["unidade"],
            "preco_unitario": f"{preco:.2f}",
            "subtotal": f"{subtotal:.2f}",
            "estoque": formatar_quantidade(estoque),
        })

    # ========================================================
    # RESULTADO FINAL
    # ========================================================

    return {
        "itens": resultado,
        "total": f"{total:.2f}",
        "erros": erros,
    }


# ============================================================
# TESTE LOCAL
# ============================================================

if __name__ == "__main__":

    from database import criar_banco, adicionar_novos_produtos

    # Inicializa o banco e atualiza os produtos.
    criar_banco()
    adicionar_novos_produtos()

    # Testa a compra com diferentes unidades de venda.
    compra_teste = [
        {"nome": "Uva", "quantidade": 2, "unidade": "kg"},
        {"nome": "Macarrão", "quantidade": 3, "unidade": "pacote"},
        {"nome": "Farinha", "quantidade": 1, "unidade": "pacote"},
        {"nome": "Cebola", "quantidade": 2, "unidade": "kg"},
    ]

    resultado = calcular_compra(compra_teste)

    print("\nMERCADINHO DA VILA")
    print("Resumo da compra")
    print("-" * 40)

    for item in resultado["itens"]:
        print(
            f"{item['nome']}: "
            f"{formatar_quantidade(item['quantidade'])} "
            f"{item['unidade']} = "
            f"{formatar_moeda(item['subtotal'])}"
        )

    for erro in resultado["erros"]:
        print(f"Aviso: {erro}")

    print("-" * 40)
    print("TOTAL:", formatar_moeda(resultado["total"]))
