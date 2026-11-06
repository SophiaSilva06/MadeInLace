"""Testes de integração end-to-end para a rota Home (GET /) e integridade do app FastAPI."""

from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.database import Base
from app.main import app, health_check
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
from app.routers.auth import get_login, get_registro
from app.routers.carrinho import get_carrinho
from app.routers.catalogo import detalhe_produto, listar_catalogo
from app.routers.home import get_home
from app.routers.perfil import get_perfil


@pytest.fixture
def db_session() -> Session:
    """Cria uma sessão isolada com SQLite em memória para os testes de integração."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        return session
    finally:
        pass


def test_health_check_endpoint() -> None:
    """Verifica se o endpoint de integridade responde com status ok e nome correto."""
    data = health_check()
    assert data["status"] == "ok"
    assert data["app"] == "MadeInLace"


def test_home_page_banco_vazio(db_session: Session) -> None:
    """Valida se a rota GET / funciona graciosamente mesmo quando o banco não possui dados."""
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "app": app}
    req = Request(scope)

    response = get_home(req, db_session)
    assert isinstance(response, HTMLResponse)
    assert response.status_code == 200

    html = bytes(response.body).decode("utf-8")
    assert "Made In Lace" in html
    assert "Linhas" in html
    assert "Promoções" in html
    assert "Mais Vendidos" in html


def test_home_page_usuario_logado_exibe_minha_conta(db_session: Session) -> None:
    """Valida se a rota GET / reconhece o usuário autenticado via cookie e exibe Minha Conta no header."""
    from datetime import date

    from app.core.security import hash_password
    from app.models import Usuario

    user = Usuario(
        NOME="Juliana",
        SOBRENOME="Paes",
        EMAIL="juliana@exemplo.com",
        SENHA_HASH=hash_password("SenhaForte2026!#"),
        NASCIMENTO=date(1992, 4, 15),
        CPF="12345678955",
        TELEFONE="11988887777",
        ATIVO=True,
    )
    db_session.add(user)
    db_session.commit()

    cookie_header = (b"cookie", f"user_id={user.ID}".encode("ascii"))
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [cookie_header],
        "app": app,
    }
    req = Request(scope)
    response = get_home(req, db_session)
    assert isinstance(response, HTMLResponse)
    html = bytes(response.body).decode("utf-8")
    assert "/perfil" in html
    assert "Minha Conta" in html


def test_home_page_com_dados_completos(db_session: Session) -> None:
    """Valida renderização completa da Home com produtos, imagens, promoções e best sellers."""
    # 1. Domínio e Fornecedor
    fornecedor = Fornecedor(
        NOME="Atelier Rosa Velha",
        CNPJ="11222333000181",
        RAZAO_SOCIAL="Rosa Velha Confecções Ltda",
        ATIVO=True,
    )
    linha1 = Linha(NOME="Balletcore")
    linha2 = Linha(NOME="Romantic Vintage")
    metodo = MetodoPagamento(METODO="Pix")
    st_venda = StatusVenda(ESTADO_ANDAMENTO="ENTREGUE", DESCRICAO="Entregue")
    db_session.add_all([fornecedor, linha1, linha2, metodo, st_venda])
    db_session.flush()

    # 2. Produtos
    p1 = Produto(
        FK_FORNECEDOR=fornecedor.ID,
        FK_LINHA=linha1.ID,
        NOME="Balletcore Heels",
        DESCRICAO="Sapato de cetim rosa claro com laços.",
        TIPO="calcado",
        ATIVO=True,
    )
    p2 = Produto(
        FK_FORNECEDOR=fornecedor.ID,
        FK_LINHA=linha2.ID,
        NOME="Pink Butterfly Dress",
        DESCRICAO="Vestido midi rosa com renda.",
        TIPO="roupa",
        ATIVO=True,
    )
    db_session.add_all([p1, p2])
    db_session.flush()

    # 3. Imagens e Variações
    img1 = ImgsProduto(
        FK_PRODUTO=p1.ID,
        URL_IMAGEM="img/produtos/balletcore-heels-1.png",
        ATIVO=True,
    )
    img2 = ImgsProduto(
        FK_PRODUTO=p2.ID,
        URL_IMAGEM="img/produtos/pink-butterfly-dress-1.png",
        ATIVO=True,
    )
    # p1 com preço normal R$ 329,90
    var1 = Variacao(
        FK_PRODUTO=p1.ID,
        TAMANHO="37",
        COR="Rosa claro",
        ESTOQUE=10,
        CUSTO=Decimal("148.00"),
        PRECO=Decimal("329.90"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    # p2 em promoção de 20%: R$ 419,90 -> R$ 335,92
    var2 = Variacao(
        FK_PRODUTO=p2.ID,
        TAMANHO="M",
        COR="Rosa",
        ESTOQUE=8,
        CUSTO=Decimal("180.00"),
        PRECO=Decimal("419.90"),
        PORCENTAGEM_PROMOCAO=Decimal("20.00"),
        ATIVO=True,
    )
    db_session.add_all([img1, img2, var1, var2])
    db_session.flush()

    # 4. Venda recente e Avaliação para p1
    venda = Venda(
        FK_CARRINHO=1,
        FK_USUARIO=1,
        FK_ENDERECO_USUARIO=1,
        FK_METODO_PAGAMENTO=metodo.ID,
        FK_STATUS=st_venda.ID,
        SUBTOTAL=Decimal("329.90"),
        FRETE=Decimal("0.00"),
        DESCONTO=False,
        TOTAL=Decimal("329.90"),
        FRETE_GRATIS=True,
        DATA=datetime.now() - timedelta(days=5),
    )
    db_session.add(venda)
    db_session.flush()

    item_venda = ItemVenda(
        FK_VENDA=venda.ID,
        FK_VARIACAO=var1.ID,
        QNT=2,
        PRECO_UNITARIO=Decimal("329.90"),
    )
    db_session.add(item_venda)
    db_session.flush()

    avaliacao = Avaliacao(
        FK_ITEM_VENDA=item_venda.ID,
        NOTA=5,
        COMENTARIO="Sapato impecável e super confortável!",
    )
    db_session.add(avaliacao)
    db_session.commit()

    # Requisição direta à rota GET /
    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "app": app}
    req = Request(scope)

    response = get_home(req, db_session)
    assert response.status_code == 200
    html = bytes(response.body).decode("utf-8")

    # Verifica presença dos elementos essenciais
    assert "Balletcore" in html
    assert "Balletcore Heels" in html
    assert "Pink Butterfly Dress" in html
    assert "img/produtos/balletcore-heels-1.png" in html
    assert "img/produtos/pink-butterfly-dress-1.png" in html

    # Verifica formatação monetária e de desconto
    assert "R$ 329,90" in html
    assert "R$ 419,90" in html
    assert "R$ 335,92" in html
    assert "-20%" in html
    assert "Mais Vendidos" in html

    # Verifica nota da avaliação exibida
    assert "5.0" in html


def test_arquivos_estaticos_existem() -> None:
    """Valida se os arquivos estáticos essenciais estão presentes no sistema de arquivos."""
    base_dir = Path(__file__).resolve().parent.parent.parent / "app" / "static"
    assert (base_dir / "css" / "style.css").exists()
    assert (base_dir / "img" / "site" / "MadeInLaceLogo.png").exists()
    assert (base_dir / "img" / "site" / "MadeInLaceCarrossel1.png").exists()
    assert (base_dir / "img" / "site" / "MadeInLaceCarrossel2.png").exists()


def test_rota_login_preenche_email() -> None:
    """Valida se o endpoint GET /login recebe o email e renderiza preenchido no input."""
    scope = {"type": "http", "method": "GET", "path": "/login", "headers": [], "app": app}
    req = Request(scope)
    response = get_login(req, email="cliente@exemplo.com", promo="10off")

    assert response.status_code == 200
    html = bytes(response.body).decode("utf-8")
    assert 'value="cliente@exemplo.com"' in html
    assert "10% Off Ativado Caso Seja Sua Primeira Compra! Conclua O Login E Aproveite" in html


def test_rota_registro_render() -> None:
    """Valida se o endpoint GET /registro responde com status 200 e campos de cadastro."""
    scope = {"type": "http", "method": "GET", "path": "/registro", "headers": [], "app": app}
    req = Request(scope)
    response = get_registro(req)

    assert response.status_code == 200
    html = bytes(response.body).decode("utf-8")
    assert "Registrar-se" in html
    assert "Adicionar Endereço" in html
    assert "Continuar" in html


def test_rota_carrinho_e_perfil() -> None:
    """Valida se os endpoints /carrinho e /perfil/{secao} respondem com status 200."""
    # Carrinho
    scope_carrinho = {"type": "http", "method": "GET", "path": "/carrinho", "headers": [], "app": app}
    res_carrinho = get_carrinho(Request(scope_carrinho))
    assert res_carrinho.status_code == 200
    assert "Sua Sacola de Compras" in bytes(res_carrinho.body).decode("utf-8")

    # Perfil - Guia de tamanhos
    scope_tamanhos = {"type": "http", "method": "GET", "path": "/perfil/tamanhos", "headers": [], "app": app}
    res_tamanhos = get_perfil(Request(scope_tamanhos), secao="tamanhos")
    assert res_tamanhos.status_code == 200
    assert "Guia de Tamanhos" in bytes(res_tamanhos.body).decode("utf-8")

    # Perfil - Contatos
    scope_contatos = {"type": "http", "method": "GET", "path": "/perfil/contatos", "headers": [], "app": app}
    res_contatos = get_perfil(Request(scope_contatos), secao="contatos")
    assert res_contatos.status_code == 200
    assert "Contatos & Suporte" in bytes(res_contatos.body).decode("utf-8")


def test_rota_catalogo_e_detalhe_produto(db_session: Session) -> None:
    """Valida se /catalogo e /produtos/{id} respondem corretamente com os dados do banco."""
    # Injeta um produto no banco de teste
    fornecedor = Fornecedor(
        NOME="Atelier Rosa",
        CNPJ="99888777000166",
        RAZAO_SOCIAL="Rosa Confecções",
        ATIVO=True,
    )
    linha = Linha(NOME="Romantic Corsets")
    db_session.add_all([fornecedor, linha])
    db_session.flush()

    prod = Produto(
        FK_FORNECEDOR=fornecedor.ID,
        FK_LINHA=linha.ID,
        NOME="Corset Vintage Marfim",
        DESCRICAO="Corset marfim com laços de cetim e acabamento em renda.",
        TIPO="corset",
        ATIVO=True,
    )
    db_session.add(prod)
    db_session.flush()

    var = Variacao(
        FK_PRODUTO=prod.ID,
        TAMANHO="M",
        COR="Marfim",
        ESTOQUE=5,
        CUSTO=Decimal("100.00"),
        PRECO=Decimal("250.00"),
        PORCENTAGEM_PROMOCAO=Decimal("10.00"),
        ATIVO=True,
    )
    db_session.add(var)
    db_session.commit()

    scope = {"type": "http", "method": "GET", "path": "/catalogo", "headers": [], "app": app}
    req = Request(scope)

    # 1. Catálogo geral
    res_cat = listar_catalogo(req, db_session)
    assert res_cat.status_code == 200
    assert "Corset Vintage Marfim" in bytes(res_cat.body).decode("utf-8")

    # 2. Busca por linha
    res_linha = listar_catalogo(req, db_session, linha="Romantic Corsets")
    assert res_linha.status_code == 200
    assert "Corset Vintage Marfim" in bytes(res_linha.body).decode("utf-8")

    # 3. Detalhes do produto
    res_det = detalhe_produto(req, prod.ID, db_session)
    assert res_det.status_code == 200
    body_det = bytes(res_det.body).decode("utf-8")
    assert "Corset Vintage Marfim" in body_det
    assert "laços de cetim" in body_det
    assert "225,00" in body_det

    # 4. Produto inexistente retorna 404
    with pytest.raises(HTTPException) as exc_info:
        detalhe_produto(req, 999999, db_session)
    assert exc_info.value.status_code == 404


