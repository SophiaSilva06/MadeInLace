from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
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
    tinyint_unsigned,
)

if TYPE_CHECKING:
    from app.models.avaliacao import Avaliacao
    from app.models.carrinho import Carrinho
    from app.models.dominio import MetodoPagamento, StatusVenda
    from app.models.pos_venda import Reembolso, Troca
    from app.models.produto import Variacao
    from app.models.usuario import EnderecoUsuario, Usuario


class Venda(Base):
    """Modelo ORM para a tabela VENDA."""

    __tablename__ = "VENDA"
    __table_args__ = (
        UniqueConstraint("FK_CARRINHO", "FK_USUARIO", name="UQ_VENDA_CARRINHO_USUARIO"),
        Index("IDX_VENDA_ENDERECO_USUARIO", "FK_ENDERECO_USUARIO", "FK_USUARIO"),
        Index("IDX_VENDA_USUARIO_DATA", "FK_USUARIO", "DATA"),
        Index("IDX_VENDA_METODO_PAGAMENTO", "FK_METODO_PAGAMENTO"),
        Index("IDX_VENDA_STATUS", "FK_STATUS"),
        ForeignKeyConstraint(
            ["FK_CARRINHO", "FK_USUARIO"],
            ["CARRINHO.ID", "CARRINHO.FK_USUARIO"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_VENDA_CARRINHO_USUARIO",
        ),
        ForeignKeyConstraint(
            ["FK_ENDERECO_USUARIO", "FK_USUARIO"],
            ["ENDERECO_USUARIO.ID", "ENDERECO_USUARIO.FK_USUARIO"],
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_VENDA_ENDERECO_USUARIO",
        ),
        CheckConstraint("SUBTOTAL >= 0 AND FRETE >= 0", name="CK_VENDA_VALORES"),
        CheckConstraint(
            "TOTAL = ROUND(SUBTOTAL * IF(DESCONTO = 1, 0.90, 1.00), 2) + FRETE",
            name="CK_VENDA_TOTAL",
        ),
        CheckConstraint("FRETE_GRATIS = 0 OR FRETE = 0", name="CK_VENDA_FRETE_GRATIS"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_CARRINHO: Mapped[int] = mapped_column(int_unsigned, nullable=False)
    FK_USUARIO: Mapped[int] = mapped_column(int_unsigned, nullable=False)
    FK_ENDERECO_USUARIO: Mapped[int] = mapped_column(int_unsigned, nullable=False)
    FK_METODO_PAGAMENTO: Mapped[int] = mapped_column(
        tinyint_unsigned,
        ForeignKey(
            "METODO_PAGAMENTO.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_VENDA_METODO_PAGAMENTO",
        ),
        nullable=False,
    )
    FK_STATUS: Mapped[int] = mapped_column(
        tinyint_unsigned,
        ForeignKey(
            "STATUS_VENDA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_VENDA_STATUS",
        ),
        nullable=False,
    )
    SUBTOTAL: Mapped[Decimal] = mapped_column(money_decimal, nullable=False)
    FRETE: Mapped[Decimal] = mapped_column(
        money_decimal, nullable=False, server_default=text("0.00")
    )
    DESCONTO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("0"))
    TOTAL: Mapped[Decimal] = mapped_column(money_decimal, nullable=False)
    FRETE_GRATIS: Mapped[bool] = mapped_column(
        bool_tinyint, nullable=False, server_default=text("0")
    )
    DATA: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Synonyms
    id = synonym("ID")
    fk_carrinho = synonym("FK_CARRINHO")
    fk_usuario = synonym("FK_USUARIO")
    fk_endereco_usuario = synonym("FK_ENDERECO_USUARIO")
    fk_metodo_pagamento = synonym("FK_METODO_PAGAMENTO")
    fk_status = synonym("FK_STATUS")
    subtotal = synonym("SUBTOTAL")
    frete = synonym("FRETE")
    desconto = synonym("DESCONTO")
    total = synonym("TOTAL")
    frete_gratis = synonym("FRETE_GRATIS")
    data = synonym("DATA")

    # Relacionamentos
    carrinho: Mapped[Carrinho] = relationship(
        "Carrinho",
        back_populates="venda",
        foreign_keys="[Venda.FK_CARRINHO, Venda.FK_USUARIO]",
        overlaps="carrinho,endereco_usuario,usuario,venda,vendas",
    )
    usuario: Mapped[Usuario] = relationship(
        "Usuario",
        back_populates="vendas",
        primaryjoin="foreign(Venda.FK_USUARIO) == Usuario.ID",
        overlaps="carrinho,endereco_usuario,usuario,venda,vendas",
    )
    endereco_usuario: Mapped[EnderecoUsuario] = relationship(
        "EnderecoUsuario",
        back_populates="vendas",
        foreign_keys="[Venda.FK_ENDERECO_USUARIO, Venda.FK_USUARIO]",
        overlaps="carrinho,endereco_usuario,usuario,venda,vendas",
    )
    metodo_pagamento: Mapped[MetodoPagamento] = relationship(
        "MetodoPagamento", back_populates="vendas"
    )
    status: Mapped[StatusVenda] = relationship("StatusVenda", back_populates="vendas")
    historico_status: Mapped[list[HistoricoStatusVenda]] = relationship(
        "HistoricoStatusVenda", back_populates="venda"
    )
    itens: Mapped[list[ItemVenda]] = relationship("ItemVenda", back_populates="venda")


class HistoricoStatusVenda(Base):
    """Modelo ORM para a tabela HISTORICO_STATUS_VENDA."""

    __tablename__ = "HISTORICO_STATUS_VENDA"
    __table_args__ = (
        Index("IDX_HIST_STATUS_VENDA_VENDA_DATA", "FK_VENDA", "DATA_EVENTO"),
        Index("IDX_HIST_STATUS_VENDA_STATUS", "FK_STATUS_VENDA"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_VENDA: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "VENDA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_HIST_STATUS_VENDA_VENDA",
        ),
        nullable=False,
    )
    FK_STATUS_VENDA: Mapped[int] = mapped_column(
        tinyint_unsigned,
        ForeignKey(
            "STATUS_VENDA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_HIST_STATUS_VENDA_STATUS",
        ),
        nullable=False,
    )
    DATA_EVENTO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Synonyms
    id = synonym("ID")
    fk_venda = synonym("FK_VENDA")
    fk_status_venda = synonym("FK_STATUS_VENDA")
    data_evento = synonym("DATA_EVENTO")

    # Relacionamentos
    venda: Mapped[Venda] = relationship("Venda", back_populates="historico_status")
    status_venda: Mapped[StatusVenda] = relationship("StatusVenda", back_populates="historico_vendas")


class ItemVenda(Base):
    """Modelo ORM para a tabela ITEM_VENDA."""

    __tablename__ = "ITEM_VENDA"
    __table_args__ = (
        UniqueConstraint("FK_VENDA", "FK_VARIACAO", name="UQ_ITEM_VENDA_VENDA_VARIACAO"),
        Index("IDX_ITEM_VENDA_VARIACAO", "FK_VARIACAO"),
        CheckConstraint("QNT > 0", name="CK_ITEM_VENDA_QNT"),
        CheckConstraint("PRECO_UNITARIO >= 0", name="CK_ITEM_VENDA_PRECO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_VENDA: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "VENDA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_ITEM_VENDA_VENDA",
        ),
        nullable=False,
    )
    FK_VARIACAO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "VARIACAO.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_ITEM_VENDA_VARIACAO",
        ),
        nullable=False,
    )
    QNT: Mapped[int] = mapped_column(smallint_unsigned, nullable=False)
    PRECO_UNITARIO: Mapped[Decimal] = mapped_column(money_decimal, nullable=False)

    # Synonyms
    id = synonym("ID")
    fk_venda = synonym("FK_VENDA")
    fk_variacao = synonym("FK_VARIACAO")
    qnt = synonym("QNT")
    preco_unitario = synonym("PRECO_UNITARIO")

    # Relacionamentos
    venda: Mapped[Venda] = relationship("Venda", back_populates="itens")
    variacao: Mapped[Variacao] = relationship("Variacao", back_populates="itens_venda")
    trocas: Mapped[list[Troca]] = relationship("Troca", back_populates="item_venda")
    reembolsos: Mapped[list[Reembolso]] = relationship("Reembolso", back_populates="item_venda")
    avaliacao: Mapped[Avaliacao | None] = relationship(
        "Avaliacao", back_populates="item_venda", uselist=False
    )
