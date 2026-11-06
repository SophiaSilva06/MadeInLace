from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.usuario import Usuario


def obter_usuario_logado(request: Request, db: Session | None) -> Usuario | None:
    """Extrai com segurança o usuário autenticado da sessão a partir do cookie HttpOnly user_id."""
    if db is None:
        return None
    user_id_cookie = request.cookies.get("user_id")
    if not user_id_cookie:
        return None
    try:
        user_id = int(user_id_cookie)
    except (ValueError, TypeError):
        return None

    usuario = db.get(Usuario, user_id)
    if usuario and usuario.ATIVO:
        return usuario
    return None
