"""Testes unitários rigorosos para os filtros de template e serviços da Home page."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.dialects import mysql, sqlite
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.templates import formatar_desconto, formatar_moeda
from app.models import (
    Avaliacao,
    Fornecedor,
    ImgsProduto,
    ItemVenda,
    Linha,
    MetodoPagamento,
    Produto,
    StatusVenda,
    Variacao,
    Venda,
)
from app.services.home_service import HomeService, SqlRandom

# =====================================================================
# 1. Testes dos filtros customizados do Jinja2
# =====================================================================


def test_formatar_moeda_valores_validos() -> None:
    assert formatar_moeda(Decimal("149.90")) == "R$ 149,90"
    assert formatar_moeda(Decimal("329.99")) == "R$ 330,00" or formatar_moeda(Decimal("329.99")) == "R$ 329,99"
    assert formatar_moeda(1250.5) == "R$ 1.250,50"
    assert formatar_moeda(100) == "R$ 100,00"
    assert formatar_moeda("49.90") == "R$ 49,90"
    assert formatar_moeda(0) == "R$ 0,00"


def test_formatar_moeda_valores_nulos_e_invalidos() -> None:
    assert formatar_moeda(None) == "R$ 0,00"
    assert formatar_moeda("") == "R$ 0,00"
    assert formatar_moeda("invalido") == "R$ 0,00"
    assert formatar_moeda([]) == "R$ 0,00"


def test_formatar_desconto_valores_validos() -> None:
    assert formatar_desconto(Decimal("10.00")) == "-10%"
    assert formatar_desconto(15) == "-15%"
    assert formatar_desconto(Decimal("12.50")) == "-12,5%"
    assert formatar_desconto("20") == "-20%"


def test_formatar_desconto_valores_zerados_ou_invalidos() -> None:
    assert formatar_desconto(0) == "0%"
    assert formatar_desconto(Decimal("0.00")) == "0%"
    assert formatar_desconto(-5) == "0%"
    assert formatar_desconto(None) == "0%"
    assert formatar_desconto("abc") == "0%"


# =====================================================================
# 2. Testes de compatibilidade SQL cross-dialect (SqlRandom)
# =====================================================================


def test_sql_random_compilacao_sqlite() -> None:
    stmt = select(Linha).order_by(SqlRandom())
    compiled = str(stmt.compile(dialect=sqlite.dialect()))
    assert "ORDER BY RANDOM()" in compiled


def test_sql_random_compilacao_mysql() -> None:
    stmt = select(Linha).order_by(SqlRandom())
    compiled = str(stmt.compile(dialect=mysql.dialect()))
    assert "ORDER BY RAND()" in compiled


# =====================================================================
# 3. Testes do HomeService com SQLite em memória
# =====================================================================


def _criar_banco_teste() -> Session:
    """Cria banco SQLite em memória com schema completo para testes isolados."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_get_linhas_destaque_com_e_sem_produtos() -> None:
    session = _criar_banco_teste()

    # Cria fornecedor base
    fornecedor = Fornecedor(
        NOME="Fornecedor Teste",
        CNPJ="11222333000199",
        RAZAO_SOCIAL="Fornecedor S/A",
        ATIVO=True,
    )
    session.add(fornecedor)
    session.flush()

    # Linha 1: com produtos e imagens
    linha_com_prod = Linha(NOME="Balletcore")
    # Linha 2: vazia (sem nenhum produto vinculado)
    linha_vazia = Linha(NOME="Sem Produtos")
    session.add_all([linha_com_prod, linha_vazia])
    session.flush()

    # Produto na linha 1
    prod = Produto(
        FK_FORNECEDOR=fornecedor.ID,
        FK_LINHA=linha_com_prod.ID,
        NOME="Sapato Cetim Rosa",
        TIPO="calcado",
        ATIVO=True,
    )
    session.add(prod)
    session.flush()

    img = ImgsProduto(
        FK_PRODUTO=prod.ID,
        URL_IMAGEM="img/produtos/sapato_rosa.png",
        ATIVO=True,
    )
    var = Variacao(
        FK_PRODUTO=prod.ID,
        TAMANHO="37",
        COR="Rosa",
        ESTOQUE=10,
        CUSTO=Decimal("50.00"),
        PRECO=Decimal("150.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    session.add_all([img, var])
    session.commit()

    linhas_dto = HomeService.get_linhas_destaque(session, limit=4)
    assert len(linhas_dto) == 2

    dto_ballet = next(linha for linha in linhas_dto if linha.nome == "Balletcore")
    assert dto_ballet.total_produtos == 1
    assert dto_ballet.imagem_destaque == "img/produtos/sapato_rosa.png"
    assert len(dto_ballet.produtos) == 1
    assert dto_ballet.produtos[0].nome == "Sapato Cetim Rosa"

    dto_vazia = next(linha for linha in linhas_dto if linha.nome == "Sem Produtos")
    assert dto_vazia.total_produtos == 0
    assert dto_vazia.imagem_destaque is None
    assert dto_vazia.produtos == []


def test_get_produtos_promocao_calculo_e_avaliacoes() -> None:
    session = _criar_banco_teste()

    fornecedor = Fornecedor(
        NOME="Atelier Rendas",
        CNPJ="22333444000188",
        RAZAO_SOCIAL="Atelier Rendas Ltda",
        ATIVO=True,
    )
    linha = Linha(NOME="Corsets")
    metodo = MetodoPagamento(METODO="Pix")
    st_venda = StatusVenda(ESTADO_ANDAMENTO="ENTREGUE", DESCRICAO="Entregue")
    session.add_all([fornecedor, linha, metodo, st_venda])
    session.flush()

    # Produto 1: em promoção
    prod_promo = Produto(
        FK_FORNECEDOR=fornecedor.ID,
        FK_LINHA=linha.ID,
        NOME="Corset Dark Floral",
        TIPO="corset",
        ATIVO=True,
    )
    # Produto 2: sem promoção
    prod_normal = Produto(
        FK_FORNECEDOR=fornecedor.ID,
        FK_LINHA=linha.ID,
        NOME="Corset Basico",
        TIPO="corset",
        ATIVO=True,
    )
    session.add_all([prod_promo, prod_normal])
    session.flush()

    img_promo = ImgsProduto(
        FK_PRODUTO=prod_promo.ID,
        URL_IMAGEM="img/produtos/corset_dark.png",
        ATIVO=True,
    )
    # Variação 1 do prod_promo: 10% de promoção sobre 200.00 = 180.00
    var_promo1 = Variacao(
        FK_PRODUTO=prod_promo.ID,
        TAMANHO="P",
        COR="Preto",
        ESTOQUE=5,
        CUSTO=Decimal("80.00"),
        PRECO=Decimal("200.00"),
        PORCENTAGEM_PROMOCAO=Decimal("10.00"),
        ATIVO=True,
    )
    # Variação 2 do prod_promo: 20% de promoção sobre 200.00 = 160.00 (menor preço promocional!)
    var_promo2 = Variacao(
        FK_PRODUTO=prod_promo.ID,
        TAMANHO="M",
        COR="Preto",
        ESTOQUE=8,
        CUSTO=Decimal("80.00"),
        PRECO=Decimal("200.00"),
        PORCENTAGEM_PROMOCAO=Decimal("20.00"),
        ATIVO=True,
    )
    # Variação prod normal: 0% promoção
    var_normal = Variacao(
        FK_PRODUTO=prod_normal.ID,
        TAMANHO="P",
        COR="Branco",
        ESTOQUE=10,
        CUSTO=Decimal("50.00"),
        PRECO=Decimal("120.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    session.add_all([img_promo, var_promo1, var_promo2, var_normal])
    session.flush()

    # Venda simulada e avaliação para testar média de notas
    venda = Venda(
        FK_CARRINHO=1,
        FK_USUARIO=1,
        FK_ENDERECO_USUARIO=1,
        FK_METODO_PAGAMENTO=metodo.ID,
        FK_STATUS=st_venda.ID,
        SUBTOTAL=Decimal("160.00"),
        FRETE=Decimal("0.00"),
        DESCONTO=False,
        TOTAL=Decimal("160.00"),
        FRETE_GRATIS=True,
    )
    session.add(venda)
    session.flush()

    item_venda = ItemVenda(
        FK_VENDA=venda.ID,
        FK_VARIACAO=var_promo2.ID,
        QNT=1,
        PRECO_UNITARIO=Decimal("160.00"),
    )
    session.add(item_venda)
    session.flush()

    aval = Avaliacao(
        FK_ITEM_VENDA=item_venda.ID,
        NOTA=5,
        COMENTARIO="Perfeito!",
    )
    session.add(aval)
    session.commit()

    promos = HomeService.get_produtos_promocao(session, limit=8)
    assert len(promos) == 1
    p = promos[0]
    assert p.nome == "Corset Dark Floral"
    assert p.tem_promocao is True
    assert p.preco_promocional == Decimal("160.00")
    assert p.porcentagem_promocao == Decimal("20.00")
    assert p.imagem_principal == "img/produtos/corset_dark.png"
    assert p.media_avaliacoes == 5.0
    assert p.total_avaliacoes == 1


def test_get_produtos_best_sellers_com_vendas_e_fallback() -> None:
    session = _criar_banco_teste()

    fornecedor = Fornecedor(
        NOME="Sapateira Lume",
        CNPJ="33444555000177",
        RAZAO_SOCIAL="Lume Ltda",
        ATIVO=True,
    )
    linha = Linha(NOME="Sapatos")
    metodo = MetodoPagamento(METODO="Cartão de crédito")
    st_venda = StatusVenda(ESTADO_ANDAMENTO="ENTREGUE", DESCRICAO="Entregue")
    session.add_all([fornecedor, linha, metodo, st_venda])
    session.flush()

    p1 = Produto(FK_FORNECEDOR=fornecedor.ID, FK_LINHA=linha.ID, NOME="Sapato Mary Jane", TIPO="calcado", ATIVO=True)
    p2 = Produto(FK_FORNECEDOR=fornecedor.ID, FK_LINHA=linha.ID, NOME="Sapato Boneca", TIPO="calcado", ATIVO=True)
    p3 = Produto(FK_FORNECEDOR=fornecedor.ID, FK_LINHA=linha.ID, NOME="Sapato Salto Fino", TIPO="calcado", ATIVO=True)
    session.add_all([p1, p2, p3])
    session.flush()

    v1 = Variacao(FK_PRODUTO=p1.ID, TAMANHO="36", COR="Branco", ESTOQUE=5, CUSTO=Decimal("50"), PRECO=Decimal("150"), ATIVO=True)
    v2 = Variacao(FK_PRODUTO=p2.ID, TAMANHO="37", COR="Preto", ESTOQUE=5, CUSTO=Decimal("60"), PRECO=Decimal("170"), ATIVO=True)
    v3 = Variacao(FK_PRODUTO=p3.ID, TAMANHO="38", COR="Nude", ESTOQUE=5, CUSTO=Decimal("70"), PRECO=Decimal("190"), ATIVO=True)
    session.add_all([v1, v2, v3])
    session.flush()

    # Venda recente (ontem) para o p1
    venda_recente = Venda(
        FK_CARRINHO=1,
        FK_USUARIO=1,
        FK_ENDERECO_USUARIO=1,
        FK_METODO_PAGAMENTO=metodo.ID,
        FK_STATUS=st_venda.ID,
        SUBTOTAL=Decimal("300.00"),
        FRETE=Decimal("0.00"),
        DESCONTO=False,
        TOTAL=Decimal("300.00"),
        FRETE_GRATIS=True,
        DATA=datetime.now() - timedelta(days=2),
    )
    session.add(venda_recente)
    session.flush()

    # Vendeu 3 unidades do p1
    iv1 = ItemVenda(FK_VENDA=venda_recente.ID, FK_VARIACAO=v1.ID, QNT=3, PRECO_UNITARIO=Decimal("150"))
    session.add(iv1)
    session.commit()

    # Solicitamos limit=2: o 1º deve ser p1 (por vendas recentes), o 2º deve vir de fallback (p2)
    best_sellers = HomeService.get_produtos_best_sellers(session, limit=2, dias=30)
    assert len(best_sellers) == 2
    assert best_sellers[0].nome == "Sapato Mary Jane"
    assert best_sellers[0].total_vendido == 3
    assert best_sellers[0].is_best_seller is True

    # Segundo produto veio via fallback
    assert best_sellers[1].nome == "Sapato Boneca"
    assert best_sellers[1].is_best_seller is True


def test_get_home_data_consolidado() -> None:
    session = _criar_banco_teste()

    linha = Linha(NOME="Vintage")
    session.add(linha)
    session.commit()

    home_data = HomeService.get_home_data(session)
    assert len(home_data.linhas) == 1
    assert home_data.linhas[0].nome == "Vintage"
    assert isinstance(home_data.produtos_promocao, list)
    assert isinstance(home_data.produtos_best_sellers, list)
