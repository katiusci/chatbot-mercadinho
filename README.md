# Mercadinho da Vila

Chatbot inteligente desenvolvido em Python para simular o atendimento de um mercadinho brasileiro.

O sistema permite que clientes consultem produtos, preços, categorias e disponibilidade em estoque, além de calcular o valor de listas de compras utilizando linguagem natural.

O projeto integra a API Gemini com um banco de dados SQLite e uma interface web responsiva.

## Funcionalidades

- Atendimento virtual com inteligência artificial Gemini.
- Consulta de produtos, preços e categorias.
- Verificação da disponibilidade em estoque.
- Cálculo de compras com vários produtos.
- Conversão de unidades de medida, como quilos e embalagens de 500 g.
- Validação de quantidades e estoque insuficiente.
- Cálculos monetários com `Decimal`, evitando imprecisões.
- Interface responsiva com botões de acesso rápido.
- Catálogo com 31 produtos cadastrados no SQLite.

## Tecnologias utilizadas

- **Python:** desenvolvimento da aplicação e regras de negócio.
- **FastAPI:** criação da API.
- **SQLite:** armazenamento dos produtos, preços e estoque.
- **Google Gemini API:** interpretação das mensagens em linguagem natural.
- **HTML, CSS e JavaScript:** interface do chatbot.
- **Pydantic:** validação dos dados recebidos.

## Como funciona

O cliente envia uma mensagem pelo chatbot.

O Gemini interpreta a solicitação e identifica os produtos, as quantidades e as unidades de medida.

Quando existe uma solicitação de cálculo, o módulo `calculadora.py` consulta os dados do SQLite, verifica as quantidades disponíveis e calcula os valores utilizando Python.

O Gemini não é responsável pelas operações matemáticas. Os cálculos são realizados pela aplicação para oferecer resultados mais consistentes.

## Como executar

**1. Clone o repositório e abra a pasta do projeto.**

**2. Crie um ambiente virtual:**

```bash
python -m venv .venv
```

**3. Ative o ambiente virtual no Windows:**

```powershell
.venv\Scripts\Activate.ps1
```

**4. Instale as dependências:**

```bash
python -m pip install -r requirements.txt
```

**5. Configure a chave da API Gemini.**

Crie um arquivo `.env` na pasta principal do projeto e adicione:

```env
GEMINI_API_KEY=SUA_CHAVE_AQUI
```

É necessário utilizar uma chave válida da API Gemini.

**6. Inicialize o banco de dados:**

```bash
python database.py
```

**7. Inicie o servidor:**

```bash
python -m uvicorn main:app --reload
```

**8. Acesse a aplicação no navegador:**

http://127.0.0.1:8000

A documentação interativa da API também pode ser consultada em:

http://127.0.0.1:8000/docs

## Exemplos de utilização

O cliente pode enviar mensagens como:

- Quais frutas vocês têm disponíveis?
- Quanto custa um pacote de arroz?
- Vocês têm café em estoque?
- Quero comprar 4 pacotes de arroz. Quanto vou pagar?
- Quanto custam 2 kg de uva, 3 pacotes de macarrão, 1 pacote de farinha e 2 kg de cebola?

O chatbot utiliza os dados cadastrados para responder às consultas.

## Estrutura principal do projeto

- `main.py` — API FastAPI e integração com Gemini.
- `database.py` — criação do banco e consulta dos produtos.
- `calculadora.py` — validação de quantidades e cálculo de compras.
- `index.html` — interface web do chatbot.
- `requirements.txt` — dependências do projeto.
- `.gitignore` — exclusão de arquivos privados e temporários.

## Observações

O Mercadinho da Vila é um projeto demonstrativo, desenvolvido para fins de aprendizagem e avaliação técnica.

Os produtos, preços e quantidades representam um catálogo fictício inspirado em valores de mercado de São Paulo.

O sistema simula consultas e cálculos, mas não realiza pagamentos nem finaliza pedidos.

A chave da API Gemini não está incluída no repositório e deve ser configurada individualmente no arquivo `.env`.