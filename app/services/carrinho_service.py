from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.templates import formatar_moeda
from app.models.carrinho import Carrinho, ItemCarrinho
from app.models.produto import Produto, Variacao
from app.schemas.carrinho import CarrinhoDTO, ItemCarrinhoDTO

META_FRETE_GRATIS = Decimal("160.00")
DURACAO_RESERVA_MINUTOS = 10
LIMITE_MAXIMO_POR_ITEM = 10


class CarrinhoService:
    """Regras de negócio e operações de persistência do Carrinho de Compras."""

    @staticmethod
    def obter_ou_criar_carrinho_ativo(db: Session, usuario_id: int) -> Carrinho:
        """Localiza o carrinho ATIVO do usuário ou cria um novo com TOTAL=0.00."""
        stmt = (
            select(Carrinho)
            .where(Carrinho.FK_USUARIO == usuario_id, Carrinho.STATUS == "ATIVO")
            .options(
                selectinload(Carrinho.itens)
                .joinedload(ItemCarrinho.variacao)
                .joinedload(Variacao.produto)
                .selectinload(Produto.imagens)
            )
        )
        carrinho = db.scalar(stmt)
        if not carrinho:
            carrinho = Carrinho(
                FK_USUARIO=usuario_id,
                STATUS="ATIVO",
                TOTAL=Decimal("0.00"),
                FRETE_GRATIS=False,
                DATA_CRIACAO=datetime.now(),
            )
            db.add(carrinho)
            db.flush()
        return carrinho

    @staticmethod
    def calcular_preco_unitario(variacao: Variacao) -> Decimal:
        """Calcula o preço final unitário da variação aplicando eventuais promoções."""
        preco = Decimal(str(variacao.PRECO))
        porcentagem = Decimal(str(variacao.PORCENTAGEM_PROMOCAO or "0.00"))
        if porcentagem > Decimal("0.00"):
            desconto = (preco * (porcentagem / Decimal("100.00"))).quantize(Decimal("0.01"))
            return (preco - desconto).quantize(Decimal("0.01"))
        return preco.quantize(Decimal("0.01"))

    @classmethod
    def calcular_estoque_disponivel(
        cls, db: Session, variacao_id: int, ignorar_carrinho_id: int | None = None
    ) -> int:
        """Estoque disponível = Estoque físico - reservas ativas de outros carrinhos."""
        variacao = db.get(Variacao, variacao_id)
        if not variacao or not variacao.ATIVO:
            return 0

        agora = datetime.now()
        stmt = (
            select(func.count())
            .select_from(ItemCarrinho)
            .join(Carrinho, ItemCarrinho.FK_CARRINHO == Carrinho.ID)
            .where(
                ItemCarrinho.FK_VARIACAO == variacao_id,
                Carrinho.STATUS == "ATIVO",
                ItemCarrinho.RESERVADO_ATE > agora,
            )
        )
        if ignorar_carrinho_id is not None:
            stmt = stmt.where(Carrinho.ID != ignorar_carrinho_id)

        reservas_outros = db.scalar(stmt) or 0
        return max(0, int(variacao.ESTOQUE) - int(reservas_outros))

    @classmethod
    def recalcular_carrinho(cls, db: Session, carrinho: Carrinho) -> None:
        """Recalcula preços dos itens a partir do catálogo, atualiza TOTAL e FRETE_GRATIS."""
        total = Decimal("0.00")
        for item in carrinho.itens:
            # Recalcula preço unitário com base no catálogo atual
            if item.variacao:
                preco_atual = cls.calcular_preco_unitario(item.variacao)
                item.PRECO_UNITARIO = preco_atual
            total += Decimal(str(item.PRECO_UNITARIO)) * Decimal(item.QNT)

        carrinho.TOTAL = total.quantize(Decimal("0.01"))
        carrinho.FRETE_GRATIS = bool(carrinho.TOTAL >= META_FRETE_GRATIS)
        db.flush()

    @classmethod
    def adicionar_item(
        cls,
        db: Session,
        usuario_id: int,
        produto_id: int | None = None,
        variacao_id: int | None = None,
        tamanho: str | None = None,
        cor: str | None = None,
        quantidade: int = 1,
    ) -> CarrinhoDTO:
        """Adiciona ou incrementa um item no carrinho ativo do usuário."""
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        # Localiza a variação
        variacao: Variacao | None = None
        if variacao_id:
            variacao = db.get(Variacao, variacao_id)
        elif produto_id and tamanho and cor:
            stmt_v = select(Variacao).where(
                Variacao.FK_PRODUTO == produto_id,
                Variacao.TAMANHO == tamanho,
                Variacao.COR == cor,
                Variacao.ATIVO == True,  # noqa: E712
            )
            variacao = db.scalar(stmt_v)

        if not variacao or not variacao.ATIVO:
            raise ValueError("Variação do produto não encontrada ou indisponível.")

        carrinho = cls.obter_ou_criar_carrinho_ativo(db, usuario_id)

        # Procura item existente
        stmt_item = select(ItemCarrinho).where(
            ItemCarrinho.FK_CARRINHO == carrinho.ID,
            ItemCarrinho.FK_VARIACAO == variacao.ID,
        )
        item = db.scalar(stmt_item)

        nova_quantidade = (item.QNT + quantidade) if item else quantidade
        if nova_quantidade > LIMITE_MAXIMO_POR_ITEM:
            raise ValueError(
                f"Máximo de {LIMITE_MAXIMO_POR_ITEM} unidades por variação em um mesmo carrinho."
            )

        # Valida disponibilidade
        disponivel = cls.calcular_estoque_disponivel(
            db, variacao.ID, ignorar_carrinho_id=carrinho.ID
        )
        if disponivel < nova_quantidade:
            raise ValueError("Estoque insuficiente para a quantidade solicitada.")

        agora = datetime.now()
        expiracao = agora + timedelta(minutes=DURACAO_RESERVA_MINUTOS)
        preco_unitario = cls.calcular_preco_unitario(variacao)

        if item:
            item.QNT = nova_quantidade
            item.PRECO_UNITARIO = preco_unitario
            item.RESERVADO_ATE = expiracao
        else:
            item = ItemCarrinho(
                FK_CARRINHO=carrinho.ID,
                FK_VARIACAO=variacao.ID,
                QNT=nova_quantidade,
                PRECO_UNITARIO=preco_unitario,
                RESERVADO_ATE=expiracao,
            )
            db.add(item)

        db.flush()
        cls.recalcular_carrinho(db, carrinho)
        db.commit()

        return cls.obter_carrinho_dto(db, usuario_id)

    @classmethod
    def atualizar_quantidade(
        cls,
        db: Session,
        usuario_id: int,
        item_id: int,
        nova_quantidade: int,
    ) -> CarrinhoDTO:
        """Altera a quantidade de um item no carrinho (1 a 10)."""
        if nova_quantidade < 1 or nova_quantidade > LIMITE_MAXIMO_POR_ITEM:
            raise ValueError(
                f"A quantidade deve ser entre 1 e {LIMITE_MAXIMO_POR_ITEM} unidades."
            )

        carrinho = cls.obter_ou_criar_carrinho_ativo(db, usuario_id)

        stmt_item = (
            select(ItemCarrinho)
            .join(Carrinho, ItemCarrinho.FK_CARRINHO == Carrinho.ID)
            .where(
                ItemCarrinho.ID == item_id,
                Carrinho.ID == carrinho.ID,
            )
            .options(joinedload(ItemCarrinho.variacao))
        )
        item = db.scalar(stmt_item)
        if not item:
            raise ValueError("Item não encontrado no seu carrinho.")

        if nova_quantidade > item.QNT:
            disponivel = cls.calcular_estoque_disponivel(
                db, item.FK_VARIACAO, ignorar_carrinho_id=carrinho.ID
            )
            if disponivel < nova_quantidade:
                raise ValueError("Estoque insuficiente para aumentar a quantidade.")

        item.QNT = nova_quantidade
        if item.variacao:
            item.PRECO_UNITARIO = cls.calcular_preco_unitario(item.variacao)

        db.flush()
        cls.recalcular_carrinho(db, carrinho)
        db.commit()

        return cls.obter_carrinho_dto(db, usuario_id)

    @classmethod
    def remover_item(
        cls,
        db: Session,
        usuario_id: int,
        item_id: int,
    ) -> CarrinhoDTO:
        """Remove o item e todas as suas unidades do carrinho.

        Operação idempotente: se o item já foi removido (ex: requisições concorrentes
        ou cliques rápidos), não lança exceção e retorna o estado atualizado do carrinho.
        """
        carrinho = cls.obter_ou_criar_carrinho_ativo(db, usuario_id)

        stmt_item = select(ItemCarrinho).where(
            (ItemCarrinho.ID == item_id) | (ItemCarrinho.FK_VARIACAO == item_id),
            ItemCarrinho.FK_CARRINHO == carrinho.ID,
        )
        item = db.scalar(stmt_item)
        if item is not None:
            db.delete(item)
            db.flush()
            cls.recalcular_carrinho(db, carrinho)
            db.commit()

        return cls.obter_carrinho_dto(db, usuario_id)

    @classmethod
    def obter_carrinho_dto(cls, db: Session, usuario_id: int) -> CarrinhoDTO:
        """Gera o DTO completo do carrinho com formatações e timers calculados."""
        carrinho = cls.obter_ou_criar_carrinho_ativo(db, usuario_id)
        cls.recalcular_carrinho(db, carrinho)
        db.commit()

        agora = datetime.now()
        itens_dto: list[ItemCarrinhoDTO] = []
        quantidade_total = 0

        # Ordena por ID decrescente para os mais recentes ficarem no topo
        itens_ordenados = sorted(carrinho.itens, key=lambda x: x.ID, reverse=True)

        for it in itens_ordenados:
            var = it.variacao
            prod = var.produto if var else None
            nome = prod.NOME if prod else "Produto Made In Lace"
            cor = var.COR if var else ""
            tamanho = var.TAMANHO if var else ""

            # Imagem do produto
            imagem_url = "img/site/MadeInLaceLogo.png"
            if prod and prod.imagens:
                imagem_url = prod.imagens[0].URL_IMAGEM

            subtotal_item = (Decimal(str(it.PRECO_UNITARIO)) * Decimal(it.QNT)).quantize(
                Decimal("0.01")
            )
            quantidade_total += it.QNT

            segundos_restantes = max(0.0, (it.RESERVADO_ATE - agora).total_seconds())
            expirado = bool(segundos_restantes <= 0)

            itens_dto.append(
                ItemCarrinhoDTO(
                    id=it.ID,
                    variacao_id=it.FK_VARIACAO,
                    produto_id=prod.ID if prod else 0,
                    nome=nome,
                    cor=cor,
                    tamanho=tamanho,
                    imagem_url=imagem_url,
                    quantidade=it.QNT,
                    preco_unitario=float(it.PRECO_UNITARIO),
                    preco_unitario_formatado=formatar_moeda(it.PRECO_UNITARIO),
                    subtotal=float(subtotal_item),
                    subtotal_formatado=formatar_moeda(subtotal_item),
                    reservado_ate=it.RESERVADO_ATE.isoformat(),
                    segundos_restantes=round(segundos_restantes, 2),
                    expirado=expirado,
                )
            )

        total_dec = Decimal(str(carrinho.TOTAL))
        meta_dec = META_FRETE_GRATIS
        valor_para_frete = max(Decimal("0.00"), meta_dec - total_dec)
        porcentagem_frete = (
            min(Decimal("100.00"), (total_dec / meta_dec * Decimal("100.00")))
            if meta_dec > 0
            else Decimal("100.00")
        )

        return CarrinhoDTO(
            id=carrinho.ID,
            autenticado=True,
            total=float(total_dec),
            total_formatado=formatar_moeda(total_dec),
            subtotal=float(total_dec),
            subtotal_formatado=formatar_moeda(total_dec),
            frete_gratis=bool(carrinho.FRETE_GRATIS),
            quantidade_total=quantidade_total,
            meta_frete_gratis=float(meta_dec),
            valor_para_frete_gratis=float(valor_para_frete),
            valor_para_frete_gratis_formatado=formatar_moeda(valor_para_frete),
            porcentagem_frete_gratis=round(float(porcentagem_frete), 1),
            itens=itens_dto,
        )

    @classmethod
    def obter_carrinho_anonimo_dto(cls) -> dict[str, Any]:
        """Retorna uma estrutura neutra para usuários não autenticados."""
        return {
            "id": 0,
            "autenticado": False,
            "total": 0.0,
            "total_formatado": "R$ 0,00",
            "subtotal": 0.0,
            "subtotal_formatado": "R$ 0,00",
            "frete_gratis": False,
            "quantidade_total": 0,
            "meta_frete_gratis": 160.0,
            "valor_para_frete_gratis": 160.0,
            "valor_para_frete_gratis_formatado": "R$ 160,00",
            "porcentagem_frete_gratis": 0.0,
            "itens": [],
        }
