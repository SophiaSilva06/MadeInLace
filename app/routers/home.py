from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import obter_usuario_logado
from app.core.templates import templates
from app.services.carrinho_service import CarrinhoService
from app.services.home_service import HomeService

router = APIRouter(tags=["Home"])


@router.get("/", response_class=HTMLResponse)
@router.get("/home", response_class=HTMLResponse)
def get_home(request: Request, db: Annotated[Session, Depends(get_db)]) -> HTMLResponse:
    """Rota fina para renderizar a Home page do MadeInLace."""
    home_data = HomeService.get_home_data(db)
    current_user = obter_usuario_logado(request, db)
    cart_count = 0
    if current_user:
        carrinho_dto = CarrinhoService.obter_carrinho_dto(db, current_user.ID)
        cart_count = carrinho_dto.quantidade_total

    return templates.TemplateResponse(
        request=request,
        name="home/index.html",
        context={
            "home": home_data,
            "linhas": home_data.linhas,
            "produtos_promocao": home_data.produtos_promocao,
            "produtos_best_sellers": home_data.produtos_best_sellers,
            "linhas_recentes": home_data.linhas_recentes,
            "current_user": current_user,
            "cart_count": cart_count,
        },
    )
