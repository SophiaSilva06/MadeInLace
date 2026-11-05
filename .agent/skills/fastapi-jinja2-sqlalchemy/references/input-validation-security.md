# Validação de payloads e defesa contra injeção

Conteúdo: princípios · validação na borda com Pydantic · SQL injection · mass assignment · filtros, ordenação e LIKE · injeção em templates (SSTI) e XSS · injeção de comando e caminho · log injection e CRLF · SSRF e deserialização · limites e DoS · testes de segurança · checklist

## Princípios

1. **Nunca confie na entrada**: corpo, query string, cabeçalhos, cookies, caminho, arquivos, metadata gRPC e até dados vindos de outros serviços.
2. **Validação por lista de permissão (allowlist)**: defina o que é aceito (tipo, tamanho, formato, faixa) e rejeite o resto. Lista de bloqueio de "caracteres perigosos" falha sempre.
3. **Defesa em camadas**: validação reduz a superfície, mas a defesa real contra cada injeção está no ponto de uso: consulta parametrizada para SQL, escape de saída para HTML, lista de argumentos para comandos.
4. **Valide na borda, proteja no destino**: Pydantic na entrada *e* API segura na saída. Uma não substitui a outra.
5. Falhe fechado: entrada inválida retorna 422/`INVALID_ARGUMENT` sem executar nada e sem eco de detalhes internos.

## Validação na borda com Pydantic

```python
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Texto120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class BuscaProdutoIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    termo: Annotated[str, StringConstraints(strip_whitespace=True, max_length=80)] | None = None
    ordenar_por: Literal["nome", "preco", "criado_em"] = "nome"
    direcao: Literal["asc", "desc"] = "asc"
    pagina: Annotated[int, Field(ge=1, le=10_000)] = 1
    por_pagina: Annotated[int, Field(ge=1, le=100)] = 20


class CadastroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nome: Texto120
    email: EmailStr                                   # requer pacote email-validator
    senha: Annotated[str, StringConstraints(min_length=8, max_length=128)]
    # note: "papel" NÃO existe aqui; o servidor define o papel
```

- Tipos fortes (`int`, `Decimal`, `UUID`, `Literal`, `Enum`) já eliminam grande parte dos payloads maliciosos.
- Use `Query`, `Path` e `Body` com restrições (`gt`, `max_length`, `pattern`) também nos parâmetros de rota.
- Em JSON, rejeite campos desconhecidos (`extra="forbid"`) e limite o tamanho de listas (`max_length` em `list`).
- Mensagens de erro: devolva qual campo falhou e a regra, sem refletir o valor bruto em HTML.

## SQL injection

A defesa é **parametrização**, que o SQLAlchemy faz por padrão quando você usa o construtor `select()`/ORM:

```python
# SEGURO: valor viaja como parâmetro ligado
db.scalars(select(Usuario).where(Usuario.email == email))

# SEGURO: SQL textual com parâmetros nomeados
db.execute(text("SELECT id FROM usuarios WHERE email = :email"), {"email": email})

# VULNERÁVEL: nunca faça isto
db.execute(text(f"SELECT id FROM usuarios WHERE email = '{email}'"))
db.execute(text("SELECT ... WHERE nome LIKE '%" + termo + "%'"))
```

Regras:
- Proibido interpolar (`f""`, `+`, `%`, `.format`) entrada em `text()`, `execute()` ou SQL cru de qualquer tipo.
- **Identificadores** (nome de coluna/tabela, `ORDER BY`) não podem ser parâmetros: mapeie por allowlist (ver abaixo).
- O usuário do banco da aplicação deve ter só os privilégios necessários (sem `DROP`, `FILE`, `SUPER`); alterações de schema ficam com outro usuário.
- Em MySQL, evite habilitar `multi_statements` no driver.

## Mass assignment (campos que o cliente não deveria controlar)

```python
# VULNERÁVEL: cliente envia {"papel": "admin", "ativo": true}
usuario = Usuario(**request_json)

# SEGURO: schema de entrada com campos explícitos + extra="forbid"; servidor define o resto
dados = CadastroIn.model_validate(request_json)
usuario = Usuario(nome=dados.nome, email=dados.email.lower(),
                  senha_hash=hash_senha(dados.senha), papel="cliente")
```

Preço, total, papel, `cliente_id` do pedido e status **nunca** vêm do cliente: calcule ou derive no servidor (preço do banco, `cliente_id` da sessão/token).

## Filtros, ordenação e LIKE

Ordenação e filtro dinâmicos com allowlist:

```python
COLUNAS_ORDENAVEIS = {"nome": Produto.nome, "preco": Produto.preco, "criado_em": Produto.criado_em}

def buscar(db: Session, q: BuscaProdutoIn) -> list[Produto]:
    stmt = select(Produto).where(Produto.ativo.is_(True))
    if q.termo:
        stmt = stmt.where(Produto.nome.icontains(q.termo, autoescape=True))   # escapa % e _
    coluna = COLUNAS_ORDENAVEIS[q.ordenar_por]
    stmt = stmt.order_by(coluna.desc() if q.direcao == "desc" else coluna.asc())
    return list(db.scalars(stmt.limit(q.por_pagina).offset((q.pagina - 1) * q.por_pagina)))
```

`autoescape=True` evita que o usuário injete curingas (`%`, `_`) para forçar varreduras caras. Sempre limite `limit` e `offset`.

## Injeção em templates (SSTI) e XSS

- **Nunca** compile entrada do usuário como template: `Template(texto_do_usuario)` ou `env.from_string(entrada)` permite execução de código (SSTI). Se precisar de templates editáveis pelo usuário (e-mails customizados, por exemplo), use `jinja2.sandbox.SandboxedEnvironment` com contexto mínimo.
- Mantenha autoescape ligado e não use `|safe`/`Markup` com dado externo. Para HTML rico, sanitize com `nh3` (ou `bleach`) usando allowlist de tags/atributos.
- Dados em `<script>` via `|tojson`; em atributos, sempre entre aspas; URLs vindas do usuário: aceite só `http`/`https` (bloqueie `javascript:`).
- Defina cabeçalhos: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `X-Frame-Options`/`frame-ancestors`.

## Injeção de comando e path traversal

```python
# VULNERÁVEL
os.system(f"convert {nome_arquivo} saida.png")
subprocess.run(f"convert {nome_arquivo} saida.png", shell=True)

# SEGURO: lista de argumentos, sem shell; evite chamar binários externos se existir biblioteca Python
subprocess.run(["convert", str(caminho_validado), "saida.png"], check=True, timeout=10)
```

Arquivos enviados ou nomes recebidos:

```python
from pathlib import Path
import uuid

BASE = Path("/var/app/uploads").resolve()

def caminho_seguro(nome_cliente: str) -> Path:
    destino = (BASE / nome_cliente).resolve()
    if not destino.is_relative_to(BASE):          # bloqueia ../../etc/passwd
        raise ValueError("Caminho inválido")
    return destino

def nome_para_salvar(extensao_validada: str) -> str:
    return f"{uuid.uuid4().hex}{extensao_validada}"   # nunca confie no nome original
```

Upload: valide extensão **e** tipo real (assinatura do arquivo, ex.: `filetype`/Pillow abrindo a imagem), limite tamanho, salve fora do diretório público e sirva por rota controlada.

## Log injection, CRLF e cabeçalhos

- Entrada com `\n`/`\r` forjaria linhas de log: use logging estruturado (JSON) com campos separados, em vez de concatenar texto bruto, e remova quebras de linha de valores livres.
- Nunca copie entrada do usuário para cabeçalhos de resposta (`Location`, `Set-Cookie`) sem validar; em redirecionamentos (`next=`), aceite só caminhos relativos internos (começando com `/` e não com `//`) ou hosts da allowlist, para evitar *open redirect*.

## SSRF e deserialização

- Se o servidor busca uma URL fornecida pelo usuário: aceite só `https`, resolva o DNS e bloqueie IPs privados/loopback/link-local (`ipaddress.ip_address(ip).is_private`), mantenha allowlist de hosts, defina timeout e limite de tamanho, e não siga redirecionamentos às cegas.
- Nunca use `pickle`, `marshal` ou `yaml.load` em dados não confiáveis: use JSON ou `yaml.safe_load`. Evite `eval`/`exec` com qualquer dado externo.

## Limites e negação de serviço

- Limite o tamanho do corpo (no proxy reverso, ex.: `client_max_body_size`, e/ou middleware) e de uploads.
- Limite `por_pagina`, profundidade de JSON e tamanho de listas.
- Regex: evite padrões com repetição aninhada (ReDoS); prefira `StringConstraints` simples ou valide tamanho antes.
- Rate limiting nas rotas sensíveis (login, cadastro, busca, envio de e-mail).
- Timeouts em chamadas externas e no banco (`pool_timeout`, `read_timeout`).
- gRPC: configure `max_receive_message_length` e deadlines.

## Testes de segurança automatizados

Inclua testes parametrizados com payloads clássicos nas rotas que recebem texto:

```python
PAYLOADS = [
    "' OR '1'='1", "'; DROP TABLE produtos;--", "%' OR 1=1 --",
    "<script>alert(1)</script>", "{{7*7191}}", "${7*7191}", "../../etc/passwd", "a" * 10_000,
]

@pytest.mark.parametrize("payload", PAYLOADS)
def test_busca_resiste_a_payloads(client, db, payload):
    r = client.get("/api/v1/produtos", params={"termo": payload})
    assert r.status_code in (200, 422)            # nunca 500
    assert "<script>alert(1)</script>" not in r.text   # saída escapada
    assert "50337" not in r.text                        # {{7*7191}} não foi avaliado


def test_cliente_nao_define_papel(client):
    r = client.post("/api/v1/cadastro", json={"nome": "X", "email": "x@x.com",
                                              "senha": "12345678", "papel": "admin"})
    assert r.status_code == 422                    # extra="forbid"
```

Também rode no CI: `ruff` com regras `S` (bandit), `pip-audit` (dependências vulneráveis) e, quando possível, `semgrep` com regras de injeção.

## Checklist

- [ ] Todo schema de entrada com tipos fortes, limites e `extra="forbid"`
- [ ] Zero SQL montado por concatenação; `ORDER BY`/colunas por allowlist
- [ ] `LIKE` com `autoescape=True`; `limit` e `offset` sempre limitados
- [ ] Campos sensíveis (papel, preço, dono do recurso) definidos no servidor
- [ ] Autoescape do Jinja2 ligado; sem `|safe` em dado externo; sem templates montados com entrada do usuário
- [ ] `subprocess` sem `shell=True`; caminhos validados com `resolve()` + `is_relative_to`
- [ ] Redirecionamentos e URLs externas validados; proteção contra SSRF
- [ ] Sem `pickle`/`yaml.load`/`eval` sobre dados externos
- [ ] Tamanho de corpo, upload, paginação e taxa de requisições limitados
- [ ] Erros sem stack trace para o cliente; log estruturado com id de correlação
- [ ] Usuário do banco com privilégio mínimo; dependências auditadas
