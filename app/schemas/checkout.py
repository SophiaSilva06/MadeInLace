from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictBase(BaseModel):
    """Modelo base estrito para payloads de checkout."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SalvarEnderecoCheckoutPayload(StrictBase):
    """Payload para adicionar ou selecionar endereço no modal 'Modificar Endereços'."""

    id: int | None = Field(default=None, ge=1, description="ID do endereço existente para seleção/edição")
    nome: str = Field(..., min_length=1, max_length=50, description="Apelido: Casa, Trabalho")
    cep: str = Field(..., min_length=8, max_length=9, description="CEP com ou sem traço")
    logradouro: str = Field(..., min_length=1, max_length=120, description="Rua, Avenida, etc.")
    numero: str = Field(..., min_length=1, max_length=10, description="Número predial")
    complemento: str | None = Field(default=None, max_length=80, description="Complemento opcional")
    bairro: str = Field(..., min_length=1, max_length=80, description="Bairro")
    cidade: str = Field(..., min_length=1, max_length=60, description="Cidade")
    estado: str = Field(..., min_length=2, max_length=2, description="UF em 2 letras (SP, RJ, etc.)")


class FinalizarCompraPayload(StrictBase):
    """Payload para confirmação e gravação da venda simulada no banco de dados."""

    endereco_id: int = Field(..., ge=1, description="ID do ENDERECO_USUARIO selecionado")
    metodo_pagamento: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Método selecionado (Pix, Boleto, Cartão de crédito, Cartão de débito)",
    )


class ItemCheckoutDTO(BaseModel):
    """Representação serializada de cada item do carrinho exibido na coluna direita do checkout."""

    item_carrinho_id: int
    variacao_id: int
    produto_id: int
    nome: str
    tamanho: str
    cor: str
    qnt: int
    preco_unitario: Decimal
    preco_unitario_formatado: str
    subtotal: Decimal
    subtotal_formatado: str
    imagem_url: str


class ResumoCheckoutDTO(BaseModel):
    """Resumo integral de valores, endereços e itens para renderização do checkout."""

    subtotal: Decimal
    subtotal_formatado: str
    primeira_compra: bool
    valor_desconto: Decimal
    valor_desconto_formatado: str
    frete: Decimal
    frete_formatado: str
    frete_gratis: bool
    total: Decimal
    total_formatado: str
    endereco_selecionado: dict[str, Any] | None
    enderecos_usuario: list[dict[str, Any]]
    itens: list[ItemCheckoutDTO]
    metodos_pagamento: list[dict[str, Any]]
