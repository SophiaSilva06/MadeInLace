from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
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
    percent_decimal,
    smallint_unsigned,
)

if TYPE_CHECKING:
    from app.models.carrinho import ItemCarrinho
    from app.models.dominio import Linha
    from app.models.fornecedor import Fornecedor
    from app.models.pos_venda import Troca
    from app.models.venda import ItemVenda


class Produto(Base):
    """Modelo ORM para a tabela PRODUTOS."""

    __tablename__ = "PRODUTOS"
    __table_args__ = (
        Index("IDX_PRODUTOS_FORNECEDOR", "FK_FORNECEDOR"),
        Index("IDX_PRODUTOS_LINHA", "FK_LINHA"),
        Index("IDX_PRODUTOS_TIPO_ATIVO", "TIPO", "ATIVO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_FORNECEDOR: Mapped[int] = mapped_column(
        smallint_unsigned,
        ForeignKey(
            "FORNECEDORES.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_PRODUTOS_FORNECEDOR",
        ),
        nullable=False,
    )
    FK_LINHA: Mapped[int] = mapped_column(
        smallint_unsigned,
        ForeignKey(
            "LINHA.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_PRODUTOS_LINHA",
        ),
        nullable=False,
    )
    NOME: Mapped[str] = mapped_column(String(150), nullable=False)
    DESCRICAO: Mapped[str | None] = mapped_column(Text, nullable=True)
    TIPO: Mapped[str] = mapped_column(
        Enum("roupa", "calcado", "corset", name="produto_tipo_enum"),
        nullable=False,
    )
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))
    DATA_CRIACAO: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    # Synonyms
    id = synonym("ID")
    fk_fornecedor = synonym("FK_FORNECEDOR")
    fk_linha = synonym("FK_LINHA")
    nome = synonym("NOME")
    descricao = synonym("DESCRICAO")
    tipo = synonym("TIPO")
    ativo = synonym("ATIVO")
    data_criacao = synonym("DATA_CRIACAO")

    # Relacionamentos
    fornecedor: Mapped[Fornecedor] = relationship("Fornecedor", back_populates="produtos")
    linha: Mapped[Linha] = relationship("Linha", back_populates="produtos")
    imagens: Mapped[list[ImgsProduto]] = relationship(
        "ImgsProduto", back_populates="produto", cascade="all, delete-orphan"
    )
    variacoes: Mapped[list[Variacao]] = relationship("Variacao", back_populates="produto")


# Aliases plurais para ergonomia
Produtos = Produto


class ImgsProduto(Base):
    """Modelo ORM para a tabela IMGS_PRODUTOS."""

    __tablename__ = "IMGS_PRODUTOS"
    __table_args__ = (
        Index("IDX_IMGS_PRODUTOS_PRODUTO", "FK_PRODUTO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_PRODUTO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "PRODUTOS.ID",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name="FK_IMGS_PRODUTOS_PRODUTO",
        ),
        nullable=False,
    )
    URL_IMAGEM: Mapped[str] = mapped_column(String(255), nullable=False)
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))

    # Synonyms
    id = synonym("ID")
    fk_produto = synonym("FK_PRODUTO")
    url_imagem = synonym("URL_IMAGEM")
    ativo = synonym("ATIVO")

    # Relacionamentos
    produto: Mapped[Produto] = relationship("Produto", back_populates="imagens")


ImgsProdutos = ImgsProduto


class Variacao(Base):
    """Modelo ORM para a tabela VARIACAO."""

    __tablename__ = "VARIACAO"
    __table_args__ = (
        UniqueConstraint("FK_PRODUTO", "TAMANHO", "COR", name="UQ_VARIACAO_PRODUTO_TAMANHO_COR"),
        CheckConstraint("CUSTO >= 0", name="CK_VARIACAO_CUSTO"),
        CheckConstraint("PRECO > 0", name="CK_VARIACAO_PRECO"),
        CheckConstraint("PORCENTAGEM_PROMOCAO BETWEEN 0 AND 100", name="CK_VARIACAO_PROMOCAO"),
        {"mysql_engine": "InnoDB"},
    )

    ID: Mapped[int] = mapped_column(int_unsigned, primary_key=True, autoincrement=True)
    FK_PRODUTO: Mapped[int] = mapped_column(
        int_unsigned,
        ForeignKey(
            "PRODUTOS.ID",
            onupdate="CASCADE",
            ondelete="RESTRICT",
            name="FK_VARIACAO_PRODUTO",
        ),
        nullable=False,
    )
    TAMANHO: Mapped[str] = mapped_column(String(10), nullable=False)
    COR: Mapped[str] = mapped_column(String(30), nullable=False)
    ESTOQUE: Mapped[int] = mapped_column(int_unsigned, nullable=False, server_default=text("0"))
    CUSTO: Mapped[Decimal] = mapped_column(money_decimal, nullable=False)
    PRECO: Mapped[Decimal] = mapped_column(money_decimal, nullable=False)
    PORCENTAGEM_PROMOCAO: Mapped[Decimal] = mapped_column(
        percent_decimal, nullable=False, server_default=text("0.00")
    )
    ATIVO: Mapped[bool] = mapped_column(bool_tinyint, nullable=False, server_default=text("1"))

    # Synonyms
    id = synonym("ID")
    fk_produto = synonym("FK_PRODUTO")
    tamanho = synonym("TAMANHO")
    cor = synonym("COR")
    estoque = synonym("ESTOQUE")
    custo = synonym("CUSTO")
    preco = synonym("PRECO")
    porcentagem_promocao = synonym("PORCENTAGEM_PROMOCAO")
    ativo = synonym("ATIVO")

    # Relacionamentos
    produto: Mapped[Produto] = relationship("Produto", back_populates="variacoes")
    itens_carrinho: Mapped[list[ItemCarrinho]] = relationship("ItemCarrinho", back_populates="variacao")
    itens_venda: Mapped[list[ItemVenda]] = relationship("ItemVenda", back_populates="variacao")
    trocas_como_nova: Mapped[list[Troca]] = relationship("Troca", back_populates="variacao_nova")
