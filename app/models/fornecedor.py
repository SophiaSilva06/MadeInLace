from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import (
    Base,
    bool_tinyint,
    int_unsigned,
    smallint_unsigned,
)

if TYPE_CHECKING:
    from app.models.produto import Produto


class Fornecedor(Base):
    """Modelo ORM para a tabela FORNECEDORES."""

    __tablename__ = "FORNECEDORES"
    __table_args__ = (
        UniqueConstraint("CNPJ", name="UQ_FORNECEDORES_CNPJ"),
        CheckConstraint("CNPJ REGEXP '^[0-9]{14}$'", name="CK_FORNECEDORES_CNPJ"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(smallint_unsigned, primary_key=True, autoincrement=True)
    NOME: Mapped[str] = mapped_column(String(100), nullable=False)
    CNPJ: Mapped[str] = mapped_column(CHAR(14), nullable=False)
    RAZAO_SOCIAL: Mapped[str] = mapped_column(String(150), nullable=False)
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))

    # Synonyms
    id = synonym("ID")
    nome = synonym("NOME")
    cnpj = synonym("CNPJ")
    razao_social = synonym("RAZAO_SOCIAL")
    ativo = synonym("ATIVO")

    # Relacionamentos bidirecionais
    emails: Mapped[list[EmailsFornecedor]] = relationship(
        "EmailsFornecedor", back_populates="fornecedor", cascade="all, delete-orphan"
    )
    telefones: Mapped[list[TelefoneFornecedor]] = relationship(
        "TelefoneFornecedor", back_populates="fornecedor", cascade="all, delete-orphan"
    )
    enderecos: Mapped[list[EnderecoFornecedor]] = relationship(
        "EnderecoFornecedor", back_populates="fornecedor", cascade="all, delete-orphan"
    )
    produtos: Mapped[list[Produto]] = relationship("Produto", back_populates="fornecedor")


# Alias plural para consistência de importação
Fornecedores = Fornecedor


class EmailsFornecedor(Base):
    """Modelo ORM para a tabela EMAILS_FORNECEDOR."""

    __tablename__ = "EMAILS_FORNECEDOR"
    __table_args__ = (
        UniqueConstraint("FK_FORNECEDOR", "EMAIL", name="UQ_EMAILS_FORNECEDOR"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_FORNECEDOR: Mapped[int] = mapped_column(
        smallint_unsigned,
        ForeignKey(
            "FORNECEDORES.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_EMAILS_FORNECEDOR_FORNECEDOR",
        ),
        nullable=False,
    )
    EMAIL: Mapped[str] = mapped_column(String(254), nullable=False)
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))

    # Synonyms
    id = synonym("ID")
    fk_fornecedor = synonym("FK_FORNECEDOR")
    email = synonym("EMAIL")
    ativo = synonym("ATIVO")

    # Relacionamentos
    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor", back_populates="emails")


class TelefoneFornecedor(Base):
    """Modelo ORM para a tabela TELEFONE_FORNECEDOR."""

    __tablename__ = "TELEFONE_FORNECEDOR"
    __table_args__ = (
        UniqueConstraint("FK_FORNECEDOR", "DDD", "TELEFONE", name="UQ_TELEFONE_FORNECEDOR"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_FORNECEDOR: Mapped[int] = mapped_column(
        smallint_unsigned,
        ForeignKey(
            "FORNECEDORES.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_TELEFONE_FORNECEDOR_FORNECEDOR",
        ),
        nullable=False,
    )
    DDD: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    TELEFONE: Mapped[str] = mapped_column(String(9), nullable=False)
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))

    # Synonyms
    id = synonym("ID")
    fk_fornecedor = synonym("FK_FORNECEDOR")
    ddd = synonym("DDD")
    telefone = synonym("TELEFONE")
    ativo = synonym("ATIVO")

    # Relacionamentos
    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor", back_populates="telefones")


class EnderecoFornecedor(Base):
    """Modelo ORM para a tabela ENDERECO_FORNECEDOR."""

    __tablename__ = "ENDERECO_FORNECEDOR"
    __table_args__ = (
        Index("IDX_ENDERECO_FORNECEDOR_FORNECEDOR", "FK_FORNECEDOR"),
        CheckConstraint("CEP REGEXP '^[0-9]{8}$'", name="CK_ENDERECO_FORNECEDOR_CEP"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_FORNECEDOR: Mapped[int] = mapped_column(
        smallint_unsigned,
        ForeignKey(
            "FORNECEDORES.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_ENDERECO_FORNECEDOR_FORNECEDOR",
        ),
        nullable=False,
    )
    CEP: Mapped[str] = mapped_column(CHAR(8), nullable=False)
    LOGRADOURO: Mapped[str] = mapped_column(String(120), nullable=False)
    NUMERO: Mapped[str] = mapped_column(String(10), nullable=False)
    COMPLEMENTO: Mapped[str | None] = mapped_column(String(80), nullable=True)
    BAIRRO: Mapped[str] = mapped_column(String(80), nullable=False)
    CIDADE: Mapped[str] = mapped_column(String(60), nullable=False)
    ESTADO: Mapped[str] = mapped_column(CHAR(2), nullable=False)
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))

    # Synonyms
    id = synonym("ID")
    fk_fornecedor = synonym("FK_FORNECEDOR")
    cep = synonym("CEP")
    logradouro = synonym("LOGRADOURO")
    numero = synonym("NUMERO")
    complemento = synonym("COMPLEMENTO")
    bairro = synonym("BAIRRO")
    cidade = synonym("CIDADE")
    estado = synonym("ESTADO")
    ativo = synonym("ATIVO")

    # Relacionamentos
    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor", back_populates="enderecos")
