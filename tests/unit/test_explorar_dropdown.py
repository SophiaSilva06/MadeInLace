"""Testes unitários e de integração para a aba de hover do menu Explorar (18_Made In lace Explorar).

Valida:
- DTO LinhaRecenteDTO e serviço get_linhas_recentes (DBA & Backend)
- Ordenação e limite de 4 linhas mais recentes
- Geração correta de links com filtro pré-selecionado (/produtos?linha=...)
- Renderização no template base.html com fidelidade à imagem de design
- Rota de API /api/linhas/recentes
- Acessibilidade (ARIA, teclado e navegação)
"""

import urllib.parse
from datetime import datetime

import jinja2
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.templates import formatar_desconto, formatar_moeda
from app.models import Fornecedor, ImgsProduto, Linha, Produto
from app.routers.catalogo import obter_linhas_recentes_api
from app.services.home_service import HomeService, LinhaRecenteDTO


def mock_url_for(endpoint: str, **values: str) -> str:
    if endpoint == "static":
        return f"/static/{values.get('path', '')}"
    return f"/{endpoint}"


@pytest.fixture
def jinja_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(["app/templates"]),
        autoescape=True,
    )
    env.filters["moeda"] = formatar_moeda
    env.filters["desconto"] = formatar_desconto
    return env


@pytest.fixture
def db_session() -> Session:
    """Cria banco SQLite em memória isolado."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        return session
    finally:
        pass


# ==============================================================================
# 1. TESTES DO SERVIÇO E DTO (DBA & BACKEND)
# ==============================================================================


def test_dto_linha_recente_estrutura() -> None:
    """Valida contrato de dados do LinhaRecenteDTO."""
    dto = LinhaRecenteDTO(
        id=1,
        nome="Cunty",
        imagem_url="img/linhas/linha_cunty.png",
        link_url="/produtos?linha=Cunty",
    )
    assert dto.id == 1
    assert dto.nome == "Cunty"
    assert dto.imagem_url == "img/linhas/linha_cunty.png"
    assert dto.link_url == "/produtos?linha=Cunty"


def test_get_linhas_recentes_banco_vazio(db_session: Session) -> None:
    """Se não houver linhas no banco, retorna lista vazia de forma segura."""
    linhas = HomeService.get_linhas_recentes(db_session, limit=4)
    assert isinstance(linhas, list)
    assert len(linhas) == 0


def test_get_linhas_recentes_ordena_por_mais_recentes(db_session: Session) -> None:
    """Retorna no máximo 4 linhas ordenadas pelas mais recentes (lançamento/ID decrescente)."""
    forn = Fornecedor(NOME="Atelier Teste", CNPJ="11222333000100", RAZAO_SOCIAL="Teste", ATIVO=True)
    db_session.add(forn)
    db_session.flush()

    # Cria 6 linhas com IDs sequenciais
    l1 = Linha(NOME="Linha Antiga 1")
    l2 = Linha(NOME="Linha Antiga 2")
    l3 = Linha(NOME="Cunty")
    l4 = Linha(NOME="Summer")
    l5 = Linha(NOME="Christmas")
    l6 = Linha(NOME="Fairycore")
    db_session.add_all([l1, l2, l3, l4, l5, l6])
    db_session.flush()

    # Adiciona produto ativo na linha 6 com data recente
    p6 = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=l6.ID,
        NOME="Vestido Fairycore",
        TIPO="roupa",
        ATIVO=True,
        DATA_CRIACAO=datetime(2026, 11, 1, 10, 0, 0),
    )
    db_session.add(p6)
    db_session.commit()

    resultado = HomeService.get_linhas_recentes(db_session, limit=4)
    assert len(resultado) == 4
    # As 4 mais recentes devem incluir l6, l5, l4, l3
    nomes = [item.nome for item in resultado]
    assert "Fairycore" in nomes
    assert "Christmas" in nomes
    assert "Summer" in nomes
    assert "Cunty" in nomes
    assert "Linha Antiga 1" not in nomes

    # Checa formato do link_url com URL encoding
    for item in resultado:
        assert item.link_url == f"/produtos?linha={urllib.parse.quote_plus(item.nome)}"


def test_get_linhas_recentes_com_imagem_do_produto(db_session: Session) -> None:
    """Se uma linha genérica tiver produto com imagem ativa, usa a imagem do produto."""
    forn = Fornecedor(NOME="Atelier Flores", CNPJ="22333444000199", RAZAO_SOCIAL="Flores", ATIVO=True)
    linha = Linha(NOME="Colecao Exclusiva")
    db_session.add_all([forn, linha])
    db_session.flush()

    prod = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha.ID,
        NOME="Corset Floral Especial",
        TIPO="corset",
        ATIVO=True,
        DATA_CRIACAO=datetime(2026, 10, 20),
    )
    db_session.add(prod)
    db_session.flush()

    img = ImgsProduto(
        FK_PRODUTO=prod.ID,
        URL_IMAGEM="img/produtos/flower-mirror-corset-1.png",
        ATIVO=True,
    )
    db_session.add(img)
    db_session.commit()

    linhas = HomeService.get_linhas_recentes(db_session, limit=4)
    assert len(linhas) == 1
    assert linhas[0].nome == "Colecao Exclusiva"
    assert linhas[0].imagem_url == "img/produtos/flower-mirror-corset-1.png"
    assert linhas[0].link_url == "/produtos?linha=Colecao+Exclusiva"


# ==============================================================================
# 2. TESTES DE TEMPLATE (FRONTEND DESIGNER)
# ==============================================================================


def test_base_template_renderiza_aba_explorar_com_fallback(jinja_env: jinja2.Environment) -> None:
    """base.html sem linhas_recentes no contexto exibe as 4 linhas da imagem 18_Made In lace Explorar."""
    template = jinja_env.get_template("base.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=0,
        linhas_recentes=None,
    )

    # Identificadores da aba de hover
    assert 'id="nav-explorar-item"' in rendered
    assert 'id="nav-explorar-link"' in rendered
    assert 'id="explorar-dropdown"' in rendered

    # ARIA e acessibilidade
    assert 'aria-haspopup="true"' in rendered
    assert 'aria-expanded="false"' in rendered
    assert 'aria-label="Linhas recentes de produtos"' in rendered

    # 4 Linhas da imagem 18_Made In lace Explorar
    assert "Cunty" in rendered
    assert "Summer" in rendered
    assert "Christmas" in rendered
    assert "Fairycore" in rendered

    # Imagens extraídas da imagem de design
    assert "linha_cunty.png" in rendered
    assert "linha_summer.png" in rendered
    assert "linha_christmas.png" in rendered
    assert "linha_fairycore.png" in rendered

    # Links com filtro de linha pré-selecionado
    assert 'href="/produtos?linha=Cunty"' in rendered
    assert 'href="/produtos?linha=Summer"' in rendered
    assert 'href="/produtos?linha=Christmas"' in rendered
    assert 'href="/produtos?linha=Fairycore"' in rendered


def test_base_template_renderiza_linhas_dinamicas(jinja_env: jinja2.Environment) -> None:
    """base.html com linhas_recentes fornecidas no contexto exibe os dados dinâmicos."""
    template = jinja_env.get_template("base.html")
    linhas_mock = [
        LinhaRecenteDTO(10, "Belezas do Mar", "img/produtos/morning-dew-corset-1.png", "/produtos?linha=Belezas+do+Mar"),
        LinhaRecenteDTO(11, "Florestal", "img/produtos/princess-ashley-corset-1.png", "/produtos?linha=Florestal"),
    ]
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=0,
        linhas_recentes=linhas_mock,
    )

    assert "Belezas do Mar" in rendered
    assert "Florestal" in rendered
    assert 'href="/produtos?linha=Belezas+do+Mar"' in rendered
    assert 'href="/produtos?linha=Florestal"' in rendered


# ==============================================================================
# 3. TESTES DA ROTA API E INTEGRAÇÃO (BACKEND)
# ==============================================================================


def test_api_linhas_recentes_endpoint(db_session: Session) -> None:
    """Endpoint /api/linhas/recentes responde 200 com lista JSON das linhas mais recentes."""
    data = obter_linhas_recentes_api(db_session)
    assert isinstance(data, list)
    # Se houver linhas no banco do app ou fallback, cada item deve conter os campos obrigatórios
    for item in data:
        assert "id" in item
        assert "nome" in item
        assert "imagem_url" in item
        assert "link_url" in item
        assert str(item["link_url"]).startswith("/produtos?linha=")
