from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class StrictBase(BaseModel):
    """Modelo base estrito para payloads de autenticação."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LoginPayload(StrictBase):
    """Payload de credenciais de login."""

    email: str = Field(..., min_length=3, max_length=254, description="E-mail ou CPF do usuário")
    password: str = Field(..., min_length=1, max_length=128, description="Senha do usuário")
    next_url: str | None = Field(default=None, max_length=200)


class SolicitarRecuperacaoPayload(StrictBase):
    """Payload para solicitação de token de recuperação de senha."""

    email: str = Field(..., min_length=3, max_length=254)


class ValidarCodigoPayload(StrictBase):
    """Payload para validação do código de verificação numérico."""

    email: str = Field(..., min_length=3, max_length=254)
    codigo: str = Field(..., min_length=4, max_length=10)


class RedefinirSenhaPayload(StrictBase):
    """Payload de redefinição de senha com confirmação."""

    email: str = Field(..., min_length=3, max_length=254)
    codigo: str = Field(..., min_length=4, max_length=10)
    nova_senha: str = Field(..., min_length=12, max_length=128)
    confirmar_senha: str = Field(..., min_length=12, max_length=128)


class RecuperarEmailPayload(StrictBase):
    """Payload para resgate de e-mail censurado por CPF e nascimento."""

    cpf: str = Field(..., min_length=11, max_length=14)
    nascimento: str = Field(..., min_length=8, max_length=10)
    senha: str | None = Field(default=None, max_length=128)


class VerificarUnicidadePayload(StrictBase):
    """Payload para verificação de duplicidade de e-mail e CPF."""

    email: str | None = Field(default=None, max_length=254)
    cpf: str | None = Field(default=None, max_length=14)


class EnderecoCadastroPayload(StrictBase):
    """Payload para cada endereço cadastrado no registro."""

    nome: str = Field(default="Casa", max_length=50)
    cep: str = Field(..., min_length=8, max_length=9)
    logradouro: str = Field(..., min_length=1, max_length=120)
    numero: str = Field(..., min_length=1, max_length=10)
    complemento: str | None = Field(default=None, max_length=80)
    bairro: str = Field(..., min_length=1, max_length=80)
    cidade: str = Field(..., min_length=1, max_length=60)
    estado: str = Field(..., min_length=2, max_length=2)
    principal: bool = Field(default=False)


class RegistroPayload(StrictBase):
    """Payload completo de cadastro de usuário e endereços."""

    email: str = Field(..., pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=254)
    cpf: str = Field(..., min_length=11, max_length=14)
    nome: str = Field(..., min_length=2, max_length=50)
    sobrenome: str = Field(..., min_length=2, max_length=100)
    senha: str = Field(..., min_length=12, max_length=128)
    nascimento: str = Field(..., min_length=8, max_length=10)
    telefone: str = Field(..., min_length=10, max_length=15)
    codigo_verificacao: str = Field(..., min_length=4, max_length=10)
    enderecos: list[EnderecoCadastroPayload] = Field(..., min_length=1, max_length=10)
