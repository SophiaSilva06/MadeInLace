import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.sql.expression import FunctionElement

from app.models import Avaliacao, ItemVenda, Linha, Produto, Variacao, Venda


class SqlRandom(FunctionElement):
    """Expressão SQL agnóstica para ordenação randômica cross-dialect (SQLite e MySQL)."""

    name = "sql_random"
    inherit_cache = True


@compiles(SqlRandom, "sqlite")
def _compile_sql_random_sqlite(element: SqlRandom, compiler: object, **kw: object) -> str:
    return "RANDOM()"


@compiles(SqlRandom, "mysql")
def _compile_sql_random_mysql(element: SqlRandom, compiler: object, **kw: object) -> str:
    return "RAND()"


@compiles(SqlRandom)
def _compile_sql_random_default(element: SqlRandom, compiler: object, **kw: object) -> str:
    return "RAND()"


@dataclass(frozen=True, slots=True)
class ProdutoCardDTO:
    """DTO tipado para exibição de cards de produto na interface."""

    id: int
    nome: str
    descricao: str | None
    tipo: str
    linha_nome: str
    preco: Decimal
    preco_promocional: Decimal | None
    porcentagem_promocao: Decimal
    tem_promocao: bool
    imagem_principal: str | None
    media_avaliacoes: float | None
    total_avaliacoes: int
    is_best_seller: bool = False
    total_vendido: int = 0


@dataclass(frozen=True, slots=True)
class LinhaRecenteDTO:
    """DTO tipado para exibição das linhas recentes na aba de hover do menu Explorar."""

    id: int
    nome: str
    imagem_url: str
    link_url: str


@dataclass(frozen=True, slots=True)
class LinhaHomeDTO:
    """DTO tipado para exibição de linhas/coleções na Home page."""

    id: int
    nome: str
    total_produtos: int
    imagem_destaque: str | None
    produtos: list[ProdutoCardDTO]


@dataclass(frozen=True, slots=True)
class HomeDataDTO:
    """DTO consolidado contendo todas as coleções de dados da Home page."""

    linhas: list[LinhaHomeDTO]
    produtos_promocao: list[ProdutoCardDTO]
    produtos_best_sellers: list[ProdutoCardDTO]
    linhas_recentes: list[LinhaRecenteDTO] = field(default_factory=list)


def _obter_imagem_principal(produto: Produto) -> str | None:
    """Retorna a URL relativa da primeira imagem ativa do produto, ordenada por ID."""
    imagens_ativas = [img for img in produto.imagens if img.ATIVO]
    if not imagens_ativas:
        return None
    imagens_ativas.sort(key=lambda img: img.ID)
    return imagens_ativas[0].URL_IMAGEM


def _calcular_precos(variacoes: Sequence[Variacao]) -> tuple[Decimal, Decimal | None, Decimal, bool]:
    """Calcula os preços de exibição para o card do produto a partir de suas variações ativas.

    Retorna:
        (preco_referencia, menor_preco_promocional, porcentagem_promocao, tem_promocao)
    """
    variacoes_ativas = [v for v in variacoes if v.ATIVO]
    if not variacoes_ativas:
        return Decimal("0.00"), None, Decimal("0.00"), False

    # Variações com promoção positiva
    variacoes_promo = [v for v in variacoes_ativas if v.PORCENTAGEM_PROMOCAO > 0]

    if variacoes_promo:
        # Encontra a variação que resulta no menor preço promocional absoluto
        melhor_v = None
        menor_preco_promo = None

        for v in variacoes_promo:
            fator = (Decimal(100) - v.PORCENTAGEM_PROMOCAO) / Decimal(100)
            preco_calculado = (v.PRECO * fator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if menor_preco_promo is None or preco_calculado < menor_preco_promo:
                menor_preco_promo = preco_calculado
                melhor_v = v

        if melhor_v and menor_preco_promo is not None:
            return melhor_v.PRECO, menor_preco_promo, melhor_v.PORCENTAGEM_PROMOCAO, True

    # Sem promoção: menor preço padrão entre as variações ativas
    min_v = min(variacoes_ativas, key=lambda v: v.PRECO)
    return min_v.PRECO, None, Decimal("0.00"), False


def _buscar_avaliacoes_map(session: Session, produto_ids: list[int]) -> dict[int, tuple[float, int]]:
    """Busca em UMA única query agregada as médias e contagens de avaliações para uma lista de produtos.

    Evita consultas N+1 ao agrupar diretamente por VARIACAO.FK_PRODUTO.
    """
    if not produto_ids:
        return {}

    stmt = (
        select(
            Variacao.FK_PRODUTO,
            func.avg(Avaliacao.NOTA).label("media_nota"),
            func.count(Avaliacao.ID).label("total_avaliacoes"),
        )
        .select_from(Avaliacao)
        .join(ItemVenda, ItemVenda.ID == Avaliacao.FK_ITEM_VENDA)
        .join(Variacao, Variacao.ID == ItemVenda.FK_VARIACAO)
        .where(Variacao.FK_PRODUTO.in_(produto_ids))
        .group_by(Variacao.FK_PRODUTO)
    )

    resultados = session.execute(stmt).fetchall()
    return {
        int(row[0]): (round(float(row[1]), 1), int(row[2]))
        for row in resultados
        if row[0] is not None
    }


def _montar_produto_dto(
    produto: Produto,
    ratings_map: dict[int, tuple[float, int]],
    is_best_seller: bool = False,
    total_vendido: int = 0,
) -> ProdutoCardDTO:
    """Converte a entidade ORM Produto em um ProdutoCardDTO com relacionamentos pré-carregados."""
    preco_ref, preco_promo, perc_promo, tem_promo = _calcular_precos(produto.variacoes)
    img_url = _obter_imagem_principal(produto)
    linha_nome = produto.linha.NOME if produto.linha else "Geral"

    media_nota, total_avals = ratings_map.get(produto.ID, (None, 0))

    return ProdutoCardDTO(
        id=produto.ID,
        nome=produto.NOME,
        descricao=produto.DESCRICAO,
        tipo=produto.TIPO,
        linha_nome=linha_nome,
        preco=preco_ref,
        preco_promocional=preco_promo,
        porcentagem_promocao=perc_promo,
        tem_promocao=tem_promo,
        imagem_principal=img_url,
        media_avaliacoes=media_nota,
        total_avaliacoes=total_avals,
        is_best_seller=is_best_seller,
        total_vendido=total_vendido,
    )


class HomeService:
    """Camada de serviço responsável por todas as consultas da página inicial (Home)."""

    @classmethod
    def get_linhas_destaque(cls, session: Session, limit: int = 4) -> list[LinhaHomeDTO]:
        """Busca até `limit` linhas sortidas com produtos e imagens carregados via selectinload.

        Trata de forma defensiva casos de linhas sem produtos ou produtos inativos.
        """
        stmt = (
            select(Linha)
            .options(
                selectinload(Linha.produtos).selectinload(Produto.imagens),
                selectinload(Linha.produtos).selectinload(Produto.variacoes),
            )
            .order_by(SqlRandom())
            .limit(limit)
        )
        linhas = session.scalars(stmt).all()

        # Coleta todos os IDs de produtos ativos das linhas para carregar notas em lote
        todos_prod_ids: list[int] = []
        for linha in linhas:
            for p in linha.produtos:
                if p.ATIVO:
                    todos_prod_ids.append(p.ID)

        ratings_map = _buscar_avaliacoes_map(session, todos_prod_ids)

        resultado: list[LinhaHomeDTO] = []
        for linha in linhas:
            prods_ativos = [p for p in linha.produtos if p.ATIVO]

            prods_dtos = [
                _montar_produto_dto(p, ratings_map)
                for p in prods_ativos
            ]

            # Imagem de destaque da linha: primeira imagem do primeiro produto ativo, se houver
            img_destaque: str | None = None
            for p_dto in prods_dtos:
                if p_dto.imagem_principal:
                    img_destaque = p_dto.imagem_principal
                    break

            resultado.append(
                LinhaHomeDTO(
                    id=linha.ID,
                    nome=linha.NOME,
                    total_produtos=len(prods_dtos),
                    imagem_destaque=img_destaque,
                    produtos=prods_dtos,
                )
            )

        return resultado

    @classmethod
    def get_linhas_recentes(cls, session: Session, limit: int = 4) -> list[LinhaRecenteDTO]:
        """Busca até `limit` linhas mais recentes com imagens e links de filtro pré-selecionado.

        Segue a regra de negócio da Seção 7.1 da documentação MadeInLace e
        o design visual de 18_Made In lace Explorar.png.
        """
        # Mapeamento para imagens dedicadas das linhas clássicas de design
        imagens_design: dict[str, str] = {
            "cunty": "img/linhas/linha_cunty.png",
            "summer": "img/linhas/linha_summer.png",
            "christmas": "img/linhas/linha_christmas.png",
            "fairycore": "img/linhas/linha_fairycore.png",
        }

        stmt = (
            select(Linha)
            .outerjoin(Produto, (Produto.FK_LINHA == Linha.ID) & (Produto.ATIVO.is_(True)))
            .group_by(Linha.ID)
            .order_by(
                func.coalesce(func.max(Produto.DATA_CRIACAO), datetime(1970, 1, 1)).desc(),
                Linha.ID.desc(),
            )
            .limit(limit)
            .options(
                selectinload(Linha.produtos).selectinload(Produto.imagens),
            )
        )
        linhas = session.scalars(stmt).all()
        if not linhas:
            return []

        resultado: list[LinhaRecenteDTO] = []
        for linha_item in linhas:
            nome_norm = (linha_item.NOME or "").strip().lower()
            img_url = imagens_design.get(nome_norm)

            if not img_url:
                # Procura imagem ativa nos produtos associados à linha
                for p in linha_item.produtos:
                    if p.ATIVO and p.imagens:
                        imgs_ativas = [img for img in p.imagens if img.ATIVO]
                        if imgs_ativas:
                            imgs_ativas.sort(key=lambda x: x.ID)
                            img_url = imgs_ativas[0].URL_IMAGEM
                            break

            # Fallback defensivo de imagem caso a linha não possua produto nem imagem dedicada
            if not img_url:
                img_url = "img/linhas/linha_cunty.png"

            link = f"/produtos?linha={urllib.parse.quote_plus(linha_item.NOME)}"
            resultado.append(
                LinhaRecenteDTO(
                    id=linha_item.ID,
                    nome=linha_item.NOME,
                    imagem_url=img_url,
                    link_url=link,
                )
            )

        return resultado

    @classmethod
    def get_produtos_promocao(cls, session: Session, limit: int = 8) -> list[ProdutoCardDTO]:
        """Busca produtos ativos com pelo menos uma variação ativa com desconto percentual > 0."""
        stmt = (
            select(Produto)
            .join(Variacao, Variacao.FK_PRODUTO == Produto.ID)
            .where(
                Produto.ATIVO.is_(True),
                Variacao.ATIVO.is_(True),
                Variacao.PORCENTAGEM_PROMOCAO > 0,
            )
            .distinct()
            .options(
                selectinload(Produto.imagens),
                selectinload(Produto.variacoes),
                selectinload(Produto.linha),
            )
            .limit(limit)
        )
        produtos = session.scalars(stmt).all()
        if not produtos:
            return []

        ratings_map = _buscar_avaliacoes_map(session, [p.ID for p in produtos])
        return [
            _montar_produto_dto(p, ratings_map)
            for p in produtos
        ]

    @classmethod
    def get_produtos_best_sellers(
        cls, session: Session, limit: int = 8, dias: int = 30
    ) -> list[ProdutoCardDTO]:
        """Busca os produtos Best Sellers baseados em vendas dos últimos `dias`.

        Se não houver vendas suficientes (banco de testes ou inicial), aplica fallback
        automático para os produtos ativos mais recentes.
        """
        data_limite = datetime.now() - timedelta(days=dias)

        # Consulta quantidade vendida agrupada por produto nos últimos dias
        stmt_sales = (
            select(Variacao.FK_PRODUTO, func.sum(ItemVenda.QNT).label("total_vendido"))
            .select_from(ItemVenda)
            .join(Venda, Venda.ID == ItemVenda.FK_VENDA)
            .join(Variacao, Variacao.ID == ItemVenda.FK_VARIACAO)
            .join(Produto, Produto.ID == Variacao.FK_PRODUTO)
            .where(Venda.DATA >= data_limite, Produto.ATIVO.is_(True))
            .group_by(Variacao.FK_PRODUTO)
            .order_by(func.sum(ItemVenda.QNT).desc())
            .limit(limit)
        )
        sales_rows = session.execute(stmt_sales).fetchall()

        product_ids_sales: list[int] = [int(r[0]) for r in sales_rows if r[0] is not None]
        sales_count_map: dict[int, int] = {
            int(r[0]): int(r[1]) for r in sales_rows if r[0] is not None
        }

        produtos_selecionados: list[Produto] = []

        if product_ids_sales:
            # Carrega os produtos vendidos com todas as relações eager
            stmt_prods = (
                select(Produto)
                .where(Produto.ID.in_(product_ids_sales), Produto.ATIVO.is_(True))
                .options(
                    selectinload(Produto.imagens),
                    selectinload(Produto.variacoes),
                    selectinload(Produto.linha),
                )
            )
            prods = session.scalars(stmt_prods).all()
            prods_by_id = {p.ID: p for p in prods}
            # Preserva a ordem original do ranking de vendas
            produtos_selecionados = [
                prods_by_id[pid] for pid in product_ids_sales if pid in prods_by_id
            ]

        # Fallback se houver menos produtos vendidos do que o limite solicitado
        faltam = limit - len(produtos_selecionados)
        if faltam > 0:
            stmt_fallback = (
                select(Produto)
                .where(Produto.ATIVO.is_(True))
            )
            if product_ids_sales:
                stmt_fallback = stmt_fallback.where(Produto.ID.not_in(product_ids_sales))

            stmt_fallback = (
                stmt_fallback.options(
                    selectinload(Produto.imagens),
                    selectinload(Produto.variacoes),
                    selectinload(Produto.linha),
                )
                .order_by(Produto.ID.asc())
                .limit(faltam)
            )
            fallback_prods = session.scalars(stmt_fallback).all()
            produtos_selecionados.extend(fallback_prods)

        if not produtos_selecionados:
            return []

        ratings_map = _buscar_avaliacoes_map(session, [p.ID for p in produtos_selecionados])

        return [
            _montar_produto_dto(
                p,
                ratings_map,
                is_best_seller=True,
                total_vendido=sales_count_map.get(p.ID, 0),
            )
            for p in produtos_selecionados
        ]

    @classmethod
    def get_home_data(cls, session: Session) -> HomeDataDTO:
        """Coleta e orquestra todos os conjuntos de dados necessários para a Home page."""
        linhas = cls.get_linhas_destaque(session, limit=4)
        promocoes = cls.get_produtos_promocao(session, limit=8)
        best_sellers = cls.get_produtos_best_sellers(session, limit=8, dias=30)
        linhas_recentes = cls.get_linhas_recentes(session, limit=4)

        return HomeDataDTO(
            linhas=linhas,
            produtos_promocao=promocoes,
            produtos_best_sellers=best_sellers,
            linhas_recentes=linhas_recentes,
        )
