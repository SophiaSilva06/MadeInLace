from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import obter_usuario_logado as _obter_usuario_logado
from app.core.templates import templates
from app.schemas.carrinho import (
    AdicionarItemPayload,
    AtualizarQuantidadePayload,
    RemoverItemPayload,
)
from app.services.carrinho_service import CarrinhoService

router = APIRouter(tags=["Carrinho"])


@router.get("/carrinho", response_class=HTMLResponse)
def get_carrinho(
    request: Request,
    db: Annotated[Session | None, Depends(get_db)] = None,
    aviso: str | None = None,
) -> HTMLResponse:
    """Renderiza a página visual completa da sacola/carrinho de compras."""
    usuario = _obter_usuario_logado(request, db) if db is not None else None
    if usuario and db is not None:
        carrinho_dto = CarrinhoService.obter_carrinho_dto(db, usuario.ID)
        itens = carrinho_dto.itens
        subtotal = carrinho_dto.subtotal
        total = carrinho_dto.total
        frete_gratis = carrinho_dto.frete_gratis
        cart_count = carrinho_dto.quantidade_total
    else:
        carrinho_dto = CarrinhoService.obter_carrinho_anonimo_dto()  # type: ignore[assignment]
        itens = []
        subtotal = 0.0
        total = 0.0
        frete_gratis = False
        cart_count = 0

    return templates.TemplateResponse(
        request=request,
        name="carrinho/index.html",
        context={
            "carrinho": carrinho_dto,
            "itens": itens,
            "subtotal": subtotal,
            "total": total,
            "frete_gratis": frete_gratis,
            "cart_count": cart_count,
            "current_user": usuario,
            "aviso": aviso,
        },
    )


@router.get("/api/carrinho")
def api_get_carrinho(
    request: Request, db: Annotated[Session, Depends(get_db)]
) -> JSONResponse:
    """Endpoint REST que retorna o estado atualizado do carrinho ativo do usuário em JSON."""
    usuario = _obter_usuario_logado(request, db)
    if not usuario:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=CarrinhoService.obter_carrinho_anonimo_dto(),
        )

    dto = CarrinhoService.obter_carrinho_dto(db, usuario.ID)
    return JSONResponse(status_code=status.HTTP_200_OK, content=dto.model_dump())


@router.post("/api/carrinho/adicionar")
def api_adicionar_item(
    payload: AdicionarItemPayload,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    referer: Annotated[str | None, Header()] = None,
) -> JSONResponse:
    """Adiciona produto/variação ao carrinho ativo.

    Exige login prévio (Seção 9 das Regras de Negócio).
    """
    usuario = _obter_usuario_logado(request, db)
    if not usuario:
        next_path = referer or "/produtos"
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "autenticado": False,
                "message": "Faça login para adicionar produtos à sua sacola de compras.",
                "login_url": f"/login?next={next_path}",
            },
        )

    try:
        carrinho_dto = CarrinhoService.adicionar_item(
            db=db,
            usuario_id=usuario.ID,
            produto_id=payload.produto_id,
            variacao_id=payload.variacao_id,
            tamanho=payload.tamanho,
            cor=payload.cor,
            quantidade=payload.quantidade,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Produto adicionado com sucesso!",
                "carrinho": carrinho_dto.model_dump(),
            },
        )
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(e)},
        )


@router.post("/api/carrinho/atualizar-quantidade")
def api_atualizar_quantidade(
    payload: AtualizarQuantidadePayload,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """Modifica a quantidade de um item no carrinho (1 a 10)."""
    usuario = _obter_usuario_logado(request, db)
    if not usuario:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Sessão expirada. Faça login novamente."},
        )

    try:
        carrinho_dto = CarrinhoService.atualizar_quantidade(
            db=db,
            usuario_id=usuario.ID,
            item_id=payload.item_id,
            nova_quantidade=payload.quantidade,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "carrinho": carrinho_dto.model_dump(),
            },
        )
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(e)},
        )


@router.post("/api/carrinho/remover")
def api_remover_item(
    payload: RemoverItemPayload,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """Remove o item e todas as suas unidades do carrinho."""
    usuario = _obter_usuario_logado(request, db)
    if not usuario:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Sessão expirada. Faça login novamente."},
        )

    try:
        carrinho_dto = CarrinhoService.remover_item(
            db=db,
            usuario_id=usuario.ID,
            item_id=payload.item_id,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Item removido do carrinho.",
                "carrinho": carrinho_dto.model_dump(),
            },
        )
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(e)},
        )
