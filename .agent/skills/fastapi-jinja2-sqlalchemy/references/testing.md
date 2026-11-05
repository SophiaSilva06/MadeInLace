# Testes (pytest + TestClient + SQLAlchemy)

Conteúdo: dependências · banco de teste · conftest · testes de rota · testes de service · autenticação nos testes · cobertura e CI

## Dependências

`pytest`, `httpx` (exigido pelo `TestClient`), `pytest-cov` (opcional).

## Qual banco usar nos testes

| Opção | Vantagem | Risco |
|---|---|---|
| **MySQL/MariaDB de teste** (banco separado, ex.: `app_test`) | idêntico à produção; pega problemas de tipo, collation e `FOR UPDATE` | precisa de um servidor rodando (Docker no CI) |
| SQLite em memória | zero configuração, muito rápido | comportamento diferente (tipos, `Decimal`, FKs desligadas por padrão, sem `FOR UPDATE`) |

Recomendação: use **MySQL de teste** quando o projeto depende de regras sensíveis (estoque, dinheiro, transações). Use SQLite apenas para testes unitários simples, e saiba que ele não prova que o código funciona no MySQL. Nunca aponte os testes para o banco de desenvolvimento ou produção: defina `TEST_DATABASE_URL` separado e recuse rodar se o nome do banco não terminar em `_test`.

## `tests/conftest.py`

```python
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import hash_senha
from app.main import app
from app.models.usuario import Usuario

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]  # mysql+pymysql://.../app_test?charset=utf8mb4
assert TEST_DATABASE_URL.split("?")[0].endswith("_test"), "Use um banco de teste!"

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def criar_schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture()
def db():
    """Sessão ligada a uma transação externa revertida ao final de cada teste."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSession(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    # base_url https: o cookie de sessão é Secure em produção e o httpx não o reenviaria por http
    with TestClient(app, base_url="https://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def usuario(db):
    u = Usuario(nome="Teste", email="teste@exemplo.com", senha_hash=hash_senha("senha123"), papel="cliente")
    db.add(u)
    db.commit()
    return u


@pytest.fixture()
def admin(db):
    u = Usuario(nome="Admin", email="admin@exemplo.com", senha_hash=hash_senha("admin123"), papel="admin")
    db.add(u)
    db.commit()
    return u


def login(client: TestClient, email: str, senha: str):
    return client.post("/login", data={"email": email, "senha": senha}, follow_redirects=False)
```

Por que a transação externa com `create_savepoint`: cada teste começa com o banco limpo e termina com rollback, mesmo que o código chame `db.commit()`. É muito mais rápido que recriar tabelas por teste. (Exceção: testes de código que usa DDL ou `FOR UPDATE` em duas conexões simultâneas precisam de um banco limpo por teste.) O `join_transaction_mode` exige SQLAlchemy ≥ 2.0.

## Fábricas de dados

Crie helpers simples em `tests/factories.py` para não repetir construção de objetos:

```python
def criar_produto(db, **kw):
    dados = dict(sku="SKU-1", nome="Vestido", preco=Decimal("99.90"), estoque=10, categoria_id=1)
    dados.update(kw)
    p = Produto(**dados)
    db.add(p)
    db.commit()
    return p
```

## Testes de rota

```python
def test_lista_produtos_renderiza_html(client, db):
    criar_produto(db, nome="Vestido Rosa")
    r = client.get("/produtos/")
    assert r.status_code == 200
    assert "Vestido Rosa" in r.text


def test_area_admin_exige_login(client):
    r = client.get("/admin/produtos", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_cliente_nao_acessa_admin(client, usuario):
    login(client, "teste@exemplo.com", "senha123")
    assert client.get("/admin/produtos").status_code == 403


def test_criar_produto_invalido_retorna_422_e_mantem_valores(client, admin):
    login(client, "admin@exemplo.com", "admin123")
    r = client.post("/produtos/novo", data={"nome": "", "preco": "abc", "categoria_id": 1})
    assert r.status_code == 422
    assert "obrigatório" in r.text.lower()
```

O `TestClient` mantém cookies entre chamadas, então o login na sessão vale para as requisições seguintes do mesmo `client`. Se o projeto usa CSRF, o helper de teste deve primeiro obter o token (GET na página do formulário e extrair o campo) ou o conftest pode sobrescrever a dependência `validar_csrf`.

## Testes de service (regras de negócio)

Sem HTTP: passam a sessão `db` e verificam o efeito no banco.

```python
def test_finalizar_pedido_baixa_estoque(db):
    p = criar_produto(db, estoque=5)
    pedido = criar_pedido(db, itens=[(p.id, 2)])
    pedido_service.finalizar_pedido(db, pedido.id)
    db.refresh(p)
    assert p.estoque == 3


def test_finalizar_pedido_sem_estoque_levanta_erro(db):
    p = criar_produto(db, estoque=1)
    pedido = criar_pedido(db, itens=[(p.id, 2)])
    with pytest.raises(ValueError):
        pedido_service.finalizar_pedido(db, pedido.id)
    db.refresh(p)
    assert p.estoque == 1  # rollback preservou o estoque
```

Priorize testes onde há dinheiro, estoque, permissão e validação; evite testar o framework (que o Jinja2 renderiza `{{ x }}`) ou getters triviais.

## Dicas

- Nomeie testes pelo comportamento (`test_cliente_nao_acessa_admin`), não pela função.
- Um assert principal por teste; fixtures para preparar cenário.
- Teste os caminhos de erro (404, 403, 422) tanto quanto o caminho feliz.
- Parametrize entradas inválidas com `@pytest.mark.parametrize`.

## Execução e CI

```bash
pytest -q
pytest --cov=app --cov-report=term-missing
```

No CI (ex.: GitHub Actions), suba um serviço `mysql:8` ou `mariadb`, exporte `TEST_DATABASE_URL`, rode `pytest`. O schema de teste vem de `create_all`; se o projeto tiver um script SQL oficial do schema, prefira carregá-lo no banco de teste para garantir paridade com o banco real.
