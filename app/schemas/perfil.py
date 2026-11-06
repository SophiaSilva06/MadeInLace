from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EnderecoPerfilPayload(BaseModel):
    """Payload para criação ou modificação de endereço na aba do perfil."""

    model_config = ConfigDict(extra="ignore")

    id: int | None = Field(default=None, description="ID do endereço existente a modificar")
    nome: str = Field(..., min_length=1, max_length=50, description="Apelido do endereço (ex: Casa)")
    cep: str = Field(..., min_length=8, max_length=10, description="CEP do endereço")
    logradouro: str = Field(..., min_length=1, max_length=120, description="Logradouro/Rua")
    numero: str = Field(..., min_length=1, max_length=10, description="Número da residência")
    complemento: str | None = Field(default=None, max_length=80, description="Complemento (opcional)")
    bairro: str = Field(..., min_length=1, max_length=80, description="Bairro")
    cidade: str = Field(..., min_length=1, max_length=60, description="Cidade")
    estado: str = Field(..., min_length=2, max_length=20, description="UF ou nome do estado")
    is_principal: bool = Field(default=False, description="Indica se é o endereço principal")


class AtualizarPerfilPayload(BaseModel):
    """Payload consolidado submetido ao clicar em 'Salvar Informações'."""

    model_config = ConfigDict(extra="ignore")

    nome: str = Field(..., min_length=1, max_length=50, description="Nome do cliente")
    sobrenome: str = Field(..., min_length=1, max_length=100, description="Sobrenome do cliente")
    telefone: str | None = Field(default=None, max_length=20, description="Telefone com DDD")

    # Campos para alteração de senha
    senha_atual: str | None = Field(default=None, description="Senha atual para confirmação de alterações sensíveis")
    nova_senha: str | None = Field(default=None, description="Nova senha desejada")
    confirmar_nova_senha: str | None = Field(default=None, description="Confirmação da nova senha")

    # Campos para alteração de e-mail
    novo_email: str | None = Field(default=None, description="Novo e-mail a ser definido")
    codigo_email_atual: str | None = Field(default=None, description="Código de 6 dígitos enviado ao e-mail antigo")
    codigo_email_novo: str | None = Field(default=None, description="Código de 6 dígitos enviado ao novo e-mail")

    # Endereços modificados ou adicionados
    enderecos: list[EnderecoPerfilPayload] | None = Field(
        default=None, description="Lista de endereços a serem persistidos"
    )
    endereco_principal_id: int | None = Field(
        default=None, description="ID do endereço definido como principal pelo usuário"
    )


class SolicitarCodigoEmailPayload(BaseModel):
    """Payload para envio de código para um endereço de e-mail."""

    model_config = ConfigDict(extra="ignore")

    email: str = Field(..., min_length=5, max_length=254, description="Endereço de e-mail de destino")


class ValidarCodigoEmailPayload(BaseModel):
    """Payload para validar a troca de e-mail antes do salvamento consolidado."""

    model_config = ConfigDict(extra="ignore")

    email_atual: str = Field(..., description="E-mail atual cadastrado")
    codigo_atual: str = Field(..., min_length=4, max_length=10, description="Código recebido no e-mail atual")
    novo_email: str = Field(..., description="Novo e-mail a cadastrar")
    codigo_novo: str = Field(..., min_length=4, max_length=10, description="Código recebido no novo e-mail")
    senha_atual: str = Field(..., description="Senha atual do cliente")


class TrocaPayload(BaseModel):
    """Payload para solicitação de troca de um item de venda."""

    model_config = ConfigDict(extra="ignore")

    item_venda_id: int = Field(..., ge=1, description="ID do ITEM_VENDA a ser trocado")
    quantidade: int = Field(..., ge=1, description="Quantidade a trocar (de 1 até o máximo comprado)")
    motivo: str | None = Field(default=None, max_length=500, description="Motivo da troca (opcional)")
    variacoes_novas: list[int] = Field(
        ..., min_length=1, description="Lista com os IDs das novas variações para cada unidade"
    )


class ReembolsoPayload(BaseModel):
    """Payload para solicitação de reembolso de um item de venda."""

    model_config = ConfigDict(extra="ignore")

    item_venda_id: int = Field(..., ge=1, description="ID do ITEM_VENDA a ser reembolsado")
    quantidade: int = Field(..., ge=1, description="Quantidade a reembolsar (de 1 até o máximo comprado)")
    motivo: str = Field(..., min_length=3, max_length=500, description="Motivo do reembolso (obrigatório)")
