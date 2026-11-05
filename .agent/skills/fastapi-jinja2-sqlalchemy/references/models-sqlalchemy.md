# SQLAlchemy 2.0 com MySQL/MariaDB

Conteúdo: configuração · Base e convenção de nomes · models · relacionamentos · queries · paginação · transações · variante async

## Configuração (`app/core/config.py`)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str  # mysql+pymysql://user:senha@localhost:3306/nome?charset=utf8mb4
    secret_key: str
    debug: bool = False


settings = Settings()
```

`.env.example`:
```
DATABASE_URL=mysql+pymysql://app:troque_a_senha@localhost:3306/app_db?charset=utf8mb4
SECRET_KEY=gere-com-python -c "import secrets; print(secrets.token_urlsafe(32))"
DEBUG=false
```

Dependências: `fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart` (formulários), `sqlalchemy>=2`, `pymysql`, `cryptography` (exigido pelo PyMySQL para `caching_sha2_password` do MySQL 8), `pydantic-settings`, `itsdangerous` (sessões), `argon2-cffi`.

## Engine, sessão e `get_db` (`app/core/database.py`)

```python
from collections.abc import Generator

from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Convenção de nomes: padroniza os nomes de constraints geradas pelo SQLAlchemy (schema de teste)
# e fica impossível removê-las ou alterá-las depois.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # descarta conexões mortas (MySQL fecha conexões ociosas)
    pool_recycle=3600,    # menor que o wait_timeout do servidor
    echo=settings.debug,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`expire_on_commit=False` evita que objetos já entregues ao template sejam recarregados (e disparem queries) após o commit.

## Models

O schema é gerenciado fora da aplicação: mantenha tipos, tamanhos, nulabilidade e nomes dos models idênticos aos do banco e não use `create_all` fora dos testes. Se o schema precisar mudar, isso é uma decisão externa ao código da aplicação. Para desenhar a mudança, índices ou migrations (com zero-downtime), use a skill `mysql-dba-senior`.

Mixin para colunas repetidas:

```python
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
```

Entidades:

```python
from decimal import Decimal
from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Categoria(TimestampMixin, Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True)

    produtos: Mapped[list["Produto"]] = relationship(back_populates="categoria")


class Produto(TimestampMixin, Base):
    __tablename__ = "produtos"
    __table_args__ = (UniqueConstraint("sku", name="uq_produtos_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40))
    nome: Mapped[str] = mapped_column(String(120), index=True)
    descricao: Mapped[str | None] = mapped_column(Text)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    estoque: Mapped[int] = mapped_column(default=0)
    ativo: Mapped[bool] = mapped_column(default=True)

    categoria_id: Mapped[int] = mapped_column(
        ForeignKey("categorias.id", ondelete="RESTRICT"), index=True
    )
    categoria: Mapped["Categoria"] = relationship(back_populates="produtos")
```

Pontos de atenção no MySQL:
- `Mapped[str]` sem `String(n)` vira `VARCHAR` sem tamanho e falha no MySQL: sempre declare o tamanho.
- `Mapped[str | None]` já define `nullable=True`; `Mapped[str]` define `NOT NULL`.
- Índice em `VARCHAR` com `utf8mb4` ocupa 4 bytes por caractere; chaves únicas em colunas muito longas podem estourar o limite de índice. Mantenha colunas indexadas em até ~191 caracteres se o servidor for antigo.
- Para `Enum`, prefira `String` + validação no Python (ou `Enum` do Python com `native_enum=False`), pois alterar `ENUM` nativo no banco é trabalhoso.
- Todos os models precisam ser importados (ex.: em `app/models/__init__.py`) antes de usar `Base.metadata` (necessário para o `create_all` dos testes).

### Relacionamento muitos-para-muitos com dados extras (tabela de associação como entidade)

Pedido com itens é o caso clássico: use uma entidade `ItemPedido` com `quantidade` e `preco_unitario` (copiado do produto no momento da compra, para preservar o histórico), em vez de `secondary` simples.

```python
class Pedido(TimestampMixin, Base):
    __tablename__ = "pedidos"
    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="aberto")
    itens: Mapped[list["ItemPedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )


class ItemPedido(Base):
    __tablename__ = "itens_pedido"
    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("pedidos.id", ondelete="CASCADE"), index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("produtos.id"), index=True)
    quantidade: Mapped[int]
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    pedido: Mapped["Pedido"] = relationship(back_populates="itens")
    produto: Mapped["Produto"] = relationship()
```

## Queries (estilo 2.0)

```python
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload, joinedload

def obter(db: Session, produto_id: int) -> Produto | None:
    return db.get(Produto, produto_id)

def listar_ativos(db: Session) -> list[Produto]:
    stmt = (
        select(Produto)
        .where(Produto.ativo.is_(True))
        .options(joinedload(Produto.categoria))   # muitos-para-um
        .order_by(Produto.nome)
    )
    return list(db.scalars(stmt))

def pedidos_com_itens(db: Session, cliente_id: int) -> list[Pedido]:
    stmt = (
        select(Pedido)
        .where(Pedido.cliente_id == cliente_id)
        .options(selectinload(Pedido.itens).joinedload(ItemPedido.produto))
    )
    return list(db.scalars(stmt))
```

Regras: `joinedload` para relacionamentos muitos-para-um/um-para-um; `selectinload` para coleções (evita produto cartesiano). Com `joinedload` em coleção + `LIMIT` o SQLAlchemy precisa de subquery e fica mais lento.

Busca com filtros opcionais:

```python
def buscar(db: Session, termo: str | None, categoria_id: int | None) -> list[Produto]:
    stmt = select(Produto).where(Produto.ativo.is_(True))
    if termo:
        stmt = stmt.where(Produto.nome.ilike(f"%{termo}%"))
    if categoria_id:
        stmt = stmt.where(Produto.categoria_id == categoria_id)
    return list(db.scalars(stmt.order_by(Produto.nome)))
```
Os valores vão como parâmetros ligados; não há risco de SQL injection nesse padrão.

## Paginação

```python
from dataclasses import dataclass
from math import ceil

@dataclass
class Page[T]:
    itens: list[T]
    pagina: int
    por_pagina: int
    total: int

    @property
    def paginas(self) -> int:
        return max(1, ceil(self.total / self.por_pagina))

def paginar(db: Session, stmt, pagina: int, por_pagina: int = 20) -> Page:
    pagina = max(1, pagina)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    itens = list(db.scalars(stmt.limit(por_pagina).offset((pagina - 1) * por_pagina)))
    return Page(itens, pagina, por_pagina, total)
```
(A sintaxe `class Page[T]` exige Python 3.12+; em versões anteriores use `Generic[T]`.)

`OFFSET` serve bem para listas pequenas e painéis administrativos. Em listas grandes ou muito profundas ele lê e descarta todas as linhas anteriores: nesses casos use paginação keyset (`WHERE (criado_em, id) < (:ultimo_criado_em, :ultimo_id) ORDER BY criado_em DESC, id DESC LIMIT :n`, com índice nessas colunas). Detalhes na skill `mysql-dba-senior`.

## Transações e concorrência

Operações que alteram várias tabelas rodam numa única transação (`commit` no fim, `rollback` em qualquer erro). Para evitar que duas requisições vendam o mesmo estoque, trave a linha lida com `db.get(Produto, id, with_for_update=True)` ou `select(...).with_for_update()` (InnoDB). O exemplo completo, com caso de uso e Unit of Work, está em `clean-architecture.md`; em projetos sem essa camada, faça o mesmo dentro de uma função de service.

## Variante async

Só use se o usuário pedir ou se o projeto já for async. Mudanças:
- Driver: `mysql+aiomysql://...` ou `mysql+asyncmy://...`.
- `create_async_engine`, `async_sessionmaker`, `AsyncSession`; `get_db` vira `async def` com `async with`.
- Rotas `async def`, com `await db.scalars(...)`, `await db.commit()`.
- Lazy load não funciona em `AsyncSession`: carregue relacionamentos explicitamente com `selectinload`/`joinedload` ou use `await db.run_sync(...)`. Mantenha `expire_on_commit=False`.
