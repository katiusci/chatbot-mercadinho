
"""
Mercadinho da Vila - Gerenciamento do banco de dados.

Responsabilidades:
- Criar e atualizar a estrutura do banco SQLite.
- Cadastrar os 31 produtos do mercadinho.
- Atualizar preços e unidades de venda.
- Evitar produtos duplicados.
- Consultar produtos e quantidades em estoque.

Os preços são referências simuladas para São Paulo.
"""

import sqlite3
from pathlib import Path


# ============================================================
# CONFIGURAÇÕES DO BANCO DE DADOS
# ============================================================

# Guarda o banco na mesma pasta deste arquivo.
DB_NAME = Path(__file__).resolve().parent / "mercadinho.db"


# ============================================================
# CATÁLOGO DE PRODUTOS
# ============================================================

# Estrutura:
# (nome, categoria, preco, quantidade, unidade)
#
# Os preços representam a unidade de venda indicada.
# As quantidades representam unidades de estoque.
# Para produtos vendidos por kg, representam kg disponíveis.

PRODUTOS_INICIAIS = [
    ("Arroz", "Alimentos", 24.90, 20, "pacote 5 kg"),
    ("Feijão", "Alimentos", 7.90, 15, "pacote 1 kg"),
    ("Café", "Bebidas", 24.90, 12, "pacote 500 g"),
    ("Leite", "Laticínios", 5.49, 30, "caixa 1 L"),
    ("Açúcar", "Alimentos", 4.49, 55, "pacote 1 kg"),
    ("Farinha", "Alimentos", 5.49, 25, "pacote 1 kg"),
    ("Macarrão", "Alimentos", 4.49, 25, "pacote 500 g"),
    ("Óleo", "Alimentos", 7.49, 10, "garrafa 900 ml"),
    ("Bolacha", "Biscoitos", 4.99, 0, "pacote 350 g"),
    ("Água", "Bebidas", 2.49, 40, "garrafa 500 ml"),
    ("Suco", "Bebidas", 6.99, 14, "caixa 1 L"),
]


NOVOS_PRODUTOS = [
    # Frutas
    ("Banana", "Frutas", 6.99, 25, "kg"),
    ("Maçã", "Frutas", 14.90, 18, "kg"),
    ("Laranja", "Frutas", 5.99, 30, "kg"),
    ("Mamão", "Frutas", 11.90, 12, "kg"),
    ("Manga", "Frutas", 9.90, 15, "kg"),
    ("Abacaxi", "Frutas", 12.90, 10, "unidade"),
    ("Uva", "Frutas", 14.90, 8, "bandeja 500 g"),

    # Verduras
    ("Alface", "Verduras", 5.99, 20, "unidade"),
    ("Couve", "Verduras", 4.99, 15, "maço"),
    ("Espinafre", "Verduras", 5.99, 10, "maço"),

    # Legumes
    ("Tomate", "Legumes", 8.99, 22, "kg"),
    ("Cenoura", "Legumes", 7.99, 18, "kg"),
    ("Batata", "Legumes", 8.99, 30, "kg"),
    ("Cebola", "Legumes", 5.99, 25, "kg"),
    ("Pepino", "Legumes", 6.99, 14, "kg"),

    # Outros produtos
    ("Ovos", "Alimentos", 12.90, 20, "dúzia"),
    ("Pão", "Padaria", 1.20, 40, "unidade"),
    ("Queijo", "Laticínios", 14.90, 12, "pacote 200 g"),
    ("Manteiga", "Laticínios", 13.90, 10, "pote 200 g"),
    ("Iogurte", "Laticínios", 3.49, 18, "unidade 170 g"),
]


# ============================================================
# CONEXÃO COM O BANCO DE DADOS
# ============================================================

def conectar():
    """
    Abre uma conexão com o banco SQLite.
    """
    return sqlite3.connect(DB_NAME)


# ============================================================
# CRIAÇÃO E ATUALIZAÇÃO DA TABELA
# ============================================================

def criar_banco():
    """
    Cria a tabela de produtos, caso não exista.

    Se o banco for de uma versão anterior, adiciona
    a coluna 'unidade' sem apagar os produtos existentes.
    """
    with conectar() as conexao:
        cursor = conexao.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                categoria TEXT NOT NULL,
                preco REAL NOT NULL,
                quantidade INTEGER NOT NULL,
                unidade TEXT NOT NULL DEFAULT 'unidade'
            )
        """)

        # Verifica as colunas existentes na tabela.
        cursor.execute("PRAGMA table_info(produtos)")
        colunas = [
            coluna[1] for coluna in cursor.fetchall()
        ]

        # Atualiza bancos criados antes da coluna unidade.
        if "unidade" not in colunas:
            cursor.execute("""
                ALTER TABLE produtos
                ADD COLUMN unidade TEXT NOT NULL
                DEFAULT 'unidade'
            """)

        conexao.commit()

    # Cadastra ou atualiza os produtos iniciais.
    inserir_produtos(PRODUTOS_INICIAIS)


# ============================================================
# CADASTRO E ATUALIZAÇÃO DE PRODUTOS
# ============================================================

def inserir_produtos(produtos):
    """
    Cadastra os produtos no banco de dados.

    Quando o produto já existe, atualiza:
    - Categoria
    - Preço
    - Unidade de venda

    A quantidade existente é preservada.
    """
    with conectar() as conexao:
        cursor = conexao.cursor()

        cursor.executemany("""
            INSERT INTO produtos
                (nome, categoria, preco, quantidade, unidade)
            VALUES (?, ?, ?, ?, ?)

            ON CONFLICT(nome) DO UPDATE SET
                categoria = excluded.categoria,
                preco = excluded.preco,
                unidade = excluded.unidade
        """, produtos)

        conexao.commit()


def adicionar_novos_produtos():
    """
    Cadastra ou atualiza frutas, verduras,
    legumes e outros produtos.
    """
    inserir_produtos(NOVOS_PRODUTOS)


# ============================================================
# CONSULTA DE PRODUTOS
# ============================================================

def listar_produtos():
    """
    Retorna os produtos cadastrados.

    Cada produto contém:
    - ID
    - Nome
    - Categoria
    - Preço
    - Quantidade
    - Unidade de venda
    """
    with conectar() as conexao:
        conexao.row_factory = sqlite3.Row
        cursor = conexao.cursor()

        cursor.execute("""
            SELECT
                id,
                nome,
                categoria,
                preco,
                quantidade,
                unidade
            FROM produtos
            ORDER BY categoria, nome
        """)

        return [
            dict(produto)
            for produto in cursor.fetchall()
        ]


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":
    # Cria a estrutura e atualiza os produtos.
    criar_banco()
    adicionar_novos_produtos()

    # Verifica a quantidade total cadastrada.
    produtos = listar_produtos()

    print("Banco de dados atualizado com sucesso!")
    print(f"Total de produtos: {len(produtos)}")
    print("Preços e unidades de venda atualizados.")
