from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.avaliacao import Avaliacao
from app.models.dominio import Linha
from app.models.produto import Produto, Variacao
from app.models.venda import ItemVenda, Venda


@dataclass(slots=True)
class MidiaAvaliacaoDTO:
    """DTO para foto ou vídeo de avaliação de comprador."""

    url: str
    tipo: str  # 'video' ou 'imagem'


@dataclass(slots=True)
class AvaliacaoItemDTO:
    """DTO tipado para exibição individual de uma avaliação."""

    id: int
    autor_nome: str
    nota: int
    tamanho_comprado: str
    cor_comprada: str
    comentario: str
    data_formatada: str
    midias: list[MidiaAvaliacaoDTO]
    tem_midia: bool


@dataclass(slots=True)
class VariacaoOpcaoDTO:
    """DTO com detalhes de cada variação (tamanho, cor, estoque e disponibilidade)."""

    id: int
    tamanho: str
    cor: str
    estoque: int
    preco: Decimal
    preco_promocional: Decimal | None
    disponivel: bool


@dataclass(slots=True)
class ProdutoCardDTO:
    """DTO tipado para exibição nos cards da listagem, busca e catálogo."""

    id: int
    nome: str
    descricao: str | None
    tipo: str  # 'roupa', 'calcado', 'corset'
    linha_nome: str
    preco: Decimal
    preco_promocional: Decimal | None
    preco_efetivo: Decimal
    porcentagem_promocao: Decimal
    tem_promocao: bool
    imagem_principal: str
    imagens: list[str]
    media_avaliacoes: float | None
    total_avaliacoes: int
    is_best_seller: bool
    tamanhos: list[str]
    data_criacao: datetime | None
    variacoes: list[VariacaoOpcaoDTO]


@dataclass(slots=True)
class ProdutoDetalheDTO:
    """DTO tipado para exibição completa de produto, variações e avaliações."""

    id: int
    nome: str
    descricao: str | None
    tipo: str
    linha_nome: str
    imagem_principal: str
    imagens: list[str]
    preco_base: Decimal
    preco_promocional: Decimal | None
    porcentagem_promocao: Decimal
    tem_promocao: bool
    tamanhos_disponiveis: list[str]
    cores_disponiveis: list[str]
    tamanhos_todos: list[dict[str, str | bool]]
    cores_todas: list[dict[str, str | bool]]
    tamanho_inicial: str | None
    cor_inicial: str | None
    variacoes: list[VariacaoOpcaoDTO]
    estoque_total: int
    media_avaliacoes: float | None
    total_avaliacoes: int
    distribuicao_estrelas: dict[int, int]
    estrelas_visuais: list[str]
    avaliacoes_com_midia: list[AvaliacaoItemDTO]
    avaliacoes_sem_midia: list[AvaliacaoItemDTO]


class ProdutoService:
    """Serviço com regras de negócio e consultas otimizadas para produtos e catálogo."""

    @staticmethod
    def _calcular_estrelas_visuais(media: float | None) -> list[str]:
        """Calcula a lista de 5 estrelas ('full', 'half', 'empty') a partir da média."""
        if media is None or media <= 0:
            return ["empty"] * 5

        estrelas: list[str] = []
        for i in range(1, 6):
            if media >= i:
                estrelas.append("full")
            elif media >= (i - 0.75):
                estrelas.append("half")
            else:
                estrelas.append("empty")
        return estrelas

    @staticmethod
    def get_produto_por_id(session: Session, produto_id: int) -> ProdutoDetalheDTO | None:
        """Busca um produto ativo por ID com suas imagens, variações, linha e avaliações."""
        stmt = (
            select(Produto)
            .where(Produto.ID == produto_id, Produto.ATIVO.is_(True))
            .options(
                selectinload(Produto.imagens),
                selectinload(Produto.variacoes),
                selectinload(Produto.linha),
            )
        )
        produto = session.scalars(stmt).first()
        if not produto:
            return None

        # Variações ativas
        variacoes_ativas = [v for v in produto.variacoes if bool(v.ATIVO)]

        preco_base = Decimal("0.00")
        menor_promocional: Decimal | None = None
        maior_desconto = Decimal("0.00")
        tamanhos_existentes: list[str] = []
        cores_existentes: list[str] = []
        estoque_total = 0
        variacoes_dto: list[VariacaoOpcaoDTO] = []

        # Padrão ordenado de tamanhos se for vestuário/corset
        ordem_tamanhos = ["PP", "P", "M", "G", "GG", "XG"]

        for var in variacoes_ativas:
            estoque_v = int(var.ESTOQUE or 0)
            estoque_total += estoque_v
            tamanho_str = str(var.TAMANHO).strip()
            cor_str = str(var.COR).strip()

            if tamanho_str and tamanho_str not in tamanhos_existentes:
                tamanhos_existentes.append(tamanho_str)
            if cor_str and cor_str not in cores_existentes:
                cores_existentes.append(cor_str)

            preco_v = Decimal(str(var.PRECO))
            if preco_base == Decimal("0.00") or preco_v < preco_base:
                preco_base = preco_v

            desconto_pct = Decimal(str(var.PORCENTAGEM_PROMOCAO or "0.00"))
            preco_promo_item: Decimal | None = None
            if desconto_pct > 0:
                fator = Decimal("1.00") - (desconto_pct / Decimal("100.00"))
                preco_promo_item = (preco_v * fator).quantize(Decimal("0.01"))
                if menor_promocional is None or preco_promo_item < menor_promocional:
                    menor_promocional = preco_promo_item
                if desconto_pct > maior_desconto:
                    maior_desconto = desconto_pct

            variacoes_dto.append(
                VariacaoOpcaoDTO(
                    id=int(var.ID),
                    tamanho=tamanho_str,
                    cor=cor_str,
                    estoque=estoque_v,
                    preco=preco_v,
                    preco_promocional=preco_promo_item,
                    disponivel=estoque_v > 0,
                )
            )

        # Ordena tamanhos conforme padrão
        tamanhos_ordenados = sorted(
            tamanhos_existentes,
            key=lambda t: ordem_tamanhos.index(t) if t in ordem_tamanhos else 99,
        )

        # Monta estrutura com status de disponibilidade por tamanho e cor
        tamanhos_todos: list[dict[str, str | bool]] = []
        for t in tamanhos_ordenados:
            disp = any(v.disponivel for v in variacoes_dto if v.tamanho == t)
            tamanhos_todos.append({"tamanho": t, "disponivel": disp})

        cores_todas: list[dict[str, str | bool]] = []
        for c in cores_existentes:
            disp = any(v.disponivel for v in variacoes_dto if v.cor == c)
            cores_todas.append({"cor": c, "disponivel": disp})

        # Seleções padrão iniciais (primeiro tamanho e cor disponíveis)
        tamanho_inicial = next(
            (t["tamanho"] for t in tamanhos_todos if t["disponivel"]),
            tamanhos_todos[0]["tamanho"] if tamanhos_todos else None,
        )
        cor_inicial = next(
            (c["cor"] for c in cores_todas if c["disponivel"]),
            cores_todas[0]["cor"] if cores_todas else None,
        )

        # Imagens ativas do produto
        imgs_ativas = [img.URL_IMAGEM for img in produto.imagens if bool(img.ATIVO)]
        imagem_principal = imgs_ativas[0] if imgs_ativas else "img/produtos/midday-phantom-dress-1.png"
        if not imgs_ativas:
            imgs_ativas = [imagem_principal]

        # Busca detalhada de todas as avaliações deste produto com mídias e autor
        stmt_avaliacoes = (
            select(Avaliacao)
            .join(ItemVenda, ItemVenda.ID == Avaliacao.FK_ITEM_VENDA)
            .join(Variacao, Variacao.ID == ItemVenda.FK_VARIACAO)
            .where(Variacao.FK_PRODUTO == produto.ID)
            .options(
                selectinload(Avaliacao.imagens),
                selectinload(Avaliacao.item_venda).selectinload(ItemVenda.variacao),
                selectinload(Avaliacao.item_venda).selectinload(ItemVenda.venda).selectinload(Venda.usuario),
            )
            .order_by(Avaliacao.DATA_CRIACAO.desc())
        )
        avaliacoes_db = list(session.scalars(stmt_avaliacoes).all())

        distribuicao_estrelas = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        avaliacoes_com_midia: list[AvaliacaoItemDTO] = []
        avaliacoes_sem_midia: list[AvaliacaoItemDTO] = []
        total_avaliacoes = len(avaliacoes_db)
        media_avaliacoes: float | None = None

        if total_avaliacoes > 0:
            soma_notas = sum(int(a.NOTA) for a in avaliacoes_db)
            media_avaliacoes = round(soma_notas / total_avaliacoes, 1)

            for a in avaliacoes_db:
                nota_int = int(a.NOTA)
                if nota_int in distribuicao_estrelas:
                    distribuicao_estrelas[nota_int] += 1

                autor_nome = "Cliente"
                if a.item_venda and a.item_venda.venda and a.item_venda.venda.usuario:
                    autor_nome = str(a.item_venda.venda.usuario.NOME or "Cliente").strip()

                tamanho_comprado = ""
                cor_comprada = ""
                if a.item_venda and a.item_venda.variacao:
                    tamanho_comprado = str(a.item_venda.variacao.TAMANHO or "").strip()
                    cor_comprada = str(a.item_venda.variacao.COR or "").strip()

                data_str = a.DATA_CRIACAO.strftime("%d/%m/%Y") if a.DATA_CRIACAO else ""

                midias_dto: list[MidiaAvaliacaoDTO] = []
                for img in a.imagens:
                    if bool(img.ATIVO):
                        ext = img.URL_IMAGEM.lower()
                        is_video = ext.endswith((".mp4", ".webm", ".ogg", ".mov")) or "video" in ext
                        midias_dto.append(
                            MidiaAvaliacaoDTO(
                                url=img.URL_IMAGEM,
                                tipo="video" if is_video else "imagem",
                            )
                        )

                dto_item = AvaliacaoItemDTO(
                    id=int(a.ID),
                    autor_nome=autor_nome,
                    nota=nota_int,
                    tamanho_comprado=tamanho_comprado,
                    cor_comprada=cor_comprada,
                    comentario=str(a.COMENTARIO or ""),
                    data_formatada=data_str,
                    midias=midias_dto,
                    tem_midia=len(midias_dto) > 0,
                )

                if dto_item.tem_midia:
                    avaliacoes_com_midia.append(dto_item)
                else:
                    avaliacoes_sem_midia.append(dto_item)

        estrelas_visuais = ProdutoService._calcular_estrelas_visuais(media_avaliacoes)

        return ProdutoDetalheDTO(
            id=int(produto.ID),
            nome=produto.NOME,
            descricao=produto.DESCRICAO,
            tipo=produto.TIPO,
            linha_nome=produto.linha.NOME if produto.linha else "Coleção Geral",
            imagem_principal=imagem_principal,
            imagens=imgs_ativas,
            preco_base=preco_base,
            preco_promocional=menor_promocional,
            porcentagem_promocao=maior_desconto,
            tem_promocao=menor_promocional is not None,
            tamanhos_disponiveis=[t for t in tamanhos_existentes],
            cores_disponiveis=[c for c in cores_existentes],
            tamanhos_todos=tamanhos_todos,
            cores_todas=cores_todas,
            tamanho_inicial=str(tamanho_inicial) if tamanho_inicial else None,
            cor_inicial=str(cor_inicial) if cor_inicial else None,
            variacoes=variacoes_dto,
            estoque_total=estoque_total,
            media_avaliacoes=media_avaliacoes,
            total_avaliacoes=total_avaliacoes,
            distribuicao_estrelas=distribuicao_estrelas,
            estrelas_visuais=estrelas_visuais,
            avaliacoes_com_midia=avaliacoes_com_midia,
            avaliacoes_sem_midia=avaliacoes_sem_midia,
        )

    @staticmethod
    def listar_catalogo(
        session: Session,
        q: str | None = None,
        linha_nome: str | None = None,
        tipo: str | None = None,
        apenas_promocao: bool = False,
        limit: int = 24,
    ) -> Sequence[Produto]:
        """Busca catálogo com filtros de busca textual, linha, tipo e promoção."""
        stmt = (
            select(Produto)
            .where(Produto.ATIVO.is_(True))
            .options(
                selectinload(Produto.imagens),
                selectinload(Produto.variacoes),
                selectinload(Produto.linha),
            )
        )

        if linha_nome:
            stmt = stmt.join(Linha, Linha.ID == Produto.FK_LINHA).where(
                Linha.NOME.ilike(f"%{linha_nome.strip()}%")
            )

        if tipo:
            stmt = stmt.where(Produto.TIPO == tipo.strip().lower())

        if apenas_promocao:
            stmt = stmt.join(Variacao, Variacao.FK_PRODUTO == Produto.ID).where(
                Variacao.ATIVO.is_(True),
                Variacao.PORCENTAGEM_PROMOCAO > 0,
            ).distinct()

        if q:
            termo = f"%{q.strip()}%"
            # Busca por match no nome do produto ou nome da linha
            if not linha_nome:
                stmt = stmt.outerjoin(Linha, Linha.ID == Produto.FK_LINHA)
            stmt = stmt.where(
                (Produto.NOME.ilike(termo)) | (Linha.NOME.ilike(termo))
            )

        stmt = stmt.order_by(Produto.ID.desc()).limit(limit)
        return session.scalars(stmt).all()

    @staticmethod
    def _buscar_avaliacoes_map(
        session: Session, produto_ids: list[int]
    ) -> dict[int, tuple[float, int]]:
        """Busca médias e totais de avaliações em uma única query agregada."""
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

    @staticmethod
    def _buscar_best_sellers_ids(session: Session, limit: int = 12) -> set[int]:
        """Busca os IDs dos produtos com maior volume de vendas nos últimos 30 dias."""
        data_limite = datetime.now() - timedelta(days=30)
        stmt = (
            select(Variacao.FK_PRODUTO)
            .select_from(ItemVenda)
            .join(Venda, Venda.ID == ItemVenda.FK_VENDA)
            .join(Variacao, Variacao.ID == ItemVenda.FK_VARIACAO)
            .where(Venda.DATA >= data_limite)
            .group_by(Variacao.FK_PRODUTO)
            .order_by(func.sum(ItemVenda.QNT).desc())
            .limit(limit)
        )
        return {int(pid) for pid in session.scalars(stmt).all() if pid is not None}

    @staticmethod
    def obter_preco_maximo(session: Session) -> int:
        """Retorna o maior valor de preço arredondado para cima entre os produtos ativos."""
        stmt = (
            select(func.max(Variacao.PRECO))
            .join(Produto, Produto.ID == Variacao.FK_PRODUTO)
            .where(Produto.ATIVO.is_(True), Variacao.ATIVO.is_(True))
        )
        maior = session.scalar(stmt)
        if maior:
            return int(Decimal(str(maior)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        return 500

    @staticmethod
    def obter_catalogo_detalhado(
        session: Session,
        q: str | None = None,
        tipo_busca: str | None = None,
        linha_nome: str | None = None,
        tipo: str | None = None,
        categorias: list[str] | None = None,
        apenas_promocao: bool = False,
        apenas_plus_size: bool = False,
        tamanhos_roupa: list[str] | None = None,
        tamanhos_sapato: list[str] | None = None,
        preco_min: Decimal | None = None,
        preco_max: Decimal | None = None,
        ordenacao: str | None = None,
    ) -> list[ProdutoCardDTO]:
        """Consulta e formata o catálogo completo de produtos com suporte aos filtros."""
        stmt = (
            select(Produto)
            .where(Produto.ATIVO.is_(True))
            .options(
                selectinload(Produto.imagens),
                selectinload(Produto.variacoes),
                selectinload(Produto.linha),
            )
        )

        # Filtro de tipo fixo (ex: /vestidos -> tipo='roupa', /corsets -> tipo='corset', /saltos -> tipo='calcado')
        if tipo:
            stmt = stmt.where(Produto.TIPO == tipo.strip().lower())

        # Filtro de linha explícito
        if linha_nome:
            stmt = stmt.join(Linha, Linha.ID == Produto.FK_LINHA).where(
                Linha.NOME.ilike(f"%{linha_nome.strip()}%")
            )

        # Busca textual
        if q and q.strip():
            termo = f"%{q.strip()}%"
            modo = (tipo_busca or "tudo").strip().lower()
            if modo == "linhas":
                if not linha_nome:
                    stmt = stmt.join(Linha, Linha.ID == Produto.FK_LINHA)
                stmt = stmt.where(Linha.NOME.ilike(termo))
            elif modo == "produtos":
                stmt = stmt.where(Produto.NOME.ilike(termo))
            else:
                if not linha_nome:
                    stmt = stmt.outerjoin(Linha, Linha.ID == Produto.FK_LINHA)
                stmt = stmt.where((Produto.NOME.ilike(termo)) | (Linha.NOME.ilike(termo)))

        produtos_db = list(session.scalars(stmt).all())
        if not produtos_db:
            return []

        # IDs para busca em lote de notas e best sellers
        prod_ids = [int(p.ID) for p in produtos_db]
        ratings_map = ProdutoService._buscar_avaliacoes_map(session, prod_ids)
        best_sellers_ids = ProdutoService._buscar_best_sellers_ids(session)

        # Tamanhos Plus Size definidos
        plus_size_sizes = {"G1", "G2", "G3", "G4", "G5"}

        resultado: list[ProdutoCardDTO] = []

        for p in produtos_db:
            vars_ativas = [v for v in p.variacoes if bool(v.ATIVO)]
            if not vars_ativas:
                continue

            # Menor preço base e cálculo de promoção
            preco_base = min(Decimal(str(v.PRECO)) for v in vars_ativas)
            menor_promo: Decimal | None = None
            maior_desconto = Decimal("0.00")

            vars_promo = [v for v in vars_ativas if Decimal(str(v.PORCENTAGEM_PROMOCAO or "0.00")) > 0]
            for vp in vars_promo:
                desc = Decimal(str(vp.PORCENTAGEM_PROMOCAO))
                fator = Decimal("1.00") - (desc / Decimal("100.00"))
                calc = (Decimal(str(vp.PRECO)) * fator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if menor_promo is None or calc < menor_promo:
                    menor_promo = calc
                if desc > maior_desconto:
                    maior_desconto = desc

            tem_promo = menor_promo is not None
            preco_efetivo = menor_promo if tem_promo and menor_promo is not None else preco_base

            # Tamanhos disponíveis
            tamanhos_p = [str(v.TAMANHO).strip() for v in vars_ativas if v.TAMANHO]
            tamanhos_unicos = list(dict.fromkeys(tamanhos_p))

            # Imagens
            imgs_ativas = [img.URL_IMAGEM for img in p.imagens if bool(img.ATIVO)]
            img_principal = imgs_ativas[0] if imgs_ativas else "img/produtos/midday-phantom-dress-1.png"
            if not imgs_ativas:
                imgs_ativas = [img_principal]

            media_nota, total_avals = ratings_map.get(int(p.ID), (None, 0))
            is_bs = int(p.ID) in best_sellers_ids

            variacoes_dtos = [
                VariacaoOpcaoDTO(
                    id=int(v.ID),
                    tamanho=str(v.TAMANHO).strip(),
                    cor=str(v.COR).strip(),
                    estoque=int(v.ESTOQUE or 0),
                    preco=Decimal(str(v.PRECO)),
                    preco_promocional=(
                        (
                            Decimal(str(v.PRECO))
                            * (Decimal("1.00") - (Decimal(str(v.PORCENTAGEM_PROMOCAO)) / Decimal("100.00")))
                        ).quantize(Decimal("0.01"))
                        if Decimal(str(v.PORCENTAGEM_PROMOCAO or "0.00")) > 0
                        else None
                    ),
                    disponivel=int(v.ESTOQUE or 0) > 0,
                )
                for v in vars_ativas
            ]

            card = ProdutoCardDTO(
                id=int(p.ID),
                nome=p.NOME,
                descricao=p.DESCRICAO,
                tipo=p.TIPO,
                linha_nome=p.linha.NOME if p.linha else "Coleção Geral",
                preco=preco_base,
                preco_promocional=menor_promo,
                preco_efetivo=preco_efetivo,
                porcentagem_promocao=maior_desconto,
                tem_promocao=tem_promo,
                imagem_principal=img_principal,
                imagens=imgs_ativas,
                media_avaliacoes=media_nota,
                total_avaliacoes=total_avals,
                is_best_seller=is_bs,
                tamanhos=tamanhos_unicos,
                data_criacao=p.DATA_CRIACAO,
                variacoes=variacoes_dtos,
            )

            # Filtro apenas_promocao
            if apenas_promocao and not card.tem_promocao:
                continue

            # Filtro plus_size
            if apenas_plus_size and not any(t in plus_size_sizes for t in card.tamanhos):
                continue

            # Filtro categorias
            if categorias:
                cat_lower = [c.lower() for c in categorias]
                tipo_match = (
                    card.tipo.lower() in cat_lower
                    or ("vestidos" in cat_lower and card.tipo.lower() == "roupa")
                    or ("sapatos" in cat_lower and card.tipo.lower() == "calcado")
                    or ("corsets" in cat_lower and card.tipo.lower() == "corset")
                )
                if not tipo_match:
                    continue

            # Filtro tamanhos_roupa
            if tamanhos_roupa:
                if not any(t in tamanhos_roupa for t in card.tamanhos):
                    continue

            # Filtro tamanhos_sapato
            if tamanhos_sapato:
                if not any(t in tamanhos_sapato for t in card.tamanhos):
                    continue

            # Filtro preco_min e preco_max
            if preco_min is not None and card.preco_efetivo < preco_min:
                continue
            if preco_max is not None and card.preco_efetivo > preco_max:
                continue

            resultado.append(card)

        # Ordenações
        ord_key = (ordenacao or "best_sellers").strip().lower()
        if ord_key == "preco_asc":
            resultado.sort(key=lambda p: p.preco_efetivo)
        elif ord_key == "preco_desc":
            resultado.sort(key=lambda p: p.preco_efetivo, reverse=True)
        elif ord_key == "data_asc":
            resultado.sort(key=lambda p: p.data_criacao or datetime.min)
        elif ord_key == "data_desc":
            resultado.sort(key=lambda p: p.data_criacao or datetime.min, reverse=True)
        elif ord_key == "alpha_asc":
            resultado.sort(key=lambda p: p.nome.lower())
        elif ord_key == "alpha_desc":
            resultado.sort(key=lambda p: p.nome.lower(), reverse=True)
        elif ord_key == "promocao":
            resultado.sort(key=lambda p: (not p.tem_promocao, -p.porcentagem_promocao, -p.id))
        else:  # 'best_sellers' por padrão
            resultado.sort(key=lambda p: (not p.is_best_seller, -p.id))

        return resultado
