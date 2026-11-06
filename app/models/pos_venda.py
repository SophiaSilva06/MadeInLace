from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import (
    Base,
    bool_tinyint,
    int_unsigned,
    smallint_unsigned,
    tinyint_unsigned,
)

if TYPE_CHECKING:
    from app.models.dominio import StatusTroca
    from app.models.produto import Variacao
    from app.models.venda import ItemVenda


class Troca(Base):
    """Modelo ORM para a tabela TROCA."""

    __tablename__ = "TROCA"
    __table_args__ = (
        Index("IDX_TROCA_ITEM_VENDA", "FK_ITEM_VENDA"),
        Index("IDX_TROCA_STATUS", "FK_STATUS_TROCA"),
        Index("IDX_TROCA_VARIACAO_NOVA", "FK_VARIACAO_NOVA"),
        CheckConstraint("QNT > 0", name="CK_TROCA_QNT"),
        CheckConstraint(
            "(CONCLUSAO = 0 AND DATA_CONCLUSAO IS NULL) OR "
            "(CONCLUSAO = 1 AND DATA_CONCLUSAO IS NOT NULL)",
            name="CK_TROCA_CONCLUSAO",
        ),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_ITEM_VENDA: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "ITEM_VENDA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_TROCA_ITEM_VENDA",
        ),
        nullable=False,
    )
    FK_STATUS_TROCA: Mapped[int] = mapped_column(
        tinyint_unsigned,
        ForeignKey(
            "STATUS_TROCA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_TROCA_STATUS",
        ),
        nullable=False,
    )
    FK_VARIACAO_NOVA: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "VARIACAO.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_TROCA_VARIACAO_NOVA",
        ),
        nullable=False,
    )
    QNT: Mapped[int] = mapped_column(smallint_unsigned, nullable=False, server_default=text("1"))
    MOTIVO: Mapped[str | None] = mapped_column(String(500), nullable=True)
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))
    CONCLUSAO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("0"))
    DATA_CONCLUSAO: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Synonyms
    id = synonym("ID")
    fk_item_venda = synonym("FK_ITEM_VENDA")
    fk_status_troca = synonym("FK_STATUS_TROCA")
    fk_variacao_nova = synonym("FK_VARIACAO_NOVA")
    qnt = synonym("QNT")
    motivo = synonym("MOTIVO")
    data_criacao = synonym("DATA_CRIACAO")
    ativo = synonym("ATIVO")
    conclusao = synonym("CONCLUSAO")
    data_conclusao = synonym("DATA_CONCLUSAO")

    # Relacionamentos
    item_venda: Mapped[ItemVenda] = relationship("ItemVenda", back_populates="trocas")
    status_troca: Mapped[StatusTroca] = relationship("StatusTroca", back_populates="trocas")
    variacao_nova: Mapped[Variacao] = relationship("Variacao", back_populates="trocas_como_nova")
    historico_status: Mapped[list[HistoricoStatusTroca]] = relationship(
        "HistoricoStatusTroca", back_populates="troca"
    )


class HistoricoStatusTroca(Base):
    """Modelo ORM para a tabela HISTORICO_STATUS_TROCA."""

    __tablename__ = "HISTORICO_STATUS_TROCA"
    __table_args__ = (
        Index("IDX_HIST_STATUS_TROCA_TROCA_DATA", "FK_TROCA", "DATA_EVENTO"),
        Index("IDX_HIST_STATUS_TROCA_STATUS", "FK_STATUS_TROCA"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_TROCA: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "TROCA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_HIST_STATUS_TROCA_TROCA",
        ),
        nullable=False,
    )
    FK_STATUS_TROCA: Mapped[int] = mapped_column(
        tinyint_unsigned,
        ForeignKey(
            "STATUS_TROCA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_HIST_STATUS_TROCA_STATUS",
        ),
        nullable=False,
    )
    DATA_EVENTO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Synonyms
    id = synonym("ID")
    fk_troca = synonym("FK_TROCA")
    fk_status_troca = synonym("FK_STATUS_TROCA")
    data_evento = synonym("DATA_EVENTO")

    # Relacionamentos
    troca: Mapped[Troca] = relationship("Troca", back_populates="historico_status")
    status_troca: Mapped[StatusTroca] = relationship("StatusTroca", back_populates="historico_trocas")


class Reembolso(Base):
    """Modelo ORM para a tabela REEMBOLSO."""

    __tablename__ = "REEMBOLSO"
    __table_args__ = (
        Index("IDX_REEMBOLSO_ITEM_VENDA", "FK_ITEM_VENDA"),
        CheckConstraint("QNT > 0", name="CK_REEMBOLSO_QNT"),
        CheckConstraint(
            "(CONCLUSAO = 0 AND DATA_CONCLUSAO IS NULL) OR "
            "(CONCLUSAO = 1 AND DATA_CONCLUSAO IS NOT NULL)",
            name="CK_REEMBOLSO_CONCLUSAO",
        ),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_ITEM_VENDA: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "ITEM_VENDA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_REEMBOLSO_ITEM_VENDA",
        ),
        nullable=False,
    )
    QNT: Mapped[int] = mapped_column(smallint_unsigned, nullable=False, server_default=text("1"))
    MOTIVO: Mapped[str] = mapped_column(String(500), nullable=False)
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))
    CONCLUSAO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("0"))
    DATA_CONCLUSAO: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Synonyms
    id = synonym("ID")
    fk_item_venda = synonym("FK_ITEM_VENDA")
    qnt = synonym("QNT")
    motivo = synonym("MOTIVO")
    data_criacao = synonym("DATA_CRIACAO")
    ativo = synonym("ATIVO")
    conclusao = synonym("CONCLUSAO")
    data_conclusao = synonym("DATA_CONCLUSAO")

    # Relacionamentos
    item_venda: Mapped[ItemVenda] = relationship("ItemVenda", back_populates="reembolsos")
