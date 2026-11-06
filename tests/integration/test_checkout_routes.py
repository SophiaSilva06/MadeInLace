"""Testes de integração para as rotas do Checkout / Pagamento (Regras 00, 08, 10, 11)."""

import json
from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.database import Base
from app.main import app
from app.models import (
    Carrinho,
    EnderecoUsuario,
    Fornecedor,
    ItemCarrinho,
    Linha,
    MetodoPagamento,
    Produto,
    StatusVenda,
    Usuario,
    Variacao,
    Venda,
)
from app.routers.checkout import (
    finalizar_compra_api,
    get_checkout_page,
    remover_endereco_checkout_api,
    salvar_endereco_checkout_api,
)
from app.schemas.checkout import FinalizarCompraPayload, SalvarEnderecoCheckoutPayload


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Cria banco isolado em memória com dados essenciais de domínio."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Status de venda
    for sid, estado, desc in [
        (1, "EM_PROCESSAMENTO", "Pedido em processamento"),
        (2, "NA_TRANSPORTADORA", "Pedido entregue à transportadora"),
        (3, "EM_TRANSITO", "Pedido em trânsito"),
        (4, "ENTREGANDO", "Saiu para entrega"),
        (5, "ENTREGUE", "Pedido entregue"),
        (6, "TENTATIVA_FALHA", "Tentativa de entrega sem sucesso"),
        (7, "CANCELADO", "Pedido cancelado"),
    ]:
        session.add(StatusVenda(ID=sid, ESTADO_ANDAMENTO=estado, DESCRICAO=desc))

    # Métodos de pagamento
    for mid, met in [
        (1, "Pix"),
        (2, "Cartão de crédito"),
        (3, "Cartão de débito"),
        (4, "Boleto"),
    ]:
        session.add(MetodoPagamento(ID=mid, METODO=met))

    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def seed_dados(db_session: Session) -> dict[str, int]:
    """Popula usuário, endereço, produto e variação."""
    user = Usuario(
        NOME="Camila",
        SOBRENOME="Mendes",
        CPF="98765432100",
        EMAIL="camila@exemplo.com",
        SENHA_HASH="argon2_hash",
        NASCIMENTO=date(1997, 3, 15),
        ATIVO=True,
    )
    forn = Fornecedor(
        NOME="Corseteria Real",
        CNPJ="22334455000188",
        RAZAO_SOCIAL="Corseteria Real LTDA",
        ATIVO=True,
    )
    linha = Linha(NOME="Romance")
    db_session.add_all([user, forn, linha])
    db_session.flush()

    end = EnderecoUsuario(
        FK_USUARIO=user.ID,
        NOME="Casa",
        CEP="14093238",
        LOGRADOURO="Rua Dulce Pereira Bidurin",
        NUMERO="445",
        COMPLEMENTO="",
        BAIRRO="Horizonte Verde",
        CIDADE="Ribeirão Preto",
        ESTADO="SP",
        ATIVO=True,
    )
    db_session.add(end)
    db_session.flush()

    prod = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha.ID,
        NOME="Vestido Valsa Do Luar",
        DESCRICAO="Vestido delicado.",
        TIPO="roupa",
        ATIVO=True,
    )
    db_session.add(prod)
    db_session.flush()

    var = Variacao(
        FK_PRODUTO=prod.ID,
        TAMANHO="PP",
        COR="Branco",
        ESTOQUE=10,
        CUSTO=Decimal("80.00"),
        PRECO=Decimal("230.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    db_session.add(var)
    db_session.commit()

    return {
        "usuario_id": user.ID,
        "endereco_id": end.ID,
        "variacao_id": var.ID,
    }


def test_get_checkout_deslogado_redireciona_login(db_session: Session) -> None:
    """Visitante não autenticado tentando acessar o checkout deve ser redirecionado para /login."""
    scope = {"type": "http", "method": "GET", "path": "/checkout", "headers": [], "app": app}
    req = Request(scope)

    resp = get_checkout_page(req, db=db_session)
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_get_checkout_carrinho_vazio_redireciona_carrinho(db_session: Session, seed_dados: dict[str, int]) -> None:
    """Usuário com carrinho sem itens é redirecionado para a página do carrinho com aviso."""
    uid = seed_dados["usuario_id"]
    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "GET", "path": "/checkout", "headers": headers, "app": app}
    req = Request(scope)

    resp = get_checkout_page(req, db=db_session)
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 303
    assert "/carrinho" in resp.headers["location"]
    assert "aviso=vazio" in resp.headers["location"]


def test_post_finalizar_compra_carrinho_vazio_retorna_mensagem_exigida(
    db_session: Session, seed_dados: dict[str, int]
) -> None:
    """Valida se tentar pagar com carrinho vazio retorna 'Adicione Produtos Para Ir Ao Pagamento'."""
    uid = seed_dados["usuario_id"]
    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "POST", "path": "/checkout/finalizar", "headers": headers, "app": app}
    req = Request(scope)
    payload = FinalizarCompraPayload(
        endereco_id=seed_dados["endereco_id"],
        metodo_pagamento="Pix",
    )

    resp = finalizar_compra_api(request=req, payload=payload, db=db_session)
    assert resp.status_code == 400
    data = json.loads(bytes(resp.body).decode())
    assert data["success"] is False
    assert data["message"] == "Adicione Produtos Para Ir Ao Pagamento"


def test_get_checkout_sucesso_renderiza_html(db_session: Session, seed_dados: dict[str, int]) -> None:
    """Com carrinho populado e usuário logado, renderiza o HTML do checkout com status 200."""
    uid = seed_dados["usuario_id"]
    vid = seed_dados["variacao_id"]

    # Popula carrinho
    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("230.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=vid,
        QNT=1,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "GET", "path": "/checkout", "headers": headers, "app": app}
    req = Request(scope)

    resp = get_checkout_page(req, db=db_session)
    assert isinstance(resp, HTMLResponse)
    assert resp.status_code == 200
    body_text = resp.body.decode("utf-8") if isinstance(resp.body, bytes) else bytes(resp.body).decode("utf-8")
    assert "Vestido Valsa Do Luar" in body_text
    assert "Método de pagamento" in body_text


def test_post_finalizar_compra_sucesso_persiste_venda_e_redireciona(
    db_session: Session, seed_dados: dict[str, int]
) -> None:
    """Valida se POST /checkout/finalizar gera venda com método correto e retorna redirect para /perfil/pedidos."""
    uid = seed_dados["usuario_id"]
    vid = seed_dados["variacao_id"]
    eid = seed_dados["endereco_id"]

    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("230.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=vid,
        QNT=1,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "POST", "path": "/checkout/finalizar", "headers": headers, "app": app}
    req = Request(scope)

    payload = FinalizarCompraPayload(
        endereco_id=eid,
        metodo_pagamento="PIX",
    )

    resultado = finalizar_compra_api(req, payload, db=db_session)
    assert resultado["success"] is True
    assert resultado["redirect_url"] == "/perfil/pedidos"

    # Confere se a venda existe no banco
    venda_id = resultado["venda_id"]
    venda = db_session.get(Venda, venda_id)
    assert venda is not None
    assert venda.metodo_pagamento.METODO == "Pix"
    assert venda.FK_ENDERECO_USUARIO == eid
    assert venda.status.ESTADO_ANDAMENTO == "EM_PROCESSAMENTO"


def test_post_salvar_endereco_checkout_api(db_session: Session, seed_dados: dict[str, int]) -> None:
    """Valida inclusão de endereço a partir do modal 'Modificar Endereços' no checkout."""
    uid = seed_dados["usuario_id"]
    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "POST", "path": "/checkout/endereco", "headers": headers, "app": app}
    req = Request(scope)

    payload = SalvarEnderecoCheckoutPayload(
        nome="Novo Trabalho",
        cep="14093-238",
        logradouro="Avenida Principal",
        numero="1000",
        complemento="Andar 3",
        bairro="Jardim Botânico",
        cidade="Ribeirão Preto",
        estado="SP",
    )

    resultado = salvar_endereco_checkout_api(req, payload, db=db_session)
    assert resultado["success"] is True
    assert resultado["endereco"]["nome"] == "Novo Trabalho"
    assert resultado["endereco"]["id"] is not None


@pytest.mark.parametrize(
    ("metodo_solicitado", "metodo_esperado_bd"),
    [
        ("Pix", "Pix"),
        ("Boleto", "Boleto"),
        ("Crédito", "Cartão de crédito"),
        ("Débito", "Cartão de débito"),
    ],
)
def test_post_finalizar_compra_todos_os_metodos_de_pagamento_gravados_no_banco(
    db_session: Session,
    seed_dados: dict[str, int],
    metodo_solicitado: str,
    metodo_esperado_bd: str,
) -> None:
    """Valida se cada um dos 4 métodos possíveis grava o ID e nome correspondente em VENDA."""
    uid = seed_dados["usuario_id"]
    vid = seed_dados["variacao_id"]
    eid = seed_dados["endereco_id"]

    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("230.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=vid,
        QNT=1,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "POST", "path": "/checkout/finalizar", "headers": headers, "app": app}
    req = Request(scope)

    payload = FinalizarCompraPayload(
        endereco_id=eid,
        metodo_pagamento=metodo_solicitado,
    )

    resultado = finalizar_compra_api(req, payload, db=db_session)
    assert resultado["success"] is True
    venda_id = resultado["venda_id"]
    venda = db_session.get(Venda, venda_id)
    assert venda is not None
    assert venda.metodo_pagamento.METODO == metodo_esperado_bd


def test_get_checkout_html_contem_elementos_visuais_design(db_session: Session, seed_dados: dict[str, int]) -> None:
    """Verifica se o HTML gerado inclui os elementos solicitados do design 11 e 21."""
    uid = seed_dados["usuario_id"]
    vid = seed_dados["variacao_id"]

    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("230.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=vid,
        QNT=1,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "GET", "path": "/checkout", "headers": headers, "app": app}
    req = Request(scope)

    resp = get_checkout_page(req, db=db_session)
    assert isinstance(resp, HTMLResponse)
    body = resp.body.decode("utf-8") if isinstance(resp.body, bytes) else bytes(resp.body).decode("utf-8")

    # Asserções de fidelidade visual e correções aplicadas
    assert "Pagar E Finalizar" in body
    assert "Modificar Endereços" in body
    assert "Trocar de endereço" in body
    assert "Frete Grátis" in body
    assert "checkout-item-qty-badge" in body
    assert "Desconto (1ª Compra - 10%)" in body

    # Validação do fundo bege aplicado via body_class
    assert "checkout-page-body" in body

    # Validação da logo oficial ampliada e tipografia caligráfica fiel à imagem 11
    assert "checkout-brand-logo" in body
    assert "checkout-brand-title" in body
    assert "Made In Lace" in body

    # Validação de que imagens não usam caminhos relativos quebrados (devem conter /static/)
    assert "/static/img/" in body


def test_remover_endereco_checkout_api_com_sucesso(db_session: Session, seed_dados: dict[str, int]) -> None:
    """Verifica remoção lógica de endereço via rota do checkout quando há mais de 1 endereço ativo."""
    uid = seed_dados["usuario_id"]

    # Adiciona um segundo endereço para o usuário
    end2 = EnderecoUsuario(
        FK_USUARIO=uid,
        NOME="Trabalho",
        CEP="14093238",
        LOGRADOURO="Rua Dulce Pereira Bidurin",
        NUMERO="445",
        BAIRRO="Jardim Horizonte Verde",
        CIDADE="Ribeirão Preto",
        ESTADO="SP",
        ATIVO=True,
    )
    db_session.add(end2)
    db_session.commit()
    end2_id = end2.ID

    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "POST", "path": f"/checkout/endereco/remover/{end2_id}", "headers": headers, "app": app}
    req = Request(scope)

    resp = remover_endereco_checkout_api(endereco_id=end2_id, request=req, db=db_session)
    assert resp["success"] is True
    assert "removido com sucesso" in resp["message"].lower()

    # Confirma desativação lógica
    db_session.refresh(end2)
    assert end2.ATIVO is False

    # Confirma permanência física no banco
    end_db = db_session.get(EnderecoUsuario, end2_id)
    assert end_db is not None


def test_remover_endereco_checkout_api_rejeita_se_unico(db_session: Session, seed_dados: dict[str, int]) -> None:
    """Verifica que o checkout bloqueia a remoção caso reste apenas 1 endereço ativo."""
    uid = seed_dados["usuario_id"]
    eid = seed_dados["endereco_id"]

    headers = [(b"cookie", f"user_id={uid}".encode())]
    scope = {"type": "http", "method": "POST", "path": f"/checkout/endereco/remover/{eid}", "headers": headers, "app": app}
    req = Request(scope)

    resp = remover_endereco_checkout_api(endereco_id=eid, request=req, db=db_session)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 400
    data = json.loads(bytes(resp.body).decode("utf-8"))
    assert data["success"] is False
    assert "único endereço" in data["message"].lower()

    # Confirma que o endereço único continua ATIVO=True
    end_unico = db_session.get(EnderecoUsuario, eid)
    assert end_unico is not None
    assert end_unico.ATIVO is True
