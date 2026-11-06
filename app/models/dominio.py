from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import Base, smallint_unsigned, tinyint_unsigned

if TYPE_CHECKING:
    from app.models.pos_venda import HistoricoStatusTroca, Troca
    from app.models.produto import Produto
    from app.models.venda import HistoricoStatusVenda, Venda


class Linha(Base):
    """Modelo ORM para a tabela LINHA (categorias/linhas de produtos)."""

    __tablename__ = "LINHA"
    __table_args__ = (
        UniqueConstraint("NOME", name="UQ_LINHA_NOME"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(smallint_unsigned, primary_key=True, autoincrement=True)
    NOME: Mapped[str] = mapped_column(String(100), nullable=False)

    # Synonyms para ergonomia pythônica
    id = synonym("ID")
    nome = synonym("NOME")

    # Relacionamentos bidirecionais
    produtos: Mapped[list[Produto]] = relationship("Produto", back_populates="linha")


class MetodoPagamento(Base):
    """Modelo ORM para a tabela METODO_PAGAMENTO (métodos de pagamento suportados)."""

    __tablename__ = "METODO_PAGAMENTO"
    __table_args__ = (
        UniqueConstraint("METODO", name="UQ_METODO_PAGAMENTO_METODO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(tinyint_unsigned, primary_key=True, autoincrement=True)
    METODO: Mapped[str] = mapped_column(String(30), nullable=False)

    # Synonyms
    id = synonym("ID")
    metodo = synonym("METODO")

    # Relacionamentos bidirecionais
    vendas: Mapped[list[Venda]] = relationship("Venda", back_populates="metodo_pagamento")


class StatusVenda(Base):
    """Modelo ORM para a tabela STATUS_VENDA (etapas de rastreamento do pedido de venda)."""

    __tablename__ = "STATUS_VENDA"
    __table_args__ = (
        UniqueConstraint("ESTADO_ANDAMENTO", name="UQ_STATUS_VENDA_ESTADO"),
        UniqueConstraint("DESCRICAO", name="UQ_STATUS_VENDA_DESCRICAO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(tinyint_unsigned, primary_key=True, autoincrement=True)
    ESTADO_ANDAMENTO: Mapped[str] = mapped_column(
        Enum(
            "EM_PROCESSAMENTO",
            "NA_TRANSPORTADORA",
            "EM_TRANSITO",
            "ENTREGANDO",
            "ENTREGUE",
            "TENTATIVA_FALHA",
            "CANCELADO",
            name="status_venda_estado_enum",
        ),
        nullable=False,
    )
    DESCRICAO: Mapped[str] = mapped_column(String(80), nullable=False)

    # Synonyms
    id = synonym("ID")
    estado_andamento = synonym("ESTADO_ANDAMENTO")
    descricao = synonym("DESCRICAO")

    # Relacionamentos bidirecionais
    vendas: Mapped[list[Venda]] = relationship("Venda", back_populates="status")
    historico_vendas: Mapped[list[HistoricoStatusVenda]] = relationship(
        "HistoricoStatusVenda", back_populates="status_venda"
    )


class StatusTroca(Base):
    """Modelo ORM para a tabela STATUS_TROCA (etapas de análise e entrega da troca)."""

    __tablename__ = "STATUS_TROCA"
    __table_args__ = (
        UniqueConstraint("ESTADO_ANDAMENTO", name="UQ_STATUS_TROCA_ESTADO"),
        UniqueConstraint("DESCRICAO", name="UQ_STATUS_TROCA_DESCRICAO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(tinyint_unsigned, primary_key=True, autoincrement=True)
    ESTADO_ANDAMENTO: Mapped[str] = mapped_column(
        Enum(
            "SOLICITADA",
            "APROVADA",
            "DEVOLUCAO_RECEBIDA",
            "EM_PROCESSAMENTO",
            "NA_TRANSPORTADORA",
            "ENTREGANDO",
            "ENTREGUE",
            "RECUSADA",
            name="status_troca_estado_enum",
        ),
        nullable=False,
    )
    DESCRICAO: Mapped[str] = mapped_column(String(80), nullable=False)

    # Synonyms
    id = synonym("ID")
    estado_andamento = synonym("ESTADO_ANDAMENTO")
    descricao = synonym("DESCRICAO")

    # Relacionamentos bidirecionais
    trocas: Mapped[list[Troca]] = relationship("Troca", back_populates="status_troca")
    historico_trocas: Mapped[list[HistoricoStatusTroca]] = relationship(
        "HistoricoStatusTroca", back_populates="status_troca"
    )
