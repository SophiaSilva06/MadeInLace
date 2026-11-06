from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import (
    Base,
    bool_tinyint,
    int_unsigned,
    money_decimal,
    smallint_unsigned,
)

if TYPE_CHECKING:
    from app.models.produto import Variacao
    from app.models.usuario import Usuario
    from app.models.venda import Venda


class Carrinho(Base):
    """Modelo ORM para a tabela CARRINHO."""

    __tablename__ = "CARRINHO"
    __table_args__ = (
        UniqueConstraint("ID", "FK_USUARIO", name="UQ_CARRINHO_ID_USUARIO"),
        UniqueConstraint("FK_USUARIO_ATIVO", name="UQ_CARRINHO_UM_ATIVO_POR_USUARIO"),
        Index("IDX_CARRINHO_USUARIO", "FK_USUARIO"),
        CheckConstraint("TOTAL >= 0", name="CK_CARRINHO_TOTAL"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_USUARIO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "USUARIOS.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_CARRINHO_USUARIO",
        ),
        nullable=False,
    )
    STATUS: Mapped[str] = mapped_column(
        Enum("ATIVO", "CONVERTIDO", "ABANDONADO", name="carrinho_status_enum"),
        nullable=False,
        server_default=text("'ATIVO'"),
    )
    TOTAL: Mapped[Decimal] = mapped_column(
        money_decimal, nullable=False, server_default=text("0.00")
    )
    FRETE_GRATIS: Mapped[bool] = mapped_column(
        bool_tinyint, nullable=False, server_default=text("0")
    )
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    FK_USUARIO_ATIVO: Mapped[int | None] = mapped_column(
        int_unsigned,
        Computed("IF(STATUS = 'ATIVO', FK_USUARIO, NULL)", persisted=False),
        nullable=True,
    )

    # Synonyms
    id = synonym("ID")
    fk_usuario = synonym("FK_USUARIO")
    status = synonym("STATUS")
    total = synonym("TOTAL")
    frete_gratis = synonym("FRETE_GRATIS")
    data_criacao = synonym("DATA_CRIACAO")
    fk_usuario_ativo = synonym("FK_USUARIO_ATIVO")

    # Relacionamentos
    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="carrinhos")
    itens: Mapped[list[ItemCarrinho]] = relationship(
        "ItemCarrinho", back_populates="carrinho", cascade="all, delete-orphan"
    )
    venda: Mapped[Venda | None] = relationship(
        "Venda",
        back_populates="carrinho",
        uselist=False,
        foreign_keys="[Venda.FK_CARRINHO, Venda.FK_USUARIO]",
        overlaps="carrinho,endereco_usuario,usuario,venda,vendas",
    )


class ItemCarrinho(Base):
    """Modelo ORM para a tabela ITEM_CARRINHO."""

    __tablename__ = "ITEM_CARRINHO"
    __table_args__ = (
        UniqueConstraint("FK_CARRINHO", "FK_VARIACAO", name="UQ_ITEM_CARRINHO_CARRINHO_VARIACAO"),
        Index("IDX_ITEM_CARRINHO_VARIACAO", "FK_VARIACAO"),
        Index("IDX_ITEM_CARRINHO_RESERVADO_ATE", "RESERVADO_ATE"),
        CheckConstraint("QNT > 0", name="CK_ITEM_CARRINHO_QNT"),
        CheckConstraint("PRECO_UNITARIO >= 0", name="CK_ITEM_CARRINHO_PRECO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_CARRINHO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "CARRINHO.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_ITEM_CARRINHO_CARRINHO",
        ),
        nullable=False,
    )
    FK_VARIACAO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "VARIACAO.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_ITEM_CARRINHO_VARIACAO",
        ),
        nullable=False,
    )
    QNT: Mapped[int] = mapped_column(smallint_unsigned, nullable=False, server_default=text("1"))
    PRECO_UNITARIO: Mapped[Decimal] = mapped_column(money_decimal, nullable=False)
    RESERVADO_ATE: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Synonyms
    id = synonym("ID")
    fk_carrinho = synonym("FK_CARRINHO")
    fk_variacao = synonym("FK_VARIACAO")
    qnt = synonym("QNT")
    preco_unitario = synonym("PRECO_UNITARIO")
    reservado_ate = synonym("RESERVADO_ATE")

    # Relacionamentos
    carrinho: Mapped[Carrinho] = relationship("Carrinho", back_populates="itens")
    variacao: Mapped[Variacao] = relationship("Variacao", back_populates="itens_carrinho")
