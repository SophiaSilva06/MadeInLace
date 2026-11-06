from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers.auth import router as auth_router
from app.routers.carrinho import router as carrinho_router
from app.routers.catalogo import router as catalogo_router
from app.routers.checkout import router as checkout_router
from app.routers.home import router as home_router
from app.routers.perfil import router as perfil_router

# Diretório base e pasta de assets estáticos
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

# Montagem do diretório de arquivos estáticos (/static)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Registro dos routers da aplicação
app.include_router(home_router)
app.include_router(catalogo_router)
app.include_router(auth_router)
app.include_router(carrinho_router)
app.include_router(checkout_router)
app.include_router(perfil_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Endpoint de verificação de integridade da aplicação."""
    return {"status": "ok", "app": settings.app_name}
