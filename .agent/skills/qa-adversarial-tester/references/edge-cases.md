# Catálogo de cenários adversariais

Sumário: 1 Entradas · 2 Texto · 3 Números e dinheiro · 3b Formatos brasileiros · 4 Tempo · 5 Dependências e timeouts · 6 Segurança · 7 Concorrência · 8 Arquivos · 9 Exemplo parametrizado · 10 Hypothesis

## 1. Entradas genéricas
`None`, `""`, `" "`, `[]`, `{}`, `0`, `-1`, `True` onde se espera int, `float("nan")`, `float("inf")`, tipo errado (str onde se espera int), objeto sem os campos esperados, campos extras inesperados, lista com 1 elemento, com duplicados, com 1 milhão de itens.

## 2. Texto
- Só espaços, tabs, `\n`, `\r\n`, byte nulo `\x00`.
- Unicode: emoji, acentos compostos vs decompostos (`"é"` vs `"e\u0301"`), RTL, zero-width (`\u200b`), caracteres de controle, homóglifos.
- Tamanhos: 1 caractere, exatamente o limite, limite+1, 10 MB.
- Encoding inválido: bytes que não decodificam em UTF-8.
- Aspas, barras, `%`, `&`, `<`, `>` em campos que viram SQL/HTML/URL/shell.
- Caixa: `"ABC"` vs `"abc"`, e-mails com maiúsculas, espaços nas pontas.

## 3. Números e dinheiro
- Use `Decimal`, nunca `float`, para dinheiro. Teste `0.1 + 0.2`, centavos, arredondamento (half-even vs half-up).
- Quantidade 0, negativa, fracionada, acima do estoque, acima do máximo do banco (overflow de int).
- Desconto 0%, 100%, >100%, negativo; frete grátis exatamente no limite; cupom duplicado.
- Preço 0.00 e preço negativo.

## 3b. Documentos e formatos brasileiros (quando aplicável)
CPF/CNPJ com e sem máscara, dígitos repetidos (`111.111.111-11`), tamanho errado, DV inválido; CEP com hífen e sem; telefone com DDD, +55, 9º dígito; datas `dd/mm/aaaa` vs ISO.

## 4. Tempo
Fuso horário (naive vs aware), horário de verão, 29/02, 31/12→01/01, fim de mês, meia-noite, relógio andando para trás, timestamps no futuro, expiração exatamente no instante limite (`<` vs `<=`). Congele o relógio com `time-machine`/`freezegun`.

## 5. Dependências e timeouts
Simule (mock/stub no limite do sistema, não dentro do código que você está testando):
- demora maior que o timeout; nunca responde; fecha a conexão no meio;
- 500, 502, 503, 429 com `Retry-After`, 401/403, 404;
- corpo vazio, JSON truncado, tipo de campo trocado, campo obrigatório ausente, resposta gigante;
- DNS falho, conexão recusada, certificado inválido.
Verifique: erro claro e tratado, sem travar, sem vazar stack trace ao usuário, sem estado parcial gravado (rollback).

Teste de timeout com pytest:
```python
import pytest, time

def test_cliente_aborta_dependencia_lenta(monkeypatch):
    monkeypatch.setattr("app.gateway.chamar", lambda *a, **k: time.sleep(5))
    with pytest.raises(TimeoutError):
        app.checkout.pagar(pedido, timeout=0.2)
```
Proteja a própria suíte com `--timeout=30` (pytest-timeout).

## 6. Segurança básica
- SQL injection: `' OR '1'='1`, `'; DROP TABLE x;--`. A consulta deve ser parametrizada.
- XSS: `<script>alert(1)</script>`, `"><img src=x onerror=alert(1)>` devem sair escapados.
- Path traversal: `../../etc/passwd`, `..\\`, `%2e%2e%2f`.
- SSRF: URLs para `http://169.254.169.254`, `localhost`, `file://`.
- IDOR: usuário A acessa recurso do usuário B pelo ID.
- Mass assignment: enviar `is_admin=true`, `preco=0` no corpo.
- Autorização: cada rota com perfil errado deve dar 401/403.
- Senhas/tokens nunca aparecem em logs ou respostas.

## 7. Concorrência e idempotência
Duas requisições simultâneas para o último item em estoque; dupla submissão do mesmo pagamento; retry após timeout não pode cobrar duas vezes; `ThreadPoolExecutor`/`asyncio.gather` para provocar a corrida e checar o invariante.

## 8. Arquivos e uploads
Arquivo vazio, 0 bytes, gigante, extensão dupla (`foto.jpg.exe`), MIME mentindo, nome com `../` ou Unicode, imagem corrompida, zip bomb.

## 9. Exemplo parametrizado de bordas
```python
import pytest

@pytest.mark.parametrize(
    "qtd",
    [0, -1, 10**12, 1.5, "3", None, float("nan")],
    ids=["zero", "negativa", "gigante", "fracionada", "string", "none", "nan"],
)
def test_rejeita_quantidade_invalida(qtd):
    with pytest.raises(ValueError):
        carrinho.adicionar(produto_id=1, quantidade=qtd)
```

## 10. Hypothesis (propriedades)
```python
from hypothesis import given, strategies as st

@given(st.text())
def test_normalizar_e_idempotente(s):
    assert normalizar(normalizar(s)) == normalizar(s)

@given(st.decimals(min_value=0, max_value=10**6, places=2), st.integers(0, 100))
def test_desconto_nunca_deixa_total_negativo(preco, pct):
    assert aplicar_desconto(preco, pct) >= 0
```
Quando o Hypothesis achar um contraexemplo, ele é um bug no código. Fixe o caso com `@example(...)` e corrija o código.
