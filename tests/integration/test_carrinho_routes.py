"""Testes de integração para as rotas e API do Carrinho de Compras (Regras 00 & 08)."""

import json
from datetime import date
from decimal import Decimal

import pytest
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.database import Base
from app.main import app
from app.models import Fornecedor, Linha, Produto, Usuario, Variacao
from app.routers.carrinho import (
    api_adicionar_item,
    api_atualizar_quantidade,
    api_get_carrinho,
    api_remover_item,
    get_carrinho,
)
from app.schemas.carrinho import (
    AdicionarItemPayload,
    AtualizarQuantidadePayload,
    RemoverItemPayload,
)


@pytest.fixture
def db_session() -> Session:
    """Cria uma sessão isolada com SQLite em memória para os testes de integração do carrinho."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        return session
    finally:
        session.close()


@pytest.fixture
def seed_dados(db_session: Session) -> dict[str, int]:
    """Popula usuário, produto e variação para testes de rotas."""
    user = Usuario(
        NOME="Camila",
        SOBRENOME="Mendes",
        CPF="33344455566",
        EMAIL="camila@exemplo.com",
        SENHA_HASH="hash_argon2_valido",
        NASCIMENTO=date(1998, 10, 15),
        ATIVO=True,
    )
    forn = Fornecedor(
        NOME="Corseteria Real",
        CNPJ="11222333000144",
        RAZAO_SOCIAL="Corseteria Real Ltda",
        ATIVO=True,
    )
    linha = Linha(NOME="Elegância")
    db_session.add_all([user, forn, linha])
    db_session.flush()

    prod = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha.ID,
        NOME="Corset Victorian Lace",
        DESCRICAO="Corset vintage com rendas trabalhadas.",
        TIPO="corset",
        ATIVO=True,
    )
    db_session.add(prod)
    db_session.flush()

    var = Variacao(
        FK_PRODUTO=prod.ID,
        TAMANHO="M",
        COR="Preto",
        ESTOQUE=8,
        CUSTO=Decimal("90.00"),
        PRECO=Decimal("200.00"),
        PORCENTAGEM_PROMOCAO=Decimal("10.00"),  # Preço final: 180.00
        ATIVO=True,
    )
    db_session.add(var)
    db_session.commit()

    return {
        "usuario_id": user.ID,
        "produto_id": prod.ID,
        "variacao_id": var.ID,
    }


def test_get_carrinho_html_deslogado(db_session: Session) -> None:
    """Valida se GET /carrinho para visitante deslogado retorna HTML com status 200."""
    scope = {"type": "http", "method": "GET", "path": "/carrinho", "headers": [], "app": app}
    req = Request(scope)

    resp = get_carrinho(req, db_session)
    assert isinstance(resp, HTMLResponse)
    assert resp.status_code == 200
    html = bytes(resp.body).decode("utf-8")
    assert "Sua Sacola de Compras" in html
    assert "Sua sacola está vazia" in html


def test_get_carrinho_com_aviso_vazio_exibe_mensagem(db_session: Session) -> None:
    """Valida que /carrinho?aviso=vazio exibe a mensagem 'Adicione Produtos Para Ir Ao Pagamento'."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/carrinho",
        "headers": [],
        "app": app,
    }
    req = Request(scope)
    resp = get_carrinho(req, db=db_session, aviso="vazio")
    assert resp.status_code == 200
    html = bytes(resp.body).decode("utf-8")
    assert "Adicione Produtos Para Ir Ao Pagamento" in html


def test_api_get_carrinho_deslogado_e_logado(
    db_session: Session, seed_dados: dict[str, int]
) -> None:
    """Valida GET /api/carrinho para anônimo e para usuário autenticado via cookie."""
    # 1. Deslogado
    scope_anon = {"type": "http", "method": "GET", "path": "/api/carrinho", "headers": [], "app": app}
    req_anon = Request(scope_anon)
    res_anon = api_get_carrinho(req_anon, db_session)
    data_anon = json.loads(bytes(res_anon.body).decode("utf-8"))
    assert data_anon["autenticado"] is False
    assert data_anon["quantidade_total"] == 0

    # 2. Logado (cookie user_id)
    uid = seed_dados["usuario_id"]
    cookie_header = (b"cookie", f"user_id={uid}".encode("ascii"))
    scope_auth = {
        "type": "http",
        "method": "GET",
        "path": "/api/carrinho",
        "headers": [cookie_header],
        "app": app,
    }
    req_auth = Request(scope_auth)
    res_auth = api_get_carrinho(req_auth, db_session)
    data_auth = json.loads(bytes(res_auth.body).decode("utf-8"))
    assert data_auth["autenticado"] is True
    assert data_auth["total"] == 0.0


def test_api_adicionar_item_requer_login(
    db_session: Session, seed_dados: dict[str, int]
) -> None:
    """Valida que adicionar item sem autenticação retorna 401 e login_url (Seção 9)."""
    scope = {"type": "http", "method": "POST", "path": "/api/carrinho/adicionar", "headers": [], "app": app}
    req = Request(scope)
    payload = AdicionarItemPayload(variacao_id=seed_dados["variacao_id"], quantidade=1)

    resp = api_adicionar_item(payload, req, db_session)
    assert resp.status_code == 401
    data = json.loads(bytes(resp.body).decode("utf-8"))
    assert data["success"] is False
    assert "login_url" in data


def test_fluxo_completo_api_adicionar_atualizar_remover(
    db_session: Session, seed_dados: dict[str, int]
) -> None:
    """Testa ciclo completo via endpoints REST com cookie de autenticação."""
    uid = seed_dados["usuario_id"]
    vid = seed_dados["variacao_id"]
    cookie_header = (b"cookie", f"user_id={uid}".encode("ascii"))

    # 1. Adicionar 2 itens
    scope_add = {
        "type": "http",
        "method": "POST",
        "path": "/api/carrinho/adicionar",
        "headers": [cookie_header],
        "app": app,
    }
    req_add = Request(scope_add)
    payload_add = AdicionarItemPayload(variacao_id=vid, quantidade=2)
    resp_add = api_adicionar_item(payload_add, req_add, db_session)
    assert resp_add.status_code == 200
    data_add = json.loads(bytes(resp_add.body).decode("utf-8"))
    assert data_add["success"] is True
    carrinho = data_add["carrinho"]
    assert carrinho["quantidade_total"] == 2
    assert carrinho["total"] == 360.0  # 2 * 180.00
    assert carrinho["frete_gratis"] is True
    item_id = carrinho["itens"][0]["id"]

    # 2. Atualizar quantidade para 1
    scope_up = {
        "type": "http",
        "method": "POST",
        "path": "/api/carrinho/atualizar-quantidade",
        "headers": [cookie_header],
        "app": app,
    }
    req_up = Request(scope_up)
    payload_up = AtualizarQuantidadePayload(item_id=item_id, quantidade=1)
    resp_up = api_atualizar_quantidade(payload_up, req_up, db_session)
    assert resp_up.status_code == 200
    data_up = json.loads(bytes(resp_up.body).decode("utf-8"))
    assert data_up["carrinho"]["quantidade_total"] == 1
    assert data_up["carrinho"]["total"] == 180.0

    # 3. Remover item
    scope_rm = {
        "type": "http",
        "method": "POST",
        "path": "/api/carrinho/remover",
        "headers": [cookie_header],
        "app": app,
    }
    req_rm = Request(scope_rm)
    payload_rm = RemoverItemPayload(item_id=item_id)
    resp_rm = api_remover_item(payload_rm, req_rm, db_session)
    assert resp_rm.status_code == 200
    data_rm = json.loads(bytes(resp_rm.body).decode("utf-8"))
    assert data_rm["carrinho"]["quantidade_total"] == 0
    assert data_rm["carrinho"]["total"] == 0.0


def test_api_remover_item_idempotente_segunda_requisicao(
    db_session: Session, seed_dados: dict[str, int]
) -> None:
    """Garante que requisições concorrentes ou duplicadas de remoção retornam 200 de forma idempotente."""
    uid = seed_dados["usuario_id"]
    vid = seed_dados["variacao_id"]
    cookie_header = (b"cookie", f"user_id={uid}".encode("ascii"))

    # Adiciona 1 item
    req_add = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/carrinho/adicionar",
        "headers": [cookie_header],
        "app": app,
    })
    resp_add = api_adicionar_item(
        AdicionarItemPayload(variacao_id=vid, quantidade=1), req_add, db_session
    )
    data_add = json.loads(bytes(resp_add.body).decode("utf-8"))
    item_id = data_add["carrinho"]["itens"][0]["id"]

    # Primeira requisição de remoção
    req_rm1 = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/carrinho/remover",
        "headers": [cookie_header],
        "app": app,
    })
    resp_rm1 = api_remover_item(RemoverItemPayload(item_id=item_id), req_rm1, db_session)
    assert resp_rm1.status_code == 200

    # Segunda requisição idêntica de remoção (simula duplo clique ou múltiplos listeners)
    req_rm2 = Request({
        "type": "http",
        "method": "POST",
        "path": "/api/carrinho/remover",
        "headers": [cookie_header],
        "app": app,
    })
    resp_rm2 = api_remover_item(RemoverItemPayload(item_id=item_id), req_rm2, db_session)
    assert resp_rm2.status_code == 200
    data_rm2 = json.loads(bytes(resp_rm2.body).decode("utf-8"))
    assert data_rm2["success"] is True
    assert data_rm2["carrinho"]["quantidade_total"] == 0
