from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import obter_usuario_logado as _obter_usuario_sessao
from app.core.templates import templates
from app.schemas.checkout import FinalizarCompraPayload, SalvarEnderecoCheckoutPayload
from app.services.checkout_service import CheckoutService
from app.services.perfil_service import PerfilService

router = APIRouter(tags=["Checkout"])


@router.get("/checkout", response_class=HTMLResponse)
@router.get("/pagamento", response_class=HTMLResponse)
def get_checkout_page(
    request: Request,
    endereco_id: int | None = Query(default=None),
    db: Annotated[Session | None, Depends(get_db)] = None,
) -> Response:
    """Renderiza a página visual completa de pagamento do Made In Lace (11_MadeInLace Pagamento)."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario or db is None:
        return RedirectResponse(
            url="/login?next=/checkout",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    try:
        resumo = CheckoutService.obter_resumo_checkout(
            db=db,
            usuario_id=usuario.ID,
            endereco_id_selecionado=endereco_id,
        )
    except ValueError:
        # Carrinho vazio ou sem itens válidos: redireciona para o carrinho com aviso
        return RedirectResponse(
            url="/carrinho?aviso=vazio",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return templates.TemplateResponse(
        request=request,
        name="checkout/pagamento.html",
        context={
            "resumo": resumo,
            "usuario": usuario,
            "current_user": usuario,
        },
    )


@router.post("/checkout/finalizar")
@router.post("/pagamento/finalizar")
def finalizar_compra_api(
    request: Request,
    payload: FinalizarCompraPayload | None = None,
    db: Annotated[Session | None, Depends(get_db)] = None,
) -> Any:
    """Finaliza a compra simulada, persiste a VENDA no banco com o método selecionado e redireciona."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario or db is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Usuário não autenticado."},
        )

    # Suporta payload JSON direto
    if not payload:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Endereço e método de pagamento são obrigatórios.",
            },
        )

    endereco_id = payload.endereco_id
    metodo_pagamento = payload.metodo_pagamento

    try:
        venda = CheckoutService.finalizar_compra(
            db=db,
            usuario_id=usuario.ID,
            endereco_id=endereco_id,
            metodo_pagamento=metodo_pagamento,
        )
        return {
            "success": True,
            "redirect_url": "/perfil/pedidos",
            "venda_id": venda.ID,
        }
    except ValueError as e:
        msg = str(e)
        if "itens no carrinho" in msg.lower() or "vazio" in msg.lower():
            msg = "Adicione Produtos Para Ir Ao Pagamento"
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": msg},
        )


@router.post("/checkout/endereco")
@router.post("/pagamento/endereco")
def salvar_endereco_checkout_api(
    request: Request,
    payload: SalvarEnderecoCheckoutPayload,
    db: Annotated[Session | None, Depends(get_db)] = None,
) -> Any:
    """Salva um novo endereço ou atualiza um existente a partir do modal 'Modificar Endereços'."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario or db is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Usuário não autenticado."},
        )

    try:
        novo_end = CheckoutService.salvar_endereco_checkout(
            db=db,
            usuario_id=usuario.ID,
            payload=payload,
        )

        # Tenta recalcular o checkout se houver carrinho ativo
        resumo_atualizado = None
        try:
            resumo_atualizado = CheckoutService.obter_resumo_checkout(
                db=db,
                usuario_id=usuario.ID,
                endereco_id_selecionado=novo_end.ID,
            )
        except ValueError:
            resumo_atualizado = None

        return {
            "success": True,
            "endereco": {
                "id": novo_end.ID,
                "nome": novo_end.NOME,
                "cep": f"{novo_end.CEP[:5]}-{novo_end.CEP[5:]}" if len(novo_end.CEP) == 8 else novo_end.CEP,
                "logradouro": novo_end.LOGRADOURO,
                "numero": novo_end.NUMERO,
                "complemento": novo_end.COMPLEMENTO or "",
                "bairro": novo_end.BAIRRO,
                "cidade": novo_end.CIDADE,
                "estado": novo_end.ESTADO,
            },
            "resumo": resumo_atualizado,
        }
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(e)},
        )


@router.get("/checkout/recalcular")
@router.get("/pagamento/recalcular")
def recalcular_checkout_api(
    request: Request,
    endereco_id: int = Query(...),
    db: Annotated[Session | None, Depends(get_db)] = None,
) -> Any:
    """Recalcula frete e totais dinamicamente quando o usuário altera a seleção do endereço."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario or db is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Usuário não autenticado."},
        )

    try:
        resumo = CheckoutService.obter_resumo_checkout(
            db=db,
            usuario_id=usuario.ID,
            endereco_id_selecionado=endereco_id,
        )
        return {"success": True, "resumo": resumo}
    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": str(e)},
        )


@router.post("/checkout/endereco/remover/{endereco_id}")
def remover_endereco_checkout_api(
    endereco_id: int,
    request: Request,
    db: Annotated[Session | None, Depends(get_db)] = None,
) -> Any:
    """Inativa logicamente o endereço solicitado no modal de checkout garantindo que o último ativo não seja removido."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario or db is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Usuário não autenticado."},
        )

    sucesso, erro = PerfilService.remover_endereco(db, usuario.ID, endereco_id)
    if not sucesso:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": erro or "Falha ao remover endereço."},
        )

    return {"success": True, "message": "Endereço removido com sucesso!"}
