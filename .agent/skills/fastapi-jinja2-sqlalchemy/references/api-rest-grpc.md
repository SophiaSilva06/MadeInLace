# Controladores, rotas REST e gRPC

Conteúdo: princípios dos controladores · REST (recursos, status, erros, paginação, idempotência, versionamento) · DTOs com Pydantic · handlers de erro · gRPC (proto, servidor, erros, interceptors) · uma regra de negócio, duas interfaces

## Controladores finos

Um controlador (router FastAPI ou servicer gRPC) faz exatamente quatro coisas:

1. Recebe e **valida** a entrada (Pydantic/Form/proto → DTO tipado).
2. Autentica/autoriza (via dependência ou interceptor).
3. Chama **um** caso de uso (ou service) com um comando.
4. Converte o resultado em resposta (schema de saída/mensagem proto) e traduz erros de domínio.

Se um controlador tem `if` de regra de negócio, loop de cálculo ou query SQL, a lógica está na camada errada.

## REST: convenções

**Recursos e verbos**

| Ação | Rota | Sucesso |
|---|---|---|
| Listar | `GET /api/v1/produtos?pagina=1&por_pagina=20` | 200 |
| Obter | `GET /api/v1/produtos/{id}` | 200 / 404 |
| Criar | `POST /api/v1/produtos` | 201 + `Location` |
| Substituir | `PUT /api/v1/produtos/{id}` | 200 |
| Alterar parcialmente | `PATCH /api/v1/produtos/{id}` | 200 |
| Remover | `DELETE /api/v1/produtos/{id}` | 204 |
| Ação de negócio | `POST /api/v1/pedidos/{id}/finalizar` | 200 / 409 |

- Substantivos no plural para recursos; verbos só para ações que não são CRUD (subrecurso `/finalizar`).
- `GET` nunca altera estado; `PUT`/`DELETE` são idempotentes.
- Versione no caminho (`/api/v1`) desde o início; mudanças incompatíveis viram `/v2`.

**Status codes que importam**: 400 (requisição malformada), 401 (não autenticado), 403 (sem permissão), 404, 409 (conflito de regra/estado), 422 (validação de campos), 429 (limite de taxa), 500 (erro inesperado).

**Formato de erro padronizado**: Problem Details (RFC 9457, `application/problem+json`):

```json
{
  "type": "https://api.exemplo.com/erros/estoque-insuficiente",
  "title": "Estoque insuficiente",
  "status": 409,
  "detail": "Produto 42 tem 1 unidade; solicitado 2.",
  "instance": "/api/v1/pedidos/7/finalizar",
  "correlation_id": "c0a8e2f1"
}
```

**Paginação**: devolva `itens`, `pagina`, `por_pagina`, `total`, com `por_pagina` limitado (máximo 100) para evitar abuso. Para tabelas grandes ou feeds, use paginação por cursor.

**Idempotência**: para `POST` que cria pagamento/pedido, aceite o cabeçalho `Idempotency-Key`, guarde a chave com o resultado e devolva o mesmo resultado se a requisição repetir (cliente com timeout que tenta de novo não pode cobrar duas vezes).

**Concorrência otimista** (opcional): `ETag`/`If-Match` ou coluna `versao` para evitar que duas edições simultâneas se sobrescrevam.

## DTOs com Pydantic (bordas)

Separe schema de **entrada**, de **saída** e a entidade de domínio. Nunca devolva o model ORM direto (vaza campos como `senha_hash`) nem aceite o model ORM como entrada (mass assignment).

```python
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Nome = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Sku = Annotated[str, StringConstraints(pattern=r"^[A-Z0-9-]{3,40}$")]


class ProdutoIn(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=False)   # campo desconhecido => 422

    sku: Sku
    nome: Nome
    preco: Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
    estoque: Annotated[int, Field(ge=0, le=1_000_000)] = 0
    categoria_id: Annotated[int, Field(gt=0)]


class ProdutoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    nome: str
    preco: Decimal
    estoque: int
```

`extra="forbid"` é a defesa principal contra mass assignment (cliente enviando `"papel": "admin"`). Ver `input-validation-security.md`.

## Router REST completo (exemplo)

```python
from typing import Annotated
from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/pedidos", tags=["pedidos"])


class Problema(BaseModel):          # corpo dos erros (Problem Details)
    title: str
    status: int
    detail: str | None = None


@router.post(
    "/{pedido_id}/finalizar",
    response_model=PedidoFinalizadoOut,
    responses={404: {"model": Problema}, 409: {"model": Problema}},
)
def finalizar(
    pedido_id: Annotated[int, Path(gt=0)],
    uc: FinalizarPedido = Depends(finalizar_pedido_uc),
    usuario: Usuario = Depends(exigir_login_api),   # 401 em vez de redirecionar para /login
) -> PedidoFinalizadoOut:
    resultado = uc(FinalizarPedidoCmd(pedido_id=pedido_id, solicitante_id=usuario.id))
    return PedidoFinalizadoOut(pedido_id=resultado.pedido_id, total=resultado.total)
```

Rotas `def` (síncronas) rodam em threadpool, o que combina com SQLAlchemy síncrono. Não use `async def` com I/O bloqueante: trava o event loop.

## Handlers de erro centralizados

```python
from fastapi import Request
from fastapi.responses import JSONResponse

STATUS_POR_ERRO: dict[type[ErroDeDominio], int] = {
    NaoEncontrado: 404,
    EstoqueInsuficiente: 409,
    TransicaoInvalida: 409,
}


@app.exception_handler(ErroDeDominio)
async def erro_de_dominio(request: Request, exc: ErroDeDominio) -> JSONResponse:
    status = next((s for t, s in STATUS_POR_ERRO.items() if isinstance(exc, t)), 400)
    return JSONResponse(
        {"title": type(exc).__name__, "status": status, "detail": str(exc),
         "instance": request.url.path},
        status_code=status, media_type="application/problem+json",
    )


@app.exception_handler(Exception)
async def erro_inesperado(request: Request, exc: Exception) -> JSONResponse:
    cid = registrar_erro(request, exc)            # log completo no servidor
    return JSONResponse({"title": "Erro interno", "status": 500, "correlation_id": cid}, status_code=500)
```

## gRPC

Use gRPC para comunicação serviço-a-serviço, contratos fortes e streaming. Para navegador e integrações públicas, REST continua mais simples.

**Contrato (`proto/pedidos/v1/pedidos.proto`)**

```proto
syntax = "proto3";
package pedidos.v1;

service PedidoService {
  rpc FinalizarPedido (FinalizarPedidoRequest) returns (FinalizarPedidoResponse);
}

message FinalizarPedidoRequest { int64 pedido_id = 1; }
message FinalizarPedidoResponse { int64 pedido_id = 1; string total = 2; }  // string decimal, não float
```

Regras de `.proto`: nunca reutilize nem renumere campos já publicados (use `reserved`); versione o pacote (`v1`); dinheiro como string decimal ou inteiro em centavos, nunca `float`.

**Geração de código**

```bash
pip install grpcio grpcio-tools grpcio-reflection
python -m grpc_tools.protoc -I proto --python_out=app/interfaces/grpc/gen \
  --grpc_python_out=app/interfaces/grpc/gen --pyi_out=app/interfaces/grpc/gen proto/pedidos/v1/pedidos.proto
```

**Servidor** (síncrono com pool de threads, compatível com SQLAlchemy síncrono):

```python
from concurrent import futures
import grpc

class PedidoServicer(pedidos_pb2_grpc.PedidoServiceServicer):
    def __init__(self, finalizar: FinalizarPedido) -> None:
        self._finalizar = finalizar

    def FinalizarPedido(self, request, context: grpc.ServicerContext):
        if request.pedido_id <= 0:                                   # validação na borda
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "pedido_id deve ser positivo")
        try:
            r = self._finalizar(FinalizarPedidoCmd(pedido_id=request.pedido_id))
        except NaoEncontrado as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except ErroDeDominio as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        return pedidos_pb2.FinalizarPedidoResponse(pedido_id=r.pedido_id, total=str(r.total))


def servir() -> None:
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[AuthInterceptor(), LoggingInterceptor()],
        options=[("grpc.max_receive_message_length", 4 * 1024 * 1024)],
    )
    pedidos_pb2_grpc.add_PedidoServiceServicer_to_server(PedidoServicer(finalizar_pedido_uc()), server)
    server.add_secure_port("[::]:50051", credenciais_tls())     # TLS em produção
    server.start()
    server.wait_for_termination()
```

Pontos de atenção:
- Mensagens proto garantem **tipo**, não **regra**: `int64` aceita negativo e `string` aceita qualquer coisa. Valide tamanho, formato e faixa de todos os campos (pode reaproveitar os modelos Pydantic: converta `request` em dict e valide).
- `context.abort` levanta exceção e encerra a chamada; chamadas após ele não executam.
- Defina **deadline** nos clientes (`stub.Metodo(req, timeout=3)`) e respeite o cancelamento no servidor (`context.is_active()` em operações longas).
- Autenticação por metadata (`authorization: Bearer ...`) em um interceptor; autorização por método no mesmo interceptor ou no caso de uso.
- Habilite reflexão só em ambientes de desenvolvimento.
- Se usar `grpc.aio` (async), não chame SQLAlchemy síncrono no event loop: use `await asyncio.to_thread(...)` ou migre para SQLAlchemy async.

## Uma regra de negócio, várias interfaces

O ganho da Clean Architecture aparece aqui: o mesmo `FinalizarPedido` é chamado pela rota HTML (formulário), pela rota REST e pelo servicer gRPC. Cada interface só converte entrada → `FinalizarPedidoCmd` e `PedidoFinalizado` → sua resposta, e mapeia os mesmos erros de domínio (tabela em `clean-architecture.md`). Teste a regra uma vez no caso de uso; nas interfaces teste só a tradução (status, formato, autorização).
