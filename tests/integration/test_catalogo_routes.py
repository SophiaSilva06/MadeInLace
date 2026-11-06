"""Testes de integração para as rotas de Catálogo, Produtos e Filtros (Regra 00 & 08)."""

from decimal import Decimal

import pytest
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.database import Base
from app.main import app
from app.models import Fornecedor, Linha, MetodoPagamento, Produto, StatusVenda, Variacao
from app.routers.catalogo import (
    listar_corsets,
    listar_plus_size,
    listar_produtos,
    listar_promocoes,
    listar_saltos,
    listar_vestidos,
    pesquisar_produtos,
)


@pytest.fixture
def db_session() -> Session:
    """Cria uma sessão isolada com SQLite em memória para os testes de catálogo."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        return session
    finally:
        pass


@pytest.fixture
def seed_dados_catalogo(db_session: Session) -> dict[str, int]:
    """Popula dados com fornecedor, linhas, produtos dos 3 tipos, promoções e plus size."""
    forn = Fornecedor(
        NOME="Atelier Made In Lace",
        CNPJ="12345678000199",
        RAZAO_SOCIAL="Made In Lace Ltda",
        ATIVO=True,
    )
    linha_flo = Linha(NOME="Florestal")
    linha_bal = Linha(NOME="Balletcore")
    metodo = MetodoPagamento(METODO="Pix")
    st = StatusVenda(ESTADO_ANDAMENTO="ENTREGUE", DESCRICAO="Entregue")
    db_session.add_all([forn, linha_flo, linha_bal, metodo, st])
    db_session.flush()

    # 1. Vestido com promoção e tamanhos normais
    p_vestido = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha_flo.ID,
        NOME="Vestido Fada da Floresta",
        DESCRICAO="Vestido longo florestal.",
        TIPO="roupa",
        ATIVO=True,
    )
    db_session.add(p_vestido)
    db_session.flush()

    v_vestido_p = Variacao(
        FK_PRODUTO=p_vestido.ID,
        TAMANHO="P",
        COR="Verde",
        ESTOQUE=10,
        CUSTO=Decimal("100.00"),
        PRECO=Decimal("280.00"),
        PORCENTAGEM_PROMOCAO=Decimal("15.00"),
        ATIVO=True,
    )
    db_session.add(v_vestido_p)

    # 2. Corset com tamanho Plus Size (G1)
    p_corset = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha_flo.ID,
        NOME="Corset Rainha da Floresta",
        DESCRICAO="Corset estruturado com barbatanas.",
        TIPO="corset",
        ATIVO=True,
    )
    db_session.add(p_corset)
    db_session.flush()

    v_corset_g1 = Variacao(
        FK_PRODUTO=p_corset.ID,
        TAMANHO="G1",
        COR="Dourado",
        ESTOQUE=4,
        CUSTO=Decimal("80.00"),
        PRECO=Decimal("185.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    db_session.add(v_corset_g1)

    # 3. Salto (calcado) com tamanhos de sapato
    p_salto = Produto(
        FK_FORNECEDOR=forn.ID,
        FK_LINHA=linha_bal.ID,
        NOME="Salto Pump Balletcore",
        DESCRICAO="Salto de cetim rosa.",
        TIPO="calcado",
        ATIVO=True,
    )
    db_session.add(p_salto)
    db_session.flush()

    v_salto_37 = Variacao(
        FK_PRODUTO=p_salto.ID,
        TAMANHO="37",
        COR="Rosa",
        ESTOQUE=6,
        CUSTO=Decimal("70.00"),
        PRECO=Decimal("155.00"),
        PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        ATIVO=True,
    )
    db_session.add(v_salto_37)

    db_session.commit()

    return {
        "vestido_id": int(p_vestido.ID),
        "corset_id": int(p_corset.ID),
        "salto_id": int(p_salto.ID),
    }


def _criar_request(path: str) -> Request:
    raw_path, _, query_string = path.partition("?")
    scope = {
        "type": "http",
        "method": "GET",
        "path": raw_path,
        "query_string": query_string.encode("latin-1"),
        "headers": [],
        "app": app,
    }
    return Request(scope)


def test_rota_produtos_geral(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida se /produtos responde com título 'Todos Produtos' e exibe os 3 produtos."""
    req = _criar_request("/produtos")
    res = listar_produtos(req, db_session)
    assert isinstance(res, HTMLResponse)
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Todos Produtos" in html
    assert "Vestido Fada da Floresta" in html
    assert "Corset Rainha da Floresta" in html
    assert "Salto Pump Balletcore" in html
    assert "Tamanho Roupa" in html
    assert "Tamanho Sapato" in html
    assert "Categoria" in html
    assert "Preço" in html


def test_rota_vestidos_exclusiva(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida se /vestidos só lista vestidos e oculta filtros de categoria e sapato."""
    req = _criar_request("/vestidos")
    res = listar_vestidos(req, db_session)
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Vestidos" in html
    assert "Vestido Fada da Floresta" in html
    assert "Corset Rainha da Floresta" not in html
    assert "Salto Pump Balletcore" not in html

    # Filtros esperados: apenas Roupa e Preço
    assert "Tamanho Roupa" in html
    assert "Tamanho Sapato" not in html
    assert "filter-section-categoria" not in html
    # Preço máximo do slider é o do vestido mais caro (238), não 460
    assert 'max="238"' in html


def test_rota_saltos_exclusiva(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida se /saltos só lista saltos e oculta filtros de categoria e roupa."""
    req = _criar_request("/saltos")
    res = listar_saltos(req, db_session)
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Saltos" in html
    assert "Salto Pump Balletcore" in html
    assert "Vestido Fada da Floresta" not in html
    assert "Corset Rainha da Floresta" not in html

    # Filtros esperados: apenas Sapato e Preço
    assert "Tamanho Sapato" in html
    assert "Tamanho Roupa" not in html
    assert "filter-section-categoria" not in html
    # Preço máximo do slider é o do salto mais caro (155), não 460
    assert 'max="155"' in html


def test_rota_corsets_exclusiva(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida se /corsets só lista corsets e oculta filtros de categoria e sapato."""
    req = _criar_request("/corsets")
    res = listar_corsets(req, db_session)
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Corsets" in html
    assert "Corset Rainha da Floresta" in html
    assert "Salto Pump Balletcore" not in html

    assert "Tamanho Roupa" in html
    assert "Tamanho Sapato" not in html
    assert "filter-section-categoria" not in html
    # Preço máximo do slider é o do corset mais caro (185), não 460
    assert 'max="185"' in html


def test_rota_promocao_exclusiva(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida se /promocao só lista produtos com desconto percentual."""
    req = _criar_request("/promocao")
    res = listar_promocoes(req, db_session)
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Em Promoção" in html
    # Apenas o vestido tem promoção de 15%
    assert "Vestido Fada da Floresta" in html
    assert "Corset Rainha da Floresta" not in html
    assert "Salto Pump Balletcore" not in html


def test_rota_plus_size_exclusiva(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida se /plus-size só lista produtos com variação G1..G5."""
    req = _criar_request("/plus-size")
    res = listar_plus_size(req, db_session)
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Plus Size" in html
    # Apenas o corset tem tamanho G1
    assert "Corset Rainha da Floresta" in html
    assert "Salto Pump Balletcore" not in html


def test_rota_pesquisa_por_linha(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida busca por linha trazendo tag e produtos da linha correspondente."""
    req = _criar_request("/pesquisa?linha=Florestal")
    res = pesquisar_produtos(req, db_session, linha="Florestal")
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Linha: Florestal" in html
    assert "Vestido Fada da Floresta" in html
    assert "Corset Rainha da Floresta" in html
    assert "Salto Pump Balletcore" not in html


def test_rota_pesquisa_por_produto_nome(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida busca textual por nome de produto."""
    req = _criar_request("/pesquisa?nome=Pump")
    res = pesquisar_produtos(req, db_session, nome="Pump")
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Nome: Pump" in html
    assert "Salto Pump Balletcore" in html
    assert "Vestido Fada da Floresta" not in html


def test_produtos_nao_encontrados(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida mensagem de produtos não encontrados quando a busca não obtém correspondência."""
    req = _criar_request("/pesquisa?nome=InexistenteXYZ")
    res = pesquisar_produtos(req, db_session, nome="InexistenteXYZ")
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    assert "Produtos não encontrados" in html
    # Quando não há produtos, o empty state não deve ter o atributo hidden
    assert '<div class="catalog-empty-state" id="catalog-empty-state" >' in html or (
        'id="catalog-empty-state"' in html and 'id="catalog-empty-state" hidden' not in html
    )


def test_elementos_ocultos_inicialmente(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida que menu hambúrguer e empty-state vêm com hidden por padrão quando há produtos."""
    req = _criar_request("/produtos")
    res = listar_produtos(req, db_session)
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")
    # Menu dropdown global começa fechado com hidden
    assert 'id="global-filter-dropdown" role="listbox" hidden' in html
    # Empty state começa oculto com hidden pois há produtos
    assert 'id="catalog-empty-state" hidden' in html


def test_preco_maximo_dinamico_por_pagina(db_session: Session, seed_dados_catalogo: dict[str, int]) -> None:
    """Valida que o teto do slider reflete o preço do produto mais caro listado em cada página/filtro."""
    # 1. Página de Vestidos: mais caro é o vestido (238)
    req_v = _criar_request("/vestidos")
    res_v = listar_vestidos(req_v, db_session)
    html_v = bytes(res_v.body).decode("utf-8")
    assert 'max="238"' in html_v

    # 2. Página de Saltos: mais caro é o salto (155)
    req_s = _criar_request("/saltos")
    res_s = listar_saltos(req_s, db_session)
    html_s = bytes(res_s.body).decode("utf-8")
    assert 'max="155"' in html_s

    # 3. Página de Corsets: mais caro é o corset (185)
    req_c = _criar_request("/corsets")
    res_c = listar_corsets(req_c, db_session)
    html_c = bytes(res_c.body).decode("utf-8")
    assert 'max="185"' in html_c

    # 4. Pesquisa específica por nome de produto (apenas Salto Pump a 155)
    req_p = _criar_request("/pesquisa?nome=Pump")
    res_p = pesquisar_produtos(req_p, db_session, nome="Pump")
    html_p = bytes(res_p.body).decode("utf-8")
    assert 'max="155"' in html_p


def test_produtos_json_contem_produtos_base_ao_pesquisar(
    db_session: Session, seed_dados_catalogo: dict[str, int]
) -> None:
    """Garante que ao pesquisar por linha ou produto, o JSON embutido na página contenha
    todos os produtos da loja, permitindo que a remoção do filtro pré-adicionado restaure
    a listagem completa no frontend sem perder os demais produtos.
    """
    import json

    req = _criar_request("/produtos?linha=Florestal")
    res = listar_produtos(req, db_session, linha="Florestal")
    assert res.status_code == 200

    html = bytes(res.body).decode("utf-8")

    # SSR exibe apenas produtos da linha Florestal
    assert "Linha: Florestal" in html
    assert "Vestido Fada da Floresta" in html
    assert "Corset Rainha da Floresta" in html

    # Extrai o script de dados serializados
    inicio = html.find('<script id="produtos-dados" type="application/json">')
    assert inicio != -1
    fim = html.find("</script>", inicio)
    assert fim != -1
    json_str = html[inicio + len('<script id="produtos-dados" type="application/json">') : fim].strip()
    dados = json.loads(json_str)

    # O JSON serializado DEVE conter os 3 produtos da loja (incluindo o Salto Pump Balletcore)
    nomes_json = [p["nome"] for p in dados]
    assert "Salto Pump Balletcore" in nomes_json
    assert "Vestido Fada da Floresta" in nomes_json
    assert "Corset Rainha da Floresta" in nomes_json

