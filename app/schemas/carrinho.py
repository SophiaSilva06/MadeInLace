from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictBase(BaseModel):
    """Modelo base estrito para payloads do carrinho."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AdicionarItemPayload(StrictBase):
    """Payload para adicionar item ao carrinho."""

    produto_id: int | None = Field(default=None, ge=1, description="ID do produto")
    variacao_id: int | None = Field(default=None, ge=1, description="ID da variação direta")
    tamanho: str | None = Field(default=None, max_length=10, description="Tamanho selecionado")
    cor: str | None = Field(default=None, max_length=30, description="Cor selecionada")
    quantidade: int = Field(default=1, ge=1, le=10, description="Quantidade a adicionar")


class AtualizarQuantidadePayload(StrictBase):
    """Payload para alterar a quantidade de um item no carrinho."""

    item_id: int = Field(..., ge=1, description="ID do ITEM_CARRINHO")
    quantidade: int = Field(..., ge=1, le=10, description="Nova quantidade desejada")


class RemoverItemPayload(StrictBase):
    """Payload para remover um item do carrinho."""

    item_id: int = Field(..., ge=1, description="ID do ITEM_CARRINHO a remover")


class ItemCarrinhoDTO(BaseModel):
    """Representação serializável de um item do carrinho."""

    id: int
    variacao_id: int
    produto_id: int
    nome: str
    cor: str
    tamanho: str
    imagem_url: str
    quantidade: int
    preco_unitario: float
    preco_unitario_formatado: str
    subtotal: float
    subtotal_formatado: str
    reservado_ate: str
    segundos_restantes: float
    expirado: bool


class CarrinhoDTO(BaseModel):
    """Representação serializável do estado completo do carrinho."""

    id: int
    autenticado: bool = True
    total: float
    total_formatado: str
    subtotal: float
    subtotal_formatado: str
    frete_gratis: bool
    quantidade_total: int
    meta_frete_gratis: float = 160.0
    valor_para_frete_gratis: float
    valor_para_frete_gratis_formatado: str
    porcentagem_frete_gratis: float
    itens: list[ItemCarrinhoDTO] = []
