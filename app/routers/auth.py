from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.templates import templates
from app.schemas.auth import (
    RecuperarEmailPayload,
    RedefinirSenhaPayload,
    RegistroPayload,
    SolicitarRecuperacaoPayload,
    ValidarCodigoPayload,
    VerificarUnicidadePayload,
)
from app.services.auth_service import AuthService

router = APIRouter(tags=["Autenticação"])


# ==============================================================================
# 1. PÁGINA DE LOGIN E AUTENTICAÇÃO (13_MadeInLace Login)
# ==============================================================================


def _sanitizar_redirect(target: str | None) -> str:
    """Valida e sanitiza o URL de redirecionamento para evitar Open Redirect e loops em rotas de auth."""
    if not target or not isinstance(target, str):
        return "/"
    clean = target.strip()
    if (
        not clean.startswith("/")
        or clean.startswith("//")
        or clean.startswith("/login")
        or clean.startswith("/registro")
        or clean.startswith("/logout")
    ):
        return "/"
    return clean


@router.get("/login", response_class=HTMLResponse)
def get_login(
    request: Request,
    email: Annotated[str | None, Query(description="E-mail pré-preenchido vindo do formulário do footer")] = None,
    next: Annotated[str | None, Query(description="URL de destino após autenticação")] = None,
    next_url: Annotated[str | None, Query(description="URL de destino alternativa")] = None,
    promo: Annotated[str | None, Query(description="Cupom ou condição promocional")] = None,
    error: Annotated[bool, Query(description="Indica erro de credenciais inválidas")] = False,
    registered: Annotated[bool, Query(description="Indica cadastro recém-concluído")] = False,
) -> HTMLResponse:
    """Renderiza a página de login pré-preenchendo o e-mail vindo do footer se fornecido."""
    dest_url = _sanitizar_redirect(next or next_url)
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "email_preenchido": email or "",
            "next_url": dest_url,
            "promo_ativa": promo == "10off",
            "error_login": error,
            "registered": registered,
        },
    )


@router.post("/login")
def post_login(
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
    email: Annotated[str | None, Form()] = None,
    password: Annotated[str | None, Form()] = None,
    next_url: Annotated[str | None, Form()] = None,
) -> Any:
    """Processa o login tanto por submissão clássica de formulário quanto por payload JSON / AJAX."""
    identificador = email or ""
    senha = password or ""

    # Determina o destino pós-login com fallback ordenado
    query_params = request.query_params if "query_string" in request.scope else {}
    candidate = (
        next_url
        or query_params.get("next")
        or query_params.get("next_url")
        or "/"
    )
    redirect_target = _sanitizar_redirect(candidate)

    content_type = request.headers.get("content-type", "")
    accept_header = request.headers.get("accept", "")
    x_req_header = request.headers.get("x-requested-with", "")
    is_ajax = (
        "application/json" in content_type
        or "application/json" in accept_header
        or x_req_header == "XMLHttpRequest"
    )

    usuario = AuthService.authenticate_user(db, identifier=identificador, password=senha)

    if not usuario:
        if is_ajax:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": "email ou senha estão errados"},
            )
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "email_preenchido": identificador,
                "next_url": redirect_target,
                "promo_ativa": False,
                "error_login": True,
                "registered": False,
            },
            status_code=status.HTTP_200_OK,
        )

    # Login bem-sucedido
    if is_ajax:
        json_resp = JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"success": True, "redirect_url": redirect_target, "user_id": usuario.ID},
        )
        json_resp.set_cookie(
            key="user_id",
            value=str(usuario.ID),
            httponly=True,
            samesite="lax",
            max_age=86400 * 7,
        )
        return json_resp

    redirecionamento = RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)
    redirecionamento.set_cookie(
        key="user_id",
        value=str(usuario.ID),
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return redirecionamento


@router.get("/logout")
def get_logout() -> RedirectResponse:
    """Encerra a sessão do usuário removendo o cookie de autenticação."""
    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(key="user_id")
    return resp


# ==============================================================================
# 2. FLUXO DE RECUPERAÇÃO DE CONTA E SENHA (19, 24 e 30)
# ==============================================================================


@router.post("/auth/recuperar-senha/solicitar")
def solicitar_recuperacao_senha(
    payload: SolicitarRecuperacaoPayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Modal 1 (19_MadeInLace Recuperacao): Envia código de 6 dígitos para o e-mail informado."""
    sucesso, code, expira_segundos = AuthService.request_password_recovery(db, email=payload.email)
    return {
        "success": sucesso,
        "message": "Se o e-mail estiver cadastrado, as instruções foram enviadas.",
        "timer": expira_segundos,
        "expira_em_segundos": expira_segundos,
        "debug_code": code,
    }


@router.post("/auth/recuperar-senha/validar")
def validar_codigo_recuperacao(
    payload: ValidarCodigoPayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Modal 1 (19_MadeInLace Recuperacao): Valida o código para liberar a tela de nova senha."""
    valido = AuthService.verify_recovery_code(db, email=payload.email, code=payload.codigo)
    if not valido:
        return {"success": False, "message": "Código de recuperação inválido ou expirado."}
    return {"success": True, "message": "Código validado com sucesso."}


@router.post("/auth/recuperar-senha/redefinir")
def redefinir_senha(
    payload: RedefinirSenhaPayload,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Modal 2 (24_MadeInLace Recuperacao2): Atualiza a senha e autentica o usuário."""
    sucesso, erro = AuthService.reset_password(
        db,
        email=payload.email,
        code=payload.codigo,
        new_password=payload.nova_senha,
        confirm_password=payload.confirmar_senha,
    )
    if not sucesso:
        return {"success": False, "message": erro or "Falha ao redefinir a senha."}

    # Autentica e redireciona para a Home
    usuario = AuthService.authenticate_user(db, identifier=payload.email, password=payload.nova_senha)
    if usuario:
        response.set_cookie(
            key="user_id",
            value=str(usuario.ID),
            httponly=True,
            samesite="lax",
            max_age=86400 * 7,
        )

    return {"success": True, "redirect_url": "/"}


@router.post("/auth/recuperar-email")
def recuperar_email_por_cpf(
    payload: RecuperarEmailPayload,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Modal 3 (30_MadeInLace Recuperacao1.1): Busca e-mail censurado por CPF e Data de Nascimento."""
    masked_email, user = AuthService.find_masked_email_by_cpf_nasc(db, cpf=payload.cpf, nascimento=payload.nascimento)

    if not masked_email or not user:
        return {
            "success": False,
            "message": "Nenhum cadastro localizado com o CPF e data de nascimento informados.",
        }

    # Caso o cliente já tenha inserido a senha para fazer login direto
    if payload.senha:
        auth_user = AuthService.authenticate_user(db, identifier=user.EMAIL, password=payload.senha)
        if not auth_user:
            return {
                "success": False,
                "message": "Senha incorreta para a conta localizada.",
                "masked_email": masked_email,
            }
        response.set_cookie(
            key="user_id",
            value=str(auth_user.ID),
            httponly=True,
            samesite="lax",
            max_age=86400 * 7,
        )
        return {"success": True, "redirect_url": "/perfil", "masked_email": masked_email}

    return {"success": True, "masked_email": masked_email}


# ==============================================================================
# 3. PÁGINA DE CADASTRO E FLUXO DE VERIFICAÇÃO DE EMAIL (3, 31 e Autenticar_Email)
# ==============================================================================


@router.get("/registro", response_class=HTMLResponse)
@router.get("/cadastro", response_class=HTMLResponse)
def get_registro(
    request: Request,
    email: Annotated[str | None, Query(description="E-mail inicial se fornecido")] = None,
) -> HTMLResponse:
    """Renderiza a página de cadastro do usuário (3_MadeInLace Registro1.png)."""
    return templates.TemplateResponse(
        request=request,
        name="auth/registro.html",
        context={
            "email_inicial": email or "",
        },
    )


@router.post("/auth/verificar-unicidade")
def verificar_unicidade(
    payload: VerificarUnicidadePayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, bool]:
    """Verifica em tempo real se o e-mail ou CPF já estão em uso."""
    return AuthService.check_uniqueness(db, email=payload.email, cpf=payload.cpf)


@router.post("/auth/enviar-codigo-cadastro")
def enviar_codigo_cadastro(
    payload: SolicitarRecuperacaoPayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Modal 5 (MadeInLace_Autenticar_Email): Envia código de autenticação para a tabela VERIFICACAO_EMAIL."""
    sucesso, code, expira_segundos = AuthService.send_registration_email_code(db, email=payload.email)
    return {
        "success": sucesso,
        "message": f"Código de verificação enviado para {payload.email}.",
        "timer": expira_segundos,
        "expira_em_segundos": expira_segundos,
        "debug_code": code,
    }


@router.post("/auth/validar-codigo-cadastro")
def validar_codigo_cadastro(
    payload: ValidarCodigoPayload,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Modal 5: Compara o código informado com o hash gravado na tabela VERIFICACAO_EMAIL."""
    valido = AuthService.verify_registration_email_code(db, email=payload.email, code=payload.codigo)
    if not valido:
        return {"success": False, "message": "Código de verificação inválido ou expirado."}
    return {"success": True, "message": "E-mail validado com sucesso!"}


@router.post("/registro")
def post_registro(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    email: Annotated[str | None, Form()] = None,
    cpf: Annotated[str | None, Form()] = None,
    nome: Annotated[str | None, Form()] = None,
    sobrenome: Annotated[str | None, Form()] = None,
    senha: Annotated[str | None, Form()] = None,
    nascimento: Annotated[str | None, Form()] = None,
    telefone: Annotated[str | None, Form()] = None,
    codigo_verificacao: Annotated[str | None, Form()] = None,
    enderecos_json: Annotated[str | None, Form()] = None,
) -> Any:
    """Conclui o registro criando usuário e endereços na mesma transação."""
    content_type = request.headers.get("content-type", "")

    # Suporte a JSON payload
    if "application/json" in content_type:
        # Quando a requisição é feita via fetch em formato JSON
        pass

    # Monta lista de endereços (o cliente deve cadastrar seu próprio endereço)
    lista_enderecos: list[dict[str, Any]] = []
    if enderecos_json:
        try:
            parsed = json.loads(enderecos_json)
            if isinstance(parsed, list):
                lista_enderecos = parsed
        except json.JSONDecodeError:
            pass

    dados_usuario = {
        "email": email,
        "cpf": cpf,
        "nome": nome,
        "sobrenome": sobrenome,
        "senha": senha,
        "nascimento": nascimento,
        "telefone": telefone,
    }

    sucesso, erro, _ = AuthService.register_user(
        db=db,
        dados_usuario=dados_usuario,
        enderecos=lista_enderecos,
        codigo_verificacao=codigo_verificacao or "",
    )

    if not sucesso:
        if "application/json" in content_type:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"success": False, "message": erro or "Erro ao concluir cadastro."},
            )
        return templates.TemplateResponse(
            request=request,
            name="auth/registro.html",
            context={"email_inicial": email or "", "erro": erro},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Redireciona para o login com aviso de cadastro realizado
    redirect_target = "/login?registered=1"
    if "application/json" in content_type:
        return JSONResponse(content={"success": True, "redirect_url": redirect_target})

    return RedirectResponse(url=redirect_target, status_code=status.HTTP_303_SEE_OTHER)


@router.post("/api/registro")
def post_api_registro(
    payload: RegistroPayload,
    db: Annotated[Session, Depends(get_db)],
) -> JSONResponse:
    """Endpoint REST tipado para criação completa do cadastro via API."""
    dados_usuario = {
        "email": payload.email,
        "cpf": payload.cpf,
        "nome": payload.nome,
        "sobrenome": payload.sobrenome,
        "senha": payload.senha,
        "nascimento": payload.nascimento,
        "telefone": payload.telefone,
    }
    enderecos_dict = [end.model_dump() for end in payload.enderecos]

    sucesso, erro, user = AuthService.register_user(
        db=db,
        dados_usuario=dados_usuario,
        enderecos=enderecos_dict,
        codigo_verificacao=payload.codigo_verificacao,
    )
    if not sucesso or not user:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "message": erro or "Falha no cadastro."},
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"success": True, "redirect_url": "/login?registered=1", "user_id": user.ID},
    )
