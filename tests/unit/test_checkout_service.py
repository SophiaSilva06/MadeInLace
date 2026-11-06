"""Testes unitários rigorosos para o CheckoutService (Regras de Negócio Seções 10, 11 e Anexo A)."""

from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
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
from app.services.checkout_service import CheckoutService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Cria uma sessão isolada com SQLite em memória com os domínios essenciais."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Seed de status de venda
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

    # Seed de métodos de pagamento (conforme db/schema.sql)
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
def seed_dados_checkout(db_session: Session) -> dict[str, int]:
    """Cria usuário, endereços, catálogo e variações com estoque."""
    user = Usuario(
        NOME="Sophia",
        SOBRENOME="Lace",
        CPF="12345678901",
        EMAIL="sophia@madeinlace.com",
        SENHA_HASH="argon2_hash_seguro",
        NASCIMENTO=date(2001, 8, 12),
        ATIVO=True,
    )
    forn = Fornecedor(
        NOME="Atelier Francês",
        CNPJ="12345678000199",
        RAZAO_SOCIAL="Atelier Francês LTDA",
        ATIVO=True,
    )
    linha = Linha(NOME="Noiva e Festa")
    db_session.add_all([user, forn, linha])
    db_session.flush()

    # Endereço 1: Principal (Casa, SP)
    end1 = EnderecoUsuario(
        FK_USUARIO=user.ID,
        NOME="Casa",
        CEP="14093238",
        LOGRADOURO="Rua Dulce Pereira Bidurin",
        NUMERO="445",
        COMPLEMENTO="Casa de esquina",
        BAIRRO="Horizonte Verde",
        CIDADE="Ribeirão Preto",
        ESTADO="SP",
        ATIVO=True,
    )
    # Endereço 2: Secundário (Trabalho, RJ)
    end2 = EnderecoUsuario(
        FK_USUARIO=user.ID,
        NOME="Trabalho",
        CEP="20000000",
        LOGRADOURO="Avenida Rio Branco",
        NUMERO="100",
        COMPLEMENTO="Sala 501",
        BAIRRO="Centro",
        CIDADE="Rio de Janeiro",
        ESTADO="RJ",
        ATIVO=True,
    )
    db_session.add_all([end1, end2])
    db_session.flush()

    # Produto 1: Vestido Valsa Do Luar (conforme imagem 11)
    p1 = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha.ID,
        NOME="Vestido Valsa Do Luar",
        DESCRICAO="Vestido luxuoso com detalhes em renda e corset ajustado.",
        TIPO="roupa",
        ATIVO=True,
    )
    # Produto 2: Vestido Dança Das Borboletas (conforme imagem 11)
    p2 = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha.ID,
        NOME="Vestido Dança Das Borboletas",
        DESCRICAO="Vestido em seda acetinada e espartilho rendado.",
        TIPO="roupa",
        ATIVO=True,
    )
    db_session.add_all([p1, p2])
    db_session.flush()

    # Variações
    v1 = Variacao(
        FK_PRODUTO=p1.ID,
        TAMANHO="PP",
        COR="Branco",
        ESTOQUE=5,
        CUSTO=Decimal("100.00"),
        PRECO=Decimal("230.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    v2 = Variacao(
        FK_PRODUTO=p2.ID,
        TAMANHO="PP",
        COR="Branco",
        ESTOQUE=4,
        CUSTO=Decimal("120.00"),
        PRECO=Decimal("270.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    db_session.add_all([v1, v2])
    db_session.commit()

    return {
        "usuario_id": user.ID,
        "endereco_principal_id": end1.ID,
        "endereco_secundario_id": end2.ID,
        "variacao_1_id": v1.ID,
        "variacao_2_id": v2.ID,
    }


def test_obter_resumo_checkout_carrinho_vazio_lanca_excecao(
    db_session: Session, seed_dados_checkout: dict[str, int]
) -> None:
    """Verifica se obter_resumo_checkout rejeita checkout com carrinho sem itens."""
    uid = seed_dados_checkout["usuario_id"]
    with pytest.raises(ValueError, match="Carrinho vazio"):
        CheckoutService.obter_resumo_checkout(db_session, uid)


def test_obter_resumo_checkout_primeira_compra_com_desconto_10(
    db_session: Session, seed_dados_checkout: dict[str, int]
) -> None:
    """Valida o cálculo exato do checkout para primeira compra com 10% de desconto sobre o subtotal."""
    uid = seed_dados_checkout["usuario_id"]
    v1_id = seed_dados_checkout["variacao_1_id"]
    v2_id = seed_dados_checkout["variacao_2_id"]

    # Cria carrinho ativo com os itens da imagem 11 (Valsa Do Luar: 230 + Dança Das Borboletas: 270 = 500)
    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("500.00"), DATA_CRIACAO=datetime.now())
    db_session.add(carrinho)
    db_session.flush()

    item1 = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=v1_id,
        QNT=1,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    item2 = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=v2_id,
        QNT=1,
        PRECO_UNITARIO=Decimal("270.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add_all([item1, item2])
    db_session.commit()

    resumo = CheckoutService.obter_resumo_checkout(db_session, uid)

    assert resumo["subtotal"] == Decimal("500.00")
    assert resumo["primeira_compra"] is True
    assert resumo["valor_desconto"] == Decimal("50.00")  # 10% de 500.00
    # Base frete = 500 - 50 = 450 >= 160 -> Frete Grátis!
    assert resumo["frete"] == Decimal("0.00")
    assert resumo["frete_gratis"] is True
    assert resumo["total"] == Decimal("450.00")
    assert resumo["endereco_selecionado"]["id"] == seed_dados_checkout["endereco_principal_id"]
    assert len(resumo["itens"]) == 2


def test_obter_resumo_checkout_nao_primeira_compra_sem_desconto_e_frete_anexo_a(
    db_session: Session, seed_dados_checkout: dict[str, int]
) -> None:
    """Se o usuário já tem pedido anterior concluído, não ganha 10% e frete é cobrado abaixo de 160."""
    uid = seed_dados_checkout["usuario_id"]
    v1_id = seed_dados_checkout["variacao_1_id"]
    end_rj = seed_dados_checkout["endereco_secundario_id"]

    # Simula venda anterior não cancelada
    carrinho_antigo = Carrinho(FK_USUARIO=uid, STATUS="CONVERTIDO", TOTAL=Decimal("200.00"))
    db_session.add(carrinho_antigo)
    db_session.flush()

    venda_antiga = Venda(
        FK_CARRINHO=carrinho_antigo.ID,
        FK_USUARIO=uid,
        FK_ENDERECO_USUARIO=end_rj,
        FK_METODO_PAGAMENTO=1,
        FK_STATUS=5,  # Entregue
        SUBTOTAL=Decimal("200.00"),
        FRETE=Decimal("0.00"),
        DESCONTO=True,
        TOTAL=Decimal("180.00"),
        FRETE_GRATIS=True,
    )
    db_session.add(venda_antiga)
    db_session.commit()

    # Novo carrinho com apenas 1 item de R$ 100.00 (abaixo de R$ 160)
    carrinho_atual = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("100.00"))
    db_session.add(carrinho_atual)
    db_session.flush()

    # Variação com preço de catálogo 100.00 (para testar subtotal abaixo de 160)
    v_abaixo = Variacao(
        FK_PRODUTO=seed_dados_checkout["variacao_1_id"],  # produto id
        TAMANHO="P",
        COR="Nude",
        ESTOQUE=5,
        CUSTO=Decimal("40.00"),
        PRECO=Decimal("100.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    # Ajusta FK_PRODUTO correto
    v_ref = db_session.get(Variacao, v1_id)
    assert v_ref is not None
    v_abaixo.FK_PRODUTO = v_ref.FK_PRODUTO
    db_session.add(v_abaixo)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho_atual.ID,
        FK_VARIACAO=v_abaixo.ID,
        QNT=1,
        PRECO_UNITARIO=Decimal("100.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    # Selecionando o endereço do RJ (Frete do RJ na tabela do Anexo A é R$ 19,90)
    resumo = CheckoutService.obter_resumo_checkout(db_session, uid, endereco_id_selecionado=end_rj)

    assert resumo["subtotal"] == Decimal("100.00")
    assert resumo["primeira_compra"] is False
    assert resumo["valor_desconto"] == Decimal("0.00")
    assert resumo["frete_gratis"] is False
    assert resumo["frete"] == Decimal("19.90")  # Tabela Anexo A: RJ = 19.90
    assert resumo["total"] == Decimal("119.90")


def test_finalizar_compra_grava_dados_e_metodo_no_banco(
    db_session: Session, seed_dados_checkout: dict[str, int]
) -> None:
    """Verifica se a finalização grava a VENDA com o método selecionado, decrementa estoque e converte o carrinho."""
    uid = seed_dados_checkout["usuario_id"]
    v1_id = seed_dados_checkout["variacao_1_id"]
    end_id = seed_dados_checkout["endereco_principal_id"]

    # Cria carrinho ativo com 2 unidades
    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("460.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=v1_id,
        QNT=2,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    var_inicial = db_session.get(Variacao, v1_id)
    assert var_inicial is not None
    estoque_inicial = var_inicial.ESTOQUE

    # Finaliza a compra selecionando "Cartão de crédito"
    venda = CheckoutService.finalizar_compra(
        db=db_session,
        usuario_id=uid,
        endereco_id=end_id,
        metodo_pagamento="Cartão de crédito",
    )

    assert venda.ID is not None
    assert venda.FK_USUARIO == uid
    assert venda.FK_ENDERECO_USUARIO == end_id
    assert venda.metodo_pagamento.METODO == "Cartão de crédito"
    assert venda.status.ESTADO_ANDAMENTO == "EM_PROCESSAMENTO"
    assert venda.SUBTOTAL == Decimal("460.00")

    # Verifica se histórico de status foi registrado
    assert len(venda.historico_status) == 1
    assert venda.historico_status[0].FK_STATUS_VENDA == venda.FK_STATUS

    # Verifica itens da venda
    assert len(venda.itens) == 1
    assert venda.itens[0].FK_VARIACAO == v1_id
    assert venda.itens[0].QNT == 2
    assert venda.itens[0].PRECO_UNITARIO == Decimal("230.00")

    # Verifica se o estoque da variação foi decrementado
    variacao_pos = db_session.get(Variacao, v1_id)
    assert variacao_pos is not None
    assert variacao_pos.ESTOQUE == estoque_inicial - 2

    # Verifica se o carrinho foi convertido
    carrinho_pos = db_session.get(Carrinho, carrinho.ID)
    assert carrinho_pos is not None
    assert carrinho_pos.STATUS == "CONVERTIDO"


@pytest.mark.parametrize(
    ("metodo_input", "metodo_esperado"),
    [
        ("PIX", "Pix"),
        ("Pix", "Pix"),
        ("Boleto", "Boleto"),
        ("Crédito", "Cartão de crédito"),
        ("Cartão de crédito", "Cartão de crédito"),
        ("Débito", "Cartão de débito"),
        ("Cartão de débito", "Cartão de débito"),
    ],
)
def test_finalizar_compra_mapeamento_flexivel_metodos_pagamento(
    db_session: Session,
    seed_dados_checkout: dict[str, int],
    metodo_input: str,
    metodo_esperado: str,
) -> None:
    """Garante que qualquer variante dos 4 métodos aceitos grave o registro exato no banco."""
    uid = seed_dados_checkout["usuario_id"]
    v2_id = seed_dados_checkout["variacao_2_id"]
    end_id = seed_dados_checkout["endereco_principal_id"]

    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("270.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=v2_id,
        QNT=1,
        PRECO_UNITARIO=Decimal("270.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    venda = CheckoutService.finalizar_compra(
        db=db_session,
        usuario_id=uid,
        endereco_id=end_id,
        metodo_pagamento=metodo_input,
    )

    assert venda.metodo_pagamento.METODO == metodo_esperado


def test_finalizar_compra_estoque_insuficiente_rejeita(
    db_session: Session, seed_dados_checkout: dict[str, int]
) -> None:
    """Impede a finalização da compra se o estoque físico for menor do que a quantidade solicitada."""
    uid = seed_dados_checkout["usuario_id"]
    v1_id = seed_dados_checkout["variacao_1_id"]
    end_id = seed_dados_checkout["endereco_principal_id"]

    # Reduz estoque para 1
    var = db_session.get(Variacao, v1_id)
    assert var is not None
    var.ESTOQUE = 1
    db_session.commit()

    # Carrinho solicita 2 unidades
    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("460.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=v1_id,
        QNT=2,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    with pytest.raises(ValueError, match="Estoque insuficiente"):
        CheckoutService.finalizar_compra(
            db=db_session,
            usuario_id=uid,
            endereco_id=end_id,
            metodo_pagamento="Pix",
        )


@pytest.mark.parametrize(
    ("url_entrada", "url_esperada"),
    [
        ("img/produtos/morning-dew-corset-1.png", "/static/img/produtos/morning-dew-corset-1.png"),
        ("img/produtos/satin-mary-jane-heels-1.png", "/static/img/produtos/satin-mary-jane-heels-1.png"),
        ("/img/produtos/corset.png", "/static/img/produtos/corset.png"),
        ("/static/img/produtos/foto.png", "/static/img/produtos/foto.png"),
        ("https://cdn.exemplo.com/foto.png", "https://cdn.exemplo.com/foto.png"),
        (None, "/static/img/site/MadeInLaceLogo.png"),
        ("", "/static/img/site/MadeInLaceLogo.png"),
        ("   ", "/static/img/site/MadeInLaceLogo.png"),
    ],
)
def test_formatar_url_imagem_seguranca_e_prefixo_static(url_entrada: str | None, url_esperada: str) -> None:
    """Garante que qualquer formato de URL de imagem de produto seja prefixado com /static/ para evitar erro 404."""
    assert CheckoutService.formatar_url_imagem(url_entrada) == url_esperada


def test_obter_resumo_checkout_itens_com_imagens_prefixadas_com_static(
    db_session: Session, seed_dados_checkout: dict[str, int]
) -> None:
    """Verifica se as URLs de imagens retornadas pelo resumo de checkout sempre iniciam com /static/."""
    from app.models.produto import ImgsProduto

    uid = seed_dados_checkout["usuario_id"]
    v1_id = seed_dados_checkout["variacao_1_id"]
    v1 = db_session.get(Variacao, v1_id)
    assert v1 is not None

    # Adiciona imagem ao produto com formato relativo padrão do banco
    img_prod = ImgsProduto(
        FK_PRODUTO=v1.FK_PRODUTO,
        URL_IMAGEM="img/produtos/morning-dew-corset-1.png",
        ATIVO=True,
    )
    db_session.add(img_prod)

    carrinho = Carrinho(FK_USUARIO=uid, STATUS="ATIVO", TOTAL=Decimal("230.00"))
    db_session.add(carrinho)
    db_session.flush()

    item = ItemCarrinho(
        FK_CARRINHO=carrinho.ID,
        FK_VARIACAO=v1_id,
        QNT=1,
        PRECO_UNITARIO=Decimal("230.00"),
        RESERVADO_ATE=datetime.now(),
    )
    db_session.add(item)
    db_session.commit()

    resumo = CheckoutService.obter_resumo_checkout(db_session, uid)
    assert len(resumo["itens"]) == 1
    assert resumo["itens"][0]["imagem_url"].startswith("/static/")
    assert resumo["itens"][0]["imagem_url"] == "/static/img/produtos/morning-dew-corset-1.png"
