# Clean Architecture, SOLID e tipagem estrita (Python)

Conteúdo: quando aplicar · camadas e regra de dependência · estrutura de pastas · domínio (entidades, value objects, exceções) · portas e casos de uso · adaptadores (SQLAlchemy) · composição e injeção de dependência · SOLID em Python · tipagem estrita · tratamento de erros

## Quando aplicar (e quanto)

Clean Architecture custa código extra (mapeamento entre objetos, interfaces). Aplique na medida do projeto:

| Projeto | Nível recomendado |
|---|---|
| CRUD simples, poucas regras | Router → service → ORM models (estrutura do `SKILL.md`). Sem camada de domínio separada |
| Regras de negócio relevantes (estoque, preço, pedido, permissões) | Domínio puro + casos de uso + repositórios como portas. Modelos ORM separados das entidades |
| Várias interfaces (REST + gRPC + CLI + fila) | Nível completo: os mesmos casos de uso servem a todas as interfaces |

Se o usuário pede "Clean Architecture" explicitamente, aplique o nível completo. Em caso de dúvida, comece pelo nível intermediário e explique o que seria separado se o projeto crescer.

## Camadas e regra de dependência

```
interfaces (REST, gRPC, templates)  ──►  application (casos de uso, portas)  ──►  domain (entidades, regras)
infrastructure (SQLAlchemy, e-mail, cache)  ──implementa──►  portas da application
```

Regra: **dependências apontam para dentro**. O domínio não importa FastAPI, SQLAlchemy, Pydantic nem nada de I/O. A application conhece o domínio e define *portas* (interfaces); a infraestrutura *implementa* essas portas. Nenhum import de `app.infrastructure` dentro de `domain` ou `application` (verifique com `import-linter` ou um teste simples que varre imports).

## Estrutura de pastas (nível completo)

```
app/
├── domain/
│   ├── entities/           # Pedido, Produto (regras e invariantes)
│   ├── value_objects/      # Dinheiro, Email, Quantidade
│   └── errors.py           # ErroDeDominio e derivados
├── application/
│   ├── ports/              # Protocols: repositórios, UnitOfWork, serviços externos
│   ├── use_cases/          # FinalizarPedido, CriarProduto...
│   └── dto.py              # comandos e resultados (dataclasses imutáveis)
├── infrastructure/
│   ├── db/                 # models ORM, mapeadores, repositórios SQLAlchemy, UnitOfWork
│   └── ...                 # adaptadores de e-mail, pagamento, etc.
├── interfaces/
│   ├── rest/               # routers FastAPI, schemas Pydantic, handlers de erro
│   ├── grpc/               # servicers, interceptors
│   └── web/                # rotas HTML + templates Jinja2
├── core/                   # config, container de dependências (composition root)
└── main.py
```

## Domínio

Value objects imutáveis garantem que valores inválidos nunca existam:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal


class ErroDeDominio(Exception):
    """Base para violações de regra de negócio."""


class QuantidadeInvalida(ErroDeDominio): ...
class EstoqueInsuficiente(ErroDeDominio): ...
class TransicaoInvalida(ErroDeDominio): ...


@dataclass(frozen=True, slots=True)
class Dinheiro:
    valor: Decimal

    def __post_init__(self) -> None:
        if self.valor < 0:
            raise ValueError("Dinheiro não pode ser negativo")

    def __add__(self, outro: Dinheiro) -> Dinheiro:
        return Dinheiro(self.valor + outro.valor)

    def vezes(self, qtd: int) -> Dinheiro:
        return Dinheiro(self.valor * qtd)
```

Entidade com comportamento (nada de "modelo anêmico" com regras espalhadas nos services):

```python
from enum import StrEnum


class StatusPedido(StrEnum):
    ABERTO = "aberto"
    FINALIZADO = "finalizado"
    CANCELADO = "cancelado"


@dataclass(slots=True)
class ItemPedido:
    produto_id: int
    quantidade: int
    preco_unitario: Dinheiro

    @property
    def subtotal(self) -> Dinheiro:
        return self.preco_unitario.vezes(self.quantidade)


@dataclass(slots=True)
class Pedido:
    id: int | None
    cliente_id: int
    status: StatusPedido = StatusPedido.ABERTO
    itens: list[ItemPedido] = field(default_factory=list)

    def adicionar_item(self, produto_id: int, quantidade: int, preco: Dinheiro) -> None:
        if self.status is not StatusPedido.ABERTO:
            raise TransicaoInvalida("Só é possível alterar pedidos abertos")
        if quantidade <= 0:
            raise QuantidadeInvalida("Quantidade deve ser positiva")
        self.itens.append(ItemPedido(produto_id, quantidade, preco))

    def total(self) -> Dinheiro:
        return sum((i.subtotal for i in self.itens), Dinheiro(Decimal("0")))

    def finalizar(self) -> None:
        if self.status is not StatusPedido.ABERTO or not self.itens:
            raise TransicaoInvalida("Pedido não pode ser finalizado")
        self.status = StatusPedido.FINALIZADO


@dataclass(slots=True)
class Produto:
    id: int
    nome: str
    estoque: int

    def baixar_estoque(self, quantidade: int) -> None:
        if quantidade > self.estoque:
            raise EstoqueInsuficiente(f"{self.nome}: restam {self.estoque}, pedido {quantidade}")
        self.estoque -= quantidade
```

## Portas e casos de uso (application)

Portas são `Protocol`: tipagem estrutural, sem herança forçada e fáceis de trocar por fakes nos testes.

```python
from typing import Protocol, Self
from types import TracebackType


class PedidoRepositorio(Protocol):
    def obter(self, pedido_id: int) -> Pedido | None: ...
    def salvar(self, pedido: Pedido) -> None: ...


class ProdutoRepositorio(Protocol):
    def obter_para_atualizar(self, produto_id: int) -> Produto | None: ...  # SELECT ... FOR UPDATE
    def salvar(self, produto: Produto) -> None: ...


class UnitOfWork(Protocol):
    pedidos: PedidoRepositorio
    produtos: ProdutoRepositorio

    def __enter__(self) -> Self: ...
    def __exit__(self, et: type[BaseException] | None, e: BaseException | None, tb: TracebackType | None) -> None: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

Caso de uso: uma classe com uma responsabilidade, dependências injetadas, entrada e saída tipadas e imutáveis.

```python
@dataclass(frozen=True, slots=True)
class FinalizarPedidoCmd:
    pedido_id: int


@dataclass(frozen=True, slots=True)
class PedidoFinalizado:
    pedido_id: int
    total: Decimal


class NaoEncontrado(ErroDeDominio): ...


class FinalizarPedido:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def __call__(self, cmd: FinalizarPedidoCmd) -> PedidoFinalizado:
        with self._uow as uow:
            pedido = uow.pedidos.obter(cmd.pedido_id)
            if pedido is None:
                raise NaoEncontrado(f"Pedido {cmd.pedido_id} não existe")
            for item in pedido.itens:
                produto = uow.produtos.obter_para_atualizar(item.produto_id)
                if produto is None:
                    raise NaoEncontrado(f"Produto {item.produto_id} não existe")
                produto.baixar_estoque(item.quantidade)   # levanta EstoqueInsuficiente
                uow.produtos.salvar(produto)
            pedido.finalizar()
            uow.pedidos.salvar(pedido)
            uow.commit()
            return PedidoFinalizado(pedido.id or 0, pedido.total().valor)
```

O caso de uso não sabe o que é HTTP, gRPC nem SQL. Isso permite testá-lo com repositórios em memória.

## Adaptadores de infraestrutura (SQLAlchemy)

```python
class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def __enter__(self) -> Self:
        self.session = self._factory()
        self.pedidos = SqlAlchemyPedidoRepositorio(self.session)
        self.produtos = SqlAlchemyProdutoRepositorio(self.session)
        return self

    def __exit__(self, et, e, tb) -> None:
        if et is not None:
            self.session.rollback()
        self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
```

Repositório faz o **mapeamento** entre ORM (`PedidoModel`) e entidade (`Pedido`) em funções `_para_dominio` / `_para_orm`. Esse é o custo real da separação: mantenha-o em um único lugar por agregado. Em projetos pequenos, é aceitável usar o próprio model SQLAlchemy como entidade, desde que as regras fiquem em métodos do model e o model não dependa de FastAPI.

## Composição e injeção de dependência

Monte o grafo de objetos em um único lugar (composition root) e injete via `Depends`:

```python
# app/core/container.py
from app.application.use_cases.finalizar_pedido import FinalizarPedido
from app.core.database import SessionLocal
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


def finalizar_pedido_uc() -> FinalizarPedido:
    return FinalizarPedido(SqlAlchemyUnitOfWork(SessionLocal))
```

```python
# na rota
@router.post("/{pedido_id}/finalizar")
def finalizar(pedido_id: int, uc: FinalizarPedido = Depends(finalizar_pedido_uc)) -> PedidoOut:
    resultado = uc(FinalizarPedidoCmd(pedido_id))
    return PedidoOut(id=resultado.pedido_id, total=resultado.total)
```

Nos testes, `app.dependency_overrides[finalizar_pedido_uc] = lambda: FinalizarPedido(FakeUoW())`.

## SOLID aplicado

| Princípio | Em Python/FastAPI |
|---|---|
| **S**: responsabilidade única | Rota só traduz HTTP; caso de uso só orquestra uma ação; repositório só persiste. Se a descrição de uma classe precisa de "e", divida |
| **O**: aberto/fechado | Novos comportamentos entram como novas implementações de uma porta (ex.: `GatewayPagamento` com `PixGateway`, `CartaoGateway`), sem editar `if/elif` do caso de uso |
| **L**: substituição de Liskov | Qualquer implementação de `PedidoRepositorio` (SQL, memória) deve respeitar o contrato: mesmos retornos e exceções. Testes de contrato rodam contra todas |
| **I**: segregação de interfaces | Portas pequenas e específicas (`PedidoRepositorio`, `EnviaEmail`) em vez de um `Repositorio` genérico com 20 métodos |
| **D**: inversão de dependência | Casos de uso dependem de `Protocol`s; a implementação concreta é injetada no composition root |

Evite exagero: não crie interface para algo que nunca terá segunda implementação *nem* precisa de fake em teste.

## Tipagem estrita

Configure no `pyproject.toml` e rode no CI:

```toml
[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
warn_unreachable = true

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "S", "ANN", "SIM"]   # "S" = regras de segurança (bandit)
```

Práticas:
- Anote **todas** as funções públicas (parâmetros e retorno). Nada de `Any` implícito; se for inevitável, isole-o na borda.
- `Protocol` para portas, `Literal`/`StrEnum` para conjuntos fechados de valores, `NewType` para ids que não podem ser trocados entre si (`ClienteId` vs `PedidoId`).
- Dataclasses `frozen=True, slots=True` para DTOs e value objects.
- `X | None` explícito e tratamento do `None` antes de usar; evite `# type: ignore` sem comentário do motivo.
- Pydantic nas bordas (entrada externa); tipos nativos/dataclasses dentro do domínio.
- Use `assert_never` em `match` sobre enums para garantir tratamento exaustivo.

## Tratamento de erros

Exceções de domínio descrevem *o que* deu errado em termos de negócio; a camada de interface decide *como* mostrar (HTTP 409, gRPC `FAILED_PRECONDITION`, mensagem flash). Mapeie em **um** lugar:

| Exceção de domínio | HTTP | gRPC |
|---|---|---|
| `NaoEncontrado` | 404 | `NOT_FOUND` |
| Validação de entrada (Pydantic) | 422 | `INVALID_ARGUMENT` |
| `EstoqueInsuficiente`, `TransicaoInvalida` | 409 | `FAILED_PRECONDITION` |
| Não autenticado | 401 | `UNAUTHENTICATED` |
| Sem permissão | 403 | `PERMISSION_DENIED` |
| Erro inesperado | 500 (sem detalhes internos) | `INTERNAL` |

Nunca devolva stack trace ou mensagem de exceção de banco ao cliente; registre no log com um id de correlação e devolva o id na resposta.
