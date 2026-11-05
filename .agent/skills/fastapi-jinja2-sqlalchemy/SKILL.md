---
name: fastapi-jinja2-sqlalchemy
description: Desenvolve aplicações web em Python com FastAPI, templates Jinja2 e SQLAlchemy 2.0 sobre MySQL/MariaDB, e atua como desenvolvedor backend sênior (Clean Architecture, SOLID, tipagem estrita, rotas REST/gRPC, validação de payloads contra injeção). Use quando o usuário mencionar Jinja2, SQLAlchemy, models/ORM, CRUD com banco relacional, login/sessão em FastAPI, casos de uso, controladores, regras de negócio ou segurança de API, ou pedir para criar, estruturar, revisar ou refatorar um projeto web ou API em Python com banco de dados, mesmo sem citar todas as tecnologias (loja virtual, painel administrativo, projeto integrador).
---

# FastAPI + Jinja2 + SQLAlchemy 2.0 (MySQL/MariaDB)

Guia para construir aplicações web renderizadas no servidor com padrões usados no mercado. O objetivo é código que um time consiga manter: camadas separadas, segurança básica correta e testes automatizados.

## Ambiente Antigravity

- **Local da skill:** `.agent/skills/fastapi-jinja2-sqlalchemy/` (workspace) ou `~/.gemini/antigravity/skills/fastapi-jinja2-sqlalchemy/` (global). Caminhos como `references/`, `scripts/` e `assets/` citados neste arquivo são relativos à pasta da skill; os comandos abaixo já usam o caminho a partir da **raiz do workspace**. Se instalada globalmente, troque o prefixo `.agent/skills/fastapi-jinja2-sqlalchemy/` pelo caminho global.
- **Carregamento sob demanda:** leia cada arquivo de `references/` só quando a tarefa pedir (a tabela de arquivos de apoio indica quando). Não carregue todos de uma vez.
- **Terminal:** comandos são executados pelo terminal do agente e seguem a política de revisão que o usuário configurou. Não peça nem sugira desativar a revisão; se um comando for bloqueado ou exigir aprovação, aguarde. Se o ambiente não tiver rede, o interpretador ou a ferramenta necessária, diga isso em vez de supor o resultado.
- **Windows:** se o workspace for Windows, use `py`/`python` conforme o que existir e rode scripts `.sh` via Git Bash ou WSL.
- **Planejamento:** para trabalho que cria ou reestrutura vários arquivos/camadas (novo módulo, refatoração para Clean Architecture), apresente primeiro um *Implementation Plan* (camadas, arquivos, regras de negócio e riscos) e aguarde aprovação. Correções pequenas podem ser feitas direto.
- **Verificação:** depois de alterar código, rode `pytest`, `ruff` e `mypy` no terminal (quando configurados no projeto) e reporte a saída real, nunca uma suposição.
- **Segredos:** nunca grave credenciais em arquivos versionados; use `.env` fora do git e mantenha um `.env.example` sem valores reais.
- **Outras skills:** schema, migrations e índices vão para `mysql-dba-senior`; revisão de segurança antes do merge vai para `secops-guardian`; testes adversariais vão para `qa-adversarial-tester`. Cite a skill ao delegar.

## Decisões padrão

Use estas escolhas, salvo se o usuário pedir outra coisa ou o projeto existente já usar algo diferente (nesse caso, siga o projeto):

| Tema | Padrão | Por quê |
|---|---|---|
| SQLAlchemy | 2.0 (`DeclarativeBase`, `Mapped[]`, `select()`) | API atual; o estilo 1.x (`Query`, `declarative_base`) está legado |
| Driver MySQL | `PyMySQL` (síncrono) | simples, puro Python; FastAPI executa rotas `def` em threadpool |
| Sync vs async | Sync por padrão | SSR com Jinja2 raramente precisa de async; menos armadilhas (lazy load, sessões) |
| Schema do banco | Gerenciado fora da aplicação; os models espelham o schema existente | a aplicação não cria nem altera tabelas |
| Senhas | Argon2 (`argon2-cffi`) ou bcrypt | nunca SHA/MD5 puros |
| Sessão web | Cookie assinado (`SessionMiddleware`) ou JWT em cookie `HttpOnly` | ver `references/auth.md` |
| Config | `pydantic-settings` lendo `.env` | segredos fora do código |
| Testes | `pytest` + `TestClient` + override de dependência | rápido e isolado |

Mudança de schema, migration, índice novo, query lenta (`EXPLAIN`) ou tuning de MySQL ficam fora desta skill: use a skill `mysql-dba-senior`, se estiver disponível, e depois mantenha os models idênticos ao banco.

Se o usuário pedir async, consulte a seção "Variante async" em `references/models-sqlalchemy.md`.

## Estrutura de projeto recomendada

```
app/
├── main.py                 # cria o FastAPI, monta static, inclui routers
├── core/
│   ├── config.py           # Settings (pydantic-settings)
│   ├── database.py         # engine, SessionLocal, Base, get_db
│   └── security.py         # hash de senha, tokens, dependências de auth
├── models/                 # entidades SQLAlchemy (uma por arquivo ou agrupadas por domínio)
├── schemas/                # Pydantic: validação de entrada/saída de formulários e APIs
├── repositories/           # acesso a dados (queries); opcional em projetos pequenos
├── domain/ application/ infrastructure/ interfaces/   # opcional: Clean Architecture completa (ver references/clean-architecture.md)
├── services/               # regras de negócio (transações, cálculos, validações de domínio)
├── routers/                # rotas HTTP finas: recebem, chamam service, renderizam
├── templates/
│   ├── base.html           # layout com blocos
│   ├── components/         # macros reutilizáveis (cards, forms, paginação)
│   └── <domínio>/          # list.html, detail.html, form.html
├── static/                 # css, js, imagens
tests/
├── conftest.py
├── test_<domínio>_routes.py
└── test_<domínio>_services.py
.env.example
requirements.txt
```

Por que em camadas: a rota só lida com HTTP, o service concentra regra de negócio (e é testável sem HTTP), e o repository isola o SQL. Em projetos pequenos, pule `repositories/` e faça as queries direto no service; não crie camadas vazias só por formalidade.

## Fluxo de trabalho

1. **Entender o domínio.** Liste entidades, relacionamentos e regras de negócio antes de codar. Se o usuário já tem documentação, parta dela.
2. **Configuração e banco** (`core/config.py`, `core/database.py`): ver `references/models-sqlalchemy.md`.
3. **Models** com tipos, constraints e índices explícitos, idênticos aos do schema existente no banco.
4. **Schemas + services + routers**, uma funcionalidade vertical por vez (ex.: produtos completo, depois clientes).
5. **Templates Jinja2**: `base.html` primeiro, depois macros, depois páginas: ver `references/templates-jinja2.md`.
6. **Autenticação e autorização**: ver `references/auth.md`.
7. **Testes**: ver `references/testing.md`. Escreva ao menos um teste por rota crítica e por regra de negócio.

Ao entregar código, indique os comandos para rodar (`uvicorn`, `pytest`) e o que precisa existir no `.env`.

## Regras que valem em todo o projeto

**Banco de dados**
- Use `select()` com `db.scalars(...)`/`db.execute(...)`; evite `db.query()`.
- Evite N+1: use `selectinload` (coleções) ou `joinedload` (muitos-para-um) quando o template acessar relacionamentos. Lazy load dentro de loop no template é a causa mais comum de lentidão.
- Uma sessão por requisição via dependência `get_db`; `commit` no service ou na rota que conclui a operação, `rollback` em erro.
- Valores monetários em `Numeric(10, 2)` (`Decimal`), nunca `Float`.
- No MySQL, `String` exige tamanho (`String(120)`), e o charset deve ser `utf8mb4`.
- Nunca monte SQL concatenando strings; use parâmetros ou o construtor do SQLAlchemy.
- Prefira exclusão lógica (`ativo`/`deleted_at`) para entidades com histórico (pedidos, clientes), e `ondelete` explícito nas FKs.

**Rotas e templates**
- Rotas que devolvem HTML usam `response_class=HTMLResponse` e `templates.TemplateResponse(request, "arquivo.html", contexto)` (a assinatura atual recebe `request` como primeiro argumento).
- Formulários seguem Post/Redirect/Get: após POST bem-sucedido, `RedirectResponse(url, status_code=303)`.
- Jinja2 escapa HTML por padrão (autoescape): não use `|safe` em dado vindo do usuário.
- Toda página estende `base.html`; trechos repetidos viram macros em `templates/components/`.
- Lógica de negócio não pertence ao template. Template formata e exibe.

**Segurança**
- Proteja formulários que alteram estado com token CSRF quando a autenticação for por cookie (ver `references/auth.md`).
- Valide entrada com Pydantic/`Form(...)`; nunca confie em campos ocultos (preço, papel do usuário) vindos do cliente.
- Segredos só em variáveis de ambiente; entregue um `.env.example` e garanta que `.env` esteja no `.gitignore`.
- Cookies de sessão: `HttpOnly`, `SameSite=Lax`, `Secure` em produção.

**Qualidade**
- Type hints em tudo; nomes de domínio consistentes (se o projeto está em português, mantenha nomes de entidades e campos em português de forma consistente, e nomes técnicos como `Session`, `router` em inglês).
- Funções pequenas, rotas finas, sem lógica duplicada entre rotas.
- Formatação com `ruff`/`black`; dependências fixadas em `requirements.txt`.

## Backend sênior: arquitetura, APIs e validação

Ao atuar como desenvolvedor backend sênior, aplique estes princípios além das regras acima:

- **Regra de dependência**: domínio não importa FastAPI, SQLAlchemy nem Pydantic; a aplicação define portas (`Protocol`) e a infraestrutura as implementa. Detalhes, exemplos e o nível certo de formalidade por tamanho de projeto em `references/clean-architecture.md`.
- **Controladores finos**: validam entrada, autorizam, chamam **um** caso de uso e traduzem a resposta e os erros. Regra de negócio fica no domínio/caso de uso, nunca na rota. REST, gRPC, códigos de status e formato de erro em `references/api-rest-grpc.md`.
- **Tipagem estrita**: anote todas as funções públicas, use `mypy --strict`, `Protocol`, `Literal`/`StrEnum`, `NewType` e dataclasses imutáveis para DTOs.
- **Toda entrada é hostil**: schemas Pydantic com tipos fortes, limites e `extra="forbid"`; SQL sempre parametrizado; identificadores dinâmicos por allowlist; nunca montar templates, comandos ou caminhos com dado do usuário. Passo a passo e checklist em `references/input-validation-security.md`.
- **Erros de domínio** são mapeados em um único lugar para HTTP e gRPC; o cliente nunca vê stack trace.

Quando o projeto for pequeno, não imponha a arquitetura completa: explique o que seria separado se ele crescer e entregue o nível que o escopo justifica.

## Exemplo mínimo de rota (referência de estilo)

```python
# app/routers/produtos.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.services import produto_service

router = APIRouter(prefix="/produtos", tags=["produtos"])


@router.get("/", response_class=HTMLResponse)
def listar(request: Request, pagina: int = 1, db: Session = Depends(get_db)):
    page = produto_service.listar_paginado(db, pagina=pagina, por_pagina=20)
    return templates.TemplateResponse(request, "produtos/list.html", {"page": page})
```

## Referências (leia conforme a tarefa)

- `references/models-sqlalchemy.md`: configuração do engine para MySQL, `Base`, models, relacionamentos, queries, paginação, variante async.
- `references/templates-jinja2.md`: setup, herança, macros, filtros customizados, formulários, mensagens flash, paginação.
- `references/auth.md`: hash de senha, login por sessão, dependências de autorização por papel, CSRF.
- `references/testing.md`: fixtures, banco de teste, override de `get_db`, testes de rota e de service.
- `references/clean-architecture.md`: camadas, domínio, casos de uso, portas e adaptadores, injeção de dependência, SOLID, tipagem estrita, mapeamento de erros.
- `references/api-rest-grpc.md`: convenções REST, DTOs, handlers de erro, idempotência, contrato `.proto`, servidor gRPC, interceptors.
- `references/input-validation-security.md`: validação de payloads e defesa contra injeção (SQL, SSTI, XSS, comando, path traversal, SSRF), testes de segurança e checklist.

Leia apenas o arquivo relevante para a etapa atual, em vez de todos de uma vez.
