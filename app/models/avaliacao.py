from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import (
    Base,
    bool_tinyint,
    int_unsigned,
    tinyint_unsigned,
)

if TYPE_CHECKING:
    from app.models.venda import ItemVenda


class Avaliacao(Base):
    """Modelo ORM para a tabela AVALIACAO."""

    __tablename__ = "AVALIACAO"
    __table_args__ = (
        UniqueConstraint("FK_ITEM_VENDA", name="UQ_AVALIACAO_ITEM_VENDA"),
        CheckConstraint("NOTA BETWEEN 1 AND 5", name="CK_AVALIACAO_NOTA"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_ITEM_VENDA: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "ITEM_VENDA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_AVALIACAO_ITEM_VENDA",
        ),
        nullable=False,
    )
    NOTA: Mapped[int] = mapped_column(tinyint_unsigned, nullable=False)
    COMENTARIO: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Synonyms
    id = synonym("ID")
    fk_item_venda = synonym("FK_ITEM_VENDA")
    nota = synonym("NOTA")
    comentario = synonym("COMENTARIO")
    data_criacao = synonym("DATA_CRIACAO")

    # Relacionamentos
    item_venda: Mapped[ItemVenda] = relationship("ItemVenda", back_populates="avaliacao")
    imagens: Mapped[list[ImgsAvaliacao]] = relationship(
        "ImgsAvaliacao", back_populates="avaliacao", cascade="all, delete-orphan"
    )


class ImgsAvaliacao(Base):
    """Modelo ORM para a tabela IMGS_AVALIACAO."""

    __tablename__ = "IMGS_AVALIACAO"
    __table_args__ = (
        Index("IDX_IMGS_AVALIACAO_AVALIACAO", "FK_AVALIACAO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_AVALIACAO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "AVALIACAO.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_IMGS_AVALIACAO_AVALIACAO",
        ),
        nullable=False,
    )
    URL_IMAGEM: Mapped[str] = mapped_column(String(255), nullable=False)
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))

    # Synonyms
    id = synonym("ID")
    fk_avaliacao = synonym("FK_AVALIACAO")
    url_imagem = synonym("URL_IMAGEM")
    ativo = synonym("ATIVO")

    # Relacionamentos
    avaliacao: Mapped[Avaliacao] = relationship("Avaliacao", back_populates="imagens")
