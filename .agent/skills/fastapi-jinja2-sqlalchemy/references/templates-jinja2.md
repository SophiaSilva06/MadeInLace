# Jinja2 com FastAPI

Conteúdo: setup · base.html e herança · macros · filtros e globais · formulários e erros · mensagens flash · paginação · segurança

## Setup (`app/core/templates.py`)

Centralize a instância para que filtros e globais valham em todo o projeto.

```python
from decimal import Decimal
from pathlib import Path

from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def brl(valor: Decimal | float | None) -> str:
    if valor is None:
        return "-"
    s = f"{valor:,.2f}"                       # 1,234.50
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


templates.env.filters["brl"] = brl
```

`app/main.py`:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Meu App")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
```

No template, gere URLs com `url_for` (não escreva caminhos fixos):
`<link rel="stylesheet" href="{{ url_for('static', path='css/app.css') }}">`
`<a href="{{ url_for('listar_produtos') }}">`, em que o argumento é o *nome da função* da rota (ou `name=` explícito).

## Herança: `base.html`

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Meu App{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', path='css/app.css') }}">
  {% block head %}{% endblock %}
</head>
<body>
  {% include "components/navbar.html" %}
  <main class="container">
    {% include "components/flash.html" %}
    {% block content %}{% endblock %}
  </main>
  {% block scripts %}{% endblock %}
</body>
</html>
```

Página filha:

```html
{% extends "base.html" %}
{% block title %}Produtos{% endblock %}
{% block content %}
  <h1>Produtos</h1>
  {% for p in page.itens %}
    <article>
      <h2>{{ p.nome }}</h2>
      <p>{{ p.preco | brl }} · {{ p.categoria.nome }}</p>
    </article>
  {% else %}
    <p>Nenhum produto encontrado.</p>
  {% endfor %}
  {% from "components/pagination.html" import paginacao %}
  {{ paginacao(page, url_for('listar_produtos')) }}
{% endblock %}
```

Use o `{% else %}` do `for` para o estado vazio. Evite `{% include %}` dentro de loops grandes, pois cada include tem custo; prefira macros.

## Macros (`components/`)

Macros são as "funções" do Jinja2: use para cards, campos de formulário, paginação, badges de status.

```html
{# components/forms.html #}
{% macro campo(nome, rotulo, valor="", tipo="text", erro=None, obrigatorio=False) %}
<div class="field {{ 'has-error' if erro }}">
  <label for="{{ nome }}">{{ rotulo }}</label>
  <input id="{{ nome }}" name="{{ nome }}" type="{{ tipo }}" value="{{ valor if valor is not none else '' }}"
         {{ 'required' if obrigatorio }}>
  {% if erro %}<small class="error">{{ erro }}</small>{% endif %}
</div>
{% endmacro %}
```

```html
{% from "components/forms.html" import campo %}
{{ campo("nome", "Nome", form.nome, erro=erros.get("nome"), obrigatorio=True) }}
```

Paginação:

```html
{# components/pagination.html #}
{% macro paginacao(page, base_url) %}
{% if page.paginas > 1 %}
<nav aria-label="Paginação">
  {% if page.pagina > 1 %}<a href="{{ base_url }}?pagina={{ page.pagina - 1 }}">Anterior</a>{% endif %}
  <span>Página {{ page.pagina }} de {{ page.paginas }}</span>
  {% if page.pagina < page.paginas %}<a href="{{ base_url }}?pagina={{ page.pagina + 1 }}">Próxima</a>{% endif %}
</nav>
{% endif %}
{% endmacro %}
```

Macros importadas com `{% from ... import ... %}` **não** enxergam o contexto da página por padrão. Passe tudo por argumento (ou use `import ... with context` só se realmente necessário).

## Filtros e globais úteis

```python
templates.env.globals["app_name"] = "MadeInLace"       # exemplo: nome visível em todas as páginas
templates.env.filters["data_br"] = lambda d: d.strftime("%d/%m/%Y") if d else "-"
```

Regras: filtros formatam, não consultam o banco. Se precisar de dados em toda página (ex.: contador do carrinho), injete via dependência da rota ou context processor próprio, e não faça query dentro do template.

## Formulários e erros de validação

Padrão: GET mostra o formulário, POST valida; com erro, re-renderiza com status 422 e os valores digitados; com sucesso, redireciona (PRG).

```python
@router.get("/novo", response_class=HTMLResponse)
def novo(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "produtos/form.html",
        {"form": {}, "erros": {}, "categorias": categoria_service.listar(db)})


@router.post("/novo", response_class=HTMLResponse)
def criar(
    request: Request,
    nome: str = Form(...),
    preco: str = Form(...),
    categoria_id: int = Form(...),
    db: Session = Depends(get_db),
):
    form = {"nome": nome, "preco": preco, "categoria_id": categoria_id}
    erros = produto_service.validar(form)
    if erros:
        return templates.TemplateResponse(request, "produtos/form.html",
            {"form": form, "erros": erros, "categorias": categoria_service.listar(db)},
            status_code=422)
    produto_service.criar(db, form)
    flash(request, "Produto criado com sucesso.", "success")
    return RedirectResponse(url=request.url_for("listar_produtos"), status_code=303)
```

Para validação mais robusta, modele o formulário com um schema Pydantic e capture `ValidationError`, transformando em `{campo: mensagem}`.

## Mensagens flash

Armazene na sessão (requer `SessionMiddleware`, ver `auth.md`) e consuma uma vez:

```python
def flash(request: Request, mensagem: str, categoria: str = "info") -> None:
    request.session.setdefault("_flashes", []).append({"msg": mensagem, "cat": categoria})

def get_flashed_messages(request: Request) -> list[dict]:
    return request.session.pop("_flashes", [])

templates.env.globals["get_flashed_messages"] = get_flashed_messages
```

`components/flash.html`:
```html
{% for m in get_flashed_messages(request) %}
  <div class="alert alert-{{ m.cat }}" role="alert">{{ m.msg }}</div>
{% endfor %}
```
`request` está sempre disponível no contexto quando você usa `TemplateResponse(request, ...)`.

## Segurança em templates

- Autoescape está ligado por padrão para `.html`: `{{ valor }}` já é escapado. Não use `|safe` nem `Markup` em conteúdo vindo do usuário.
- Para JSON dentro de `<script>`, use `{{ dados | tojson }}`.
- Formulários POST incluem o token CSRF: `<input type="hidden" name="csrf_token" value="{{ csrf_token(request) }}">` (ver `auth.md`).
- Links de logout e exclusão devem ser formulários POST, nunca links GET.
- Mostre/oculte botões por papel (`{% if usuario and usuario.papel == 'admin' %}`), mas **sempre** reforce a permissão na rota: esconder o botão não protege nada.
