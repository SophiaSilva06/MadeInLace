from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.core.database import Base, bool_tinyint, int_unsigned, tinyint_unsigned

if TYPE_CHECKING:
    from app.models.carrinho import Carrinho
    from app.models.venda import Venda


class Usuario(Base):
    """Modelo ORM para a tabela USUARIOS."""

    __tablename__ = "USUARIOS"
    __table_args__ = (
        UniqueConstraint("EMAIL", name="UQ_USUARIOS_EMAIL"),
        UniqueConstraint("CPF", name="UQ_USUARIOS_CPF"),
        CheckConstraint("CPF IS NULL OR CPF REGEXP '^[0-9]{11}$'", name="CK_USUARIOS_CPF"),
        CheckConstraint(
            "TELEFONE IS NULL OR TELEFONE REGEXP '^[0-9]{10,11}$'",
            name="CK_USUARIOS_TELEFONE",
        ),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    NOME: Mapped[str] = mapped_column(String(50), nullable=False)
    SOBRENOME: Mapped[str] = mapped_column(String(100), nullable=False)
    EMAIL: Mapped[str] = mapped_column(String(254), nullable=False)
    SENHA_HASH: Mapped[str] = mapped_column(String(255), nullable=False)
    NASCIMENTO: Mapped[date | None] = mapped_column(Date, nullable=True)
    CPF: Mapped[str | None] = mapped_column(CHAR(11), nullable=True)
    TELEFONE: Mapped[str | None] = mapped_column(String(11), nullable=True)
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))
    IS_ADM: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("0"))
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Synonyms
    id = synonym("ID")
    nome = synonym("NOME")
    sobrenome = synonym("SOBRENOME")
    email = synonym("EMAIL")
    senha_hash = synonym("SENHA_HASH")
    nascimento = synonym("NASCIMENTO")
    cpf = synonym("CPF")
    telefone = synonym("TELEFONE")
    ativo = synonym("ATIVO")
    is_adm = synonym("IS_ADM")
    data_criacao = synonym("DATA_CRIACAO")

    # Relacionamentos
    enderecos: Mapped[list[EnderecoUsuario]] = relationship(
        "EnderecoUsuario", back_populates="usuario", cascade="all, delete-orphan"
    )
    recuperacoes: Mapped[list[Recuperacao]] = relationship(
        "Recuperacao", back_populates="usuario", cascade="all, delete-orphan"
    )
    carrinhos: Mapped[list[Carrinho]] = relationship("Carrinho", back_populates="usuario")
    vendas: Mapped[list[Venda]] = relationship(
        "Venda",
        back_populates="usuario",
        primaryjoin="Usuario.ID == foreign(Venda.FK_USUARIO)",
        overlaps="carrinho,endereco_usuario,usuario,venda,vendas",
    )


# Alias plural
Usuarios = Usuario


class EnderecoUsuario(Base):
    """Modelo ORM para a tabela ENDERECO_USUARIO."""

    __tablename__ = "ENDERECO_USUARIO"
    __table_args__ = (
        UniqueConstraint("ID", "FK_USUARIO", name="UQ_ENDERECO_USUARIO_ID_USUARIO"),
        Index("IDX_ENDERECO_USUARIO_USUARIO", "FK_USUARIO", "ATIVO"),
        CheckConstraint("CEP REGEXP '^[0-9]{8}$'", name="CK_ENDERECO_USUARIO_CEP"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_USUARIO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "USUARIOS.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_ENDERECO_USUARIO_USUARIO",
        ),
        nullable=False,
    )
    NOME: Mapped[str] = mapped_column(String(50), nullable=False)
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
    fk_usuario = synonym("FK_USUARIO")
    nome = synonym("NOME")
    cep = synonym("CEP")
    logradouro = synonym("LOGRADOURO")
    numero = synonym("NUMERO")
    complemento = synonym("COMPLEMENTO")
    bairro = synonym("BAIRRO")
    cidade = synonym("CIDADE")
    estado = synonym("ESTADO")
    ativo = synonym("ATIVO")

    # Relacionamentos
    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="enderecos")
    vendas: Mapped[list[Venda]] = relationship(
        "Venda",
        back_populates="endereco_usuario",
        foreign_keys="[Venda.FK_ENDERECO_USUARIO, Venda.FK_USUARIO]",
        overlaps="carrinho,endereco_usuario,usuario,venda,vendas",
    )


class Recuperacao(Base):
    """Modelo ORM para a tabela RECUPERACAO."""

    __tablename__ = "RECUPERACAO"
    __table_args__ = (
        UniqueConstraint("TOKEN", name="UQ_RECUPERACAO_TOKEN"),
        Index("IDX_RECUPERACAO_USUARIO", "FK_USUARIO"),
        CheckConstraint("DATA_EXPIRA > DATA_CRIACAO", name="CK_RECUPERACAO_DATAS"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_USUARIO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "USUARIOS.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_RECUPERACAO_USUARIO",
        ),
        nullable=False,
    )
    TOKEN: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    DATA_EXPIRA: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    EXPIRADO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("0"))

    # Synonyms
    id = synonym("ID")
    fk_usuario = synonym("FK_USUARIO")
    token = synonym("TOKEN")
    data_criacao = synonym("DATA_CRIACAO")
    data_expira = synonym("DATA_EXPIRA")
    expirado = synonym("EXPIRADO")

    # Relacionamentos
    usuario: Mapped[Usuario] = relationship("Usuario", back_populates="recuperacoes")


class VerificacaoEmail(Base):
    """Modelo ORM para a tabela VERIFICACAO_EMAIL."""

    __tablename__ = "VERIFICACAO_EMAIL"
    __table_args__ = (
        UniqueConstraint("TOKEN", name="UQ_VERIFICACAO_EMAIL_TOKEN"),
        Index("IDX_VERIFICACAO_EMAIL_BUSCA", "EMAIL", "EXPIRADO", "DATA_EXPIRA"),
        CheckConstraint("DATA_EXPIRA > DATA_CRIACAO", name="CK_VERIFICACAO_EMAIL_DATAS"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    EMAIL: Mapped[str] = mapped_column(String(254), nullable=False)
    TOKEN: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    DATA_EXPIRA: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    EXPIRADO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("0"))
    TENTATIVAS: Mapped[int] = mapped_column(tinyint_unsigned, nullable=False, server_default=text("0"))

    # Synonyms
    id = synonym("ID")
    email = synonym("EMAIL")
    token = synonym("TOKEN")
    data_criacao = synonym("DATA_CRIACAO")
    data_expira = synonym("DATA_EXPIRA")
    expirado = synonym("EXPIRADO")
    tentativas = synonym("TENTATIVAS")

