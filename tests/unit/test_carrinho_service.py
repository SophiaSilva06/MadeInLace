"""Testes unitários rigorosos para o CarrinhoService (Regras de Negócio Seções 8, 9, 11)."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import Fornecedor, Linha, Produto, Usuario, Variacao
from app.services.carrinho_service import CarrinhoService


@pytest.fixture
def db_session() -> Session:
    """Cria uma sessão isolada com SQLite em memória para os testes de unidade do carrinho."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        return session
    finally:
        session.close()


@pytest.fixture
def seed_dados_carrinho(db_session: Session) -> dict[str, int]:
    """Cria usuário, fornecedor, linha, produto e variações para teste."""
    user = Usuario(
        NOME="Isabella",
        SOBRENOME="Swan",
        CPF="11122233344",
        EMAIL="isabella@exemplo.com",
        SENHA_HASH="hash_argon2_valido",
        NASCIMENTO=date(2000, 5, 20),
        ATIVO=True,
    )
    forn = Fornecedor(
        NOME="Atelier de Sapatos",
        CNPJ="99888777000166",
        RAZAO_SOCIAL="Atelier Sapatos Ltda",
        ATIVO=True,
    )
    linha = Linha(NOME="Romance")
    db_session.add_all([user, forn, linha])
    db_session.flush()

    prod = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha.ID,
        NOME="Salto de Couro Oxford",
        DESCRICAO="Salto elegante em couro marrom oxford.",
        TIPO="calcado",
        ATIVO=True,
    )
    db_session.add(prod)
    db_session.flush()

    # Variação 1: Preço 180.00, sem promoção, estoque 5
    v1 = Variacao(
        FK_PRODUTO=prod.ID,
        TAMANHO="38",
        COR="Branco",
        ESTOQUE=5,
        CUSTO=Decimal("80.00"),
        PRECO=Decimal("180.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    # Variação 2: Preço 100.00, promoção 20% -> Preço final 80.00, estoque 15
    v2 = Variacao(
        FK_PRODUTO=prod.ID,
        TAMANHO="37",
        COR="Marrom",
        ESTOQUE=15,
        CUSTO=Decimal("50.00"),
        PRECO=Decimal("100.00"),
        PORCENTAGEM_PROMOCAO=Decimal("20.00"),
        ATIVO=True,
    )
    # Variação 3: Estoque esgotado (0)
    v3 = Variacao(
        FK_PRODUTO=prod.ID,
        TAMANHO="39",
        COR="Preto",
        ESTOQUE=0,
        CUSTO=Decimal("80.00"),
        PRECO=Decimal("180.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )

    db_session.add_all([v1, v2, v3])
    db_session.commit()

    return {
        "usuario_id": user.ID,
        "produto_id": prod.ID,
        "v1_id": v1.ID,
        "v2_id": v2.ID,
        "v3_id": v3.ID,
    }


def test_obter_ou_criar_carrinho_ativo(db_session: Session, seed_dados_carrinho: dict[str, int]) -> None:
    """Verifica se um carrinho ativo é criado caso não exista, e reutilizado se já existir."""
    uid = seed_dados_carrinho["usuario_id"]

    cart1 = CarrinhoService.obter_ou_criar_carrinho_ativo(db_session, uid)
    assert cart1.ID is not None
    assert cart1.STATUS == "ATIVO"
    assert cart1.TOTAL == Decimal("0.00")
    assert cart1.FRETE_GRATIS is False

    cart2 = CarrinhoService.obter_ou_criar_carrinho_ativo(db_session, uid)
    assert cart2.ID == cart1.ID


def test_calcular_preco_promocional(db_session: Session, seed_dados_carrinho: dict[str, int]) -> None:
    """Valida o cálculo do preço com e sem promoção."""
    v1 = db_session.get(Variacao, seed_dados_carrinho["v1_id"])
    v2 = db_session.get(Variacao, seed_dados_carrinho["v2_id"])
    assert v1 is not None and v2 is not None

    p1 = CarrinhoService.calcular_preco_unitario(v1)
    assert p1 == Decimal("180.00")

    p2 = CarrinhoService.calcular_preco_unitario(v2)
    assert p2 == Decimal("80.00")  # 100 - 20%


def test_adicionar_item_e_timer_de_reserva(
    db_session: Session, seed_dados_carrinho: dict[str, int]
) -> None:
    """Valida a adição de produto, cálculo do timer de 10 min e regra do frete grátis (>= 160)."""
    uid = seed_dados_carrinho["usuario_id"]
    v1_id = seed_dados_carrinho["v1_id"]

    # Adiciona 1 unidade de R$ 180.00
    cart_dto = CarrinhoService.adicionar_item(
        db_session,
        usuario_id=uid,
        variacao_id=v1_id,
        quantidade=1,
    )

    assert cart_dto.quantidade_total == 1
    assert cart_dto.total == 180.0
    assert cart_dto.frete_gratis is True  # 180 >= 160
    assert cart_dto.valor_para_frete_gratis == 0.0
    assert len(cart_dto.itens) == 1

    item = cart_dto.itens[0]
    assert item.quantidade == 1
    assert item.preco_unitario == 180.0
    assert item.preco_unitario_formatado == "R$ 180,00"
    assert item.segundos_restantes > 550.0  # ~600 segundos (10 min)
    assert item.expirado is False


def test_frete_gratis_incompleto_e_completo(
    db_session: Session, seed_dados_carrinho: dict[str, int]
) -> None:
    """Valida o medidor de frete grátis (R$ 160,00) em valores abaixo e acima."""
    uid = seed_dados_carrinho["usuario_id"]
    v2_id = seed_dados_carrinho["v2_id"]  # R$ 80.00

    # 1 unidade = R$ 80.00 (faltam R$ 80.00)
    cart_dto = CarrinhoService.adicionar_item(
        db_session,
        usuario_id=uid,
        variacao_id=v2_id,
        quantidade=1,
    )
    assert cart_dto.total == 80.0
    assert cart_dto.frete_gratis is False
    assert cart_dto.valor_para_frete_gratis == 80.0
    assert cart_dto.porcentagem_frete_gratis == 50.0

    # Adiciona mais 1 unidade = 2 * 80 = R$ 160.00 (Frete Grátis alcançado!)
    cart_dto2 = CarrinhoService.adicionar_item(
        db_session,
        usuario_id=uid,
        variacao_id=v2_id,
        quantidade=1,
    )
    assert cart_dto2.total == 160.0
    assert cart_dto2.frete_gratis is True
    assert cart_dto2.valor_para_frete_gratis == 0.0
    assert cart_dto2.porcentagem_frete_gratis == 100.0


def test_limite_maximo_10_unidades(
    db_session: Session, seed_dados_carrinho: dict[str, int]
) -> None:
    """Verifica que não permite ultrapassar 10 unidades da mesma variação (Seção 9)."""
    uid = seed_dados_carrinho["usuario_id"]
    v2_id = seed_dados_carrinho["v2_id"]

    # Adiciona 10 unidades (permitido)
    CarrinhoService.adicionar_item(
        db_session,
        usuario_id=uid,
        variacao_id=v2_id,
        quantidade=10,
    )

    # Tentar adicionar a 11ª deve falhar
    with pytest.raises(ValueError, match="Máximo de 10 unidades"):
        CarrinhoService.adicionar_item(
            db_session,
            usuario_id=uid,
            variacao_id=v2_id,
            quantidade=1,
        )


def test_estoque_insuficiente(db_session: Session, seed_dados_carrinho: dict[str, int]) -> None:
    """Verifica erro quando o estoque disponível for menor que a quantidade pedida."""
    uid = seed_dados_carrinho["usuario_id"]
    v3_id = seed_dados_carrinho["v3_id"]  # estoque 0

    with pytest.raises(ValueError, match="Estoque insuficiente"):
        CarrinhoService.adicionar_item(
            db_session,
            usuario_id=uid,
            variacao_id=v3_id,
            quantidade=1,
        )


def test_atualizar_quantidade_e_remover_item(
    db_session: Session, seed_dados_carrinho: dict[str, int]
) -> None:
    """Valida alteração de quantidade e remoção do item pelo ID."""
    uid = seed_dados_carrinho["usuario_id"]
    v1_id = seed_dados_carrinho["v1_id"]

    cart_dto = CarrinhoService.adicionar_item(
        db_session,
        usuario_id=uid,
        variacao_id=v1_id,
        quantidade=1,
    )
    item_id = cart_dto.itens[0].id

    # Atualiza para 3 unidades
    cart_atualizado = CarrinhoService.atualizar_quantidade(
        db_session,
        usuario_id=uid,
        item_id=item_id,
        nova_quantidade=3,
    )
    assert cart_atualizado.quantidade_total == 3
    assert cart_atualizado.total == 540.0  # 3 * 180

    # Remove o item
    cart_pos_remocao = CarrinhoService.remover_item(
        db_session,
        usuario_id=uid,
        item_id=item_id,
    )
    assert cart_pos_remocao.quantidade_total == 0
    assert cart_pos_remocao.total == 0.0
    assert len(cart_pos_remocao.itens) == 0


def test_remover_item_idempotente_segunda_chamada(
    db_session: Session, seed_dados_carrinho: dict[str, int]
) -> None:
    """Garante que remoções repetidas ou concorrentes do mesmo item sejam idempotentes e não lancem erro."""
    uid = seed_dados_carrinho["usuario_id"]
    v1_id = seed_dados_carrinho["v1_id"]

    cart_dto = CarrinhoService.adicionar_item(
        db_session,
        usuario_id=uid,
        variacao_id=v1_id,
        quantidade=1,
    )
    item_id = cart_dto.itens[0].id

    # Primeira remoção: sucesso
    res1 = CarrinhoService.remover_item(db_session, usuario_id=uid, item_id=item_id)
    assert res1.quantidade_total == 0

    # Segunda remoção do mesmo item_id: deve ser idempotente, sem estourar ValueError
    res2 = CarrinhoService.remover_item(db_session, usuario_id=uid, item_id=item_id)
    assert res2.quantidade_total == 0
    assert len(res2.itens) == 0
