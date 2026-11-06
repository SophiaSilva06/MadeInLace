from __future__ import annotations

import base64
import hashlib
import os
import re
import secrets
from typing import Final

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

# Parâmetros recomendados para Argon2id em conformidade com OWASP
ARGON2_TIME_COST: Final[int] = 2
ARGON2_MEMORY_COST: Final[int] = 65536
ARGON2_PARALLELISM: Final[int] = 4
ARGON2_KEY_LENGTH: Final[int] = 32


def _b64decode_unpadded(s: str) -> bytes:
    """Decodifica base64 permitindo strings com ou sem padding '='."""
    clean = s.strip()
    rem = len(clean) % 4
    if rem:
        clean += "=" * (4 - rem)
    return base64.b64decode(clean.encode("ascii"))


def hash_password(plain_password: str) -> str:
    """Gera um hash seguro de senha utilizando o algoritmo Argon2id no formato padrão RFC 9106."""
    salt = os.urandom(16)
    kdf = Argon2id(
        salt=salt,
        length=ARGON2_KEY_LENGTH,
        iterations=ARGON2_TIME_COST,
        lanes=ARGON2_PARALLELISM,
        memory_cost=ARGON2_MEMORY_COST,
    )
    derived = kdf.derive(plain_password.encode("utf-8"))
    salt_b64 = base64.b64encode(salt).decode("ascii")
    key_b64 = base64.b64encode(derived).decode("ascii")
    return f"$argon2id$v=19$m={ARGON2_MEMORY_COST},t={ARGON2_TIME_COST},p={ARGON2_PARALLELISM}${salt_b64}${key_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano confere com o hash armazenado.

    Suporta hashes Argon2id no formato RFC 9106 (com versão '$argon2id$v=19$m=...' ou sem versão)
    e extrai dinamicamente as iterações (t), custo de memória (m) e paralelismo (p).
    Também suporta fallback de hashes legados.
    """
    if not hashed_password or not plain_password:
        return False

    parts = hashed_password.split("$")

    # Hashes Argon2id: ['', 'argon2id', ...]
    if len(parts) >= 5 and parts[1] == "argon2id":
        try:
            if parts[2].startswith("v="):
                # Com versão: ['', 'argon2id', 'v=19', 'm=65536,t=3,p=4', '<salt>', '<key>']
                params_str = parts[3]
                salt_str = parts[4]
                key_str = parts[5]
            else:
                # Sem versão: ['', 'argon2id', 'm=65536,t=2,p=4', '<salt>', '<key>']
                params_str = parts[2]
                salt_str = parts[3]
                key_str = parts[4]

            salt = _b64decode_unpadded(salt_str)
            expected_key = _b64decode_unpadded(key_str)

            # Extrai os parâmetros dinâmicos t, m, p
            params: dict[str, int] = {}
            for item in params_str.split(","):
                if "=" in item:
                    k, v = item.split("=", 1)
                    if v.isdigit():
                        params[k] = int(v)

            time_cost = params.get("t", ARGON2_TIME_COST)
            memory_cost = params.get("m", ARGON2_MEMORY_COST)
            parallelism = params.get("p", ARGON2_PARALLELISM)

            kdf = Argon2id(
                salt=salt,
                length=len(expected_key),
                iterations=time_cost,
                lanes=parallelism,
                memory_cost=memory_cost,
            )
            kdf.verify(plain_password.encode("utf-8"), expected_key)
            return True
        except (InvalidKey, ValueError, TypeError):
            return False

    # Fallback para hashes gerados com SHA-256 ou texto de desenvolvimento
    if hashed_password.startswith("$sha256$"):
        parts_sha = hashed_password.split("$")
        if len(parts_sha) == 4:
            salt_s = parts_sha[2]
            expected = parts_sha[3]
            calc = hashlib.sha256((salt_s + plain_password).encode("utf-8")).hexdigest()
            return secrets.compare_digest(calc, expected)

    return False


def hash_token(token: str) -> str:
    """Retorna o hash SHA-256 em hexadecimal (64 caracteres) de um token ou código de verificação."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def generate_verification_code(length: int = 6) -> str:
    """Gera um código numérico aleatório de alta entropia para envio por e-mail (ex: 489213)."""
    digits = "0123456789"
    return "".join(secrets.choice(digits) for _ in range(length))


def mask_email(email: str) -> str:
    """Censura parcialmente o e-mail para exibição segura na recuperação de conta.

    Exemplo: 'sophia.designer@gmail.com' -> 'so******@g******.com'
    """
    if "@" not in email:
        return email

    user, domain = email.split("@", 1)
    if len(user) <= 2:
        masked_user = user + "*" * 4
    else:
        masked_user = user[:2] + "*" * (len(user) - 2)

    domain_parts = domain.split(".", 1)
    if len(domain_parts) == 2:
        d_name, d_ext = domain_parts
        if len(d_name) <= 1:
            masked_domain = d_name + "*" * 3 + "." + d_ext
        else:
            masked_domain = d_name[0] + "*" * (len(d_name) - 1) + "." + d_ext
    else:
        masked_domain = domain[0] + "*" * (len(domain) - 1)

    return f"{masked_user}@{masked_domain}"


def clean_digits(val: str | None) -> str:
    """Remove qualquer caractere não numérico de CPF, CEP e telefone."""
    if not val:
        return ""
    return re.sub(r"\D", "", val)


def validate_password_strength(password: str, email: str = "") -> tuple[bool, str | None]:
    """Valida a senha conforme as regras de negócio da Seção 2.3 do projeto.

    - Mínimo de 12 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 letra minúscula
    - Pelo menos 1 número
    - Pelo menos 1 símbolo especial
    - Não pode ser igual ao e-mail
    """
    if not password or len(password) < 12:
        return False, "A senha deve conter no mínimo 12 caracteres."

    if email and password.strip().lower() == email.strip().lower():
        return False, "A senha não pode ser igual ao e-mail cadastrado."

    if not re.search(r"[A-Z]", password):
        return False, "A senha deve conter pelo menos uma letra maiúscula."

    if not re.search(r"[a-z]", password):
        return False, "A senha deve conter pelo menos uma letra minúscula."

    if not re.search(r"[0-9]", password):
        return False, "A senha deve conter pelo menos um número."

    if not re.search(r"[^A-Za-z0-9]", password):
        return False, "A senha deve conter pelo menos um caractere especial/símbolo."

    return True, None
