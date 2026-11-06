from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import obter_usuario_logado as _obter_usuario_sessao
from app.core.security import clean_digits
from app.core.templates import templates
from app.models.usuario import EnderecoUsuario
from app.schemas.perfil import (
    AtualizarPerfilPayload,
    EnderecoPerfilPayload,
    ReembolsoPayload,
    SolicitarCodigoEmailPayload,
    TrocaPayload,
    ValidarCodigoEmailPayload,
)
from app.services.perfil_service import PerfilService

router = APIRouter(prefix="/perfil", tags=["Perfil"])


@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
@router.get("/{secao}", response_class=HTMLResponse)
def get_perfil(
    request: Request,
    secao: str = "dados",
    db: Annotated[Session | None, Depends(get_db)] = None,
) -> Response:
    """Renderiza a página visual completa do Perfil e gerencia controle de acesso por aba."""
    usuario = _obter_usuario_sessao(request, db)

    # Seções públicas de apoio (Guia de Tamanhos e Contatos)
    secoes_publicas = {"tamanhos", "contatos"}
    if not usuario and secao not in secoes_publicas:
        return RedirectResponse(url="/login?next=/perfil", status_code=status.HTTP_303_SEE_OTHER)

    perfil_dados: dict[str, Any] = {}
    pedidos_dados: dict[str, Any] = {"pedidos": [], "total": 0, "tem_mais": False}
    trocas_dados: dict[str, Any] = {"itens": [], "total": 0, "tem_mais": False}

    if usuario and db is not None:
        cookie_principal = request.cookies.get("endereco_principal_id")
        principal_id = int(cookie_principal) if cookie_principal and cookie_principal.isdigit() else None

        p_info = PerfilService.obter_perfil_usuario(db, usuario.ID, endereco_principal_id=principal_id)
        if p_info:
            perfil_dados = p_info

        pedidos_dados = PerfilService.listar_pedidos_usuario(
            db, usuario.ID, filtro="todos", limit=2, offset=0
        )
        trocas_dados = PerfilService.listar_trocas_e_reembolsos(
            db, usuario.ID, limit=2, offset=0
        )

    return templates.TemplateResponse(
        request=request,
        name="perfil/index.html",
        context={
            "secao_ativa": secao,
            "usuario": usuario,
            "current_user": usuario,
            "perfil": perfil_dados,
            "pedidos_iniciais": pedidos_dados.get("pedidos", []),
            "tem_mais_pedidos": pedidos_dados.get("tem_mais", False),
            "trocas_iniciais": trocas_dados.get("itens", []),
            "tem_mais_trocas": trocas_dados.get("tem_mais", False),
        },
    )


@router.post("/salvar")
def post_salvar_perfil(
    payload: AtualizarPerfilPayload,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Persiste todas as alterações de nome, sobrenome, telefone, senha, e-mail e endereços."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    sucesso, erro = PerfilService.salvar_informacoes_completas(db, usuario.ID, payload)
    if not sucesso:
        return {"success": False, "message": erro or "Falha ao salvar as informações."}

    if payload.endereco_principal_id and response is not None:
        response.set_cookie(
            key="endereco_principal_id",
            value=str(payload.endereco_principal_id),
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,
        )

    return {"success": True, "message": "Informações atualizadas com sucesso!"}


@router.post("/enderecos/definir-principal/{endereco_id}")
def definir_endereco_principal_api(
    endereco_id: int,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Marca o endereço informado como principal via cookie seguro de sessão."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    perfil = PerfilService.obter_perfil_usuario(db, usuario.ID)
    if not perfil or not any(e["id"] == endereco_id for e in perfil["enderecos"]):
        return {"success": False, "message": "Endereço não localizado."}

    if response is not None:
        response.set_cookie(
            key="endereco_principal_id",
            value=str(endereco_id),
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,
        )

    return {
        "success": True,
        "message": "Endereço principal atualizado com sucesso!",
        "principal_id": endereco_id,
    }


@router.post("/enderecos/remover/{endereco_id}")
def remover_endereco_api(
    endereco_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Inativa o endereço solicitado preservando integridade referencial se já usado em pedidos."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    sucesso, erro = PerfilService.remover_endereco(db, usuario.ID, endereco_id)
    if not sucesso:
        return {"success": False, "message": erro or "Falha ao remover endereço."}

    return {"success": True, "message": "Endereço removido com sucesso!"}


@router.post("/enderecos/salvar")
def salvar_novo_endereco_perfil_api(
    payload: EnderecoPerfilPayload,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Salva um novo endereço ou atualiza existente no modal 'Modificar Endereços' do perfil."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    sucesso, erro = PerfilService.salvar_endereco(db, usuario.ID, payload)
    if not sucesso:
        return {"success": False, "message": erro or "Falha ao cadastrar endereço."}

    # Busca o endereço ativo recém-salvo
    cep_limpo = clean_digits(payload.cep)
    end = db.scalars(
        select(EnderecoUsuario)
        .where(
            EnderecoUsuario.FK_USUARIO == usuario.ID,
            EnderecoUsuario.ATIVO.is_(True),
            EnderecoUsuario.CEP == cep_limpo,
            EnderecoUsuario.NUMERO == payload.numero.strip(),
            EnderecoUsuario.NOME == payload.nome.strip(),
        )
        .order_by(EnderecoUsuario.ID.desc())
    ).first()

    if not end:
        return {"success": False, "message": "Endereço cadastrado não localizado."}

    if response is not None:
        response.set_cookie(
            key="endereco_principal_id",
            value=str(end.ID),
            httponly=True,
            samesite="lax",
            max_age=86400 * 30,
        )

    return {
        "success": True,
        "message": "Endereço salvo com sucesso!",
        "endereco": {
            "id": end.ID,
            "nome": end.NOME,
            "cep": f"{end.CEP[:5]}-{end.CEP[5:]}" if len(end.CEP) == 8 else end.CEP,
            "logradouro": end.LOGRADOURO,
            "numero": end.NUMERO,
            "complemento": end.COMPLEMENTO or "",
            "bairro": end.BAIRRO,
            "cidade": end.CIDADE,
            "estado": end.ESTADO,
            "is_principal": True,
        },
    }


@router.post("/email/enviar-codigo-atual")
def enviar_codigo_email_atual(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Envia código de 6 dígitos numéricos para o e-mail cadastrado atualmente."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    sucesso, cod, expira_segundos = PerfilService.enviar_codigo_verificacao_email(db, usuario.EMAIL)
    return {
        "success": sucesso,
        "message": f"Código enviado com sucesso para {usuario.EMAIL}.",
        "timer": expira_segundos,
        "expira_em_segundos": expira_segundos,
        "debug_code": cod,
    }


@router.post("/email/enviar-codigo-novo")
def enviar_codigo_email_novo(
    payload: SolicitarCodigoEmailPayload,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Envia código de 6 dígitos numéricos para o novo e-mail fornecido."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    sucesso, cod, expira_segundos = PerfilService.enviar_codigo_verificacao_email(db, payload.email)
    return {
        "success": sucesso,
        "message": f"Código enviado com sucesso para {payload.email}.",
        "timer": expira_segundos,
        "expira_em_segundos": expira_segundos,
        "debug_code": cod,
    }


@router.post("/email/validar")
def validar_troca_email_api(
    payload: ValidarCodigoEmailPayload,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Valida ambos os códigos de e-mail e senha atual antes de consolidar o salvamento."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    valido, erro = PerfilService.validar_troca_email(
        db,
        usuario_id=usuario.ID,
        email_atual=payload.email_atual,
        codigo_atual=payload.codigo_atual,
        novo_email=payload.novo_email,
        codigo_novo=payload.codigo_novo,
        senha_atual=payload.senha_atual,
    )
    if not valido:
        return {"success": False, "message": erro or "código de verificação inválido"}

    return {"success": True, "message": "Códigos validados com sucesso!"}


@router.get("/api/pedidos")
def listar_pedidos_api(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    filtro: Annotated[str, Query()] = "todos",
    limit: Annotated[int, Query()] = 2,
    offset: Annotated[int, Query()] = 0,
) -> dict[str, Any]:
    """Retorna listagem de pedidos paginados de 2 em 2 com suporte a filtros de status."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado.", "pedidos": [], "tem_mais": False}

    resultado = PerfilService.listar_pedidos_usuario(
        db, usuario.ID, filtro=filtro, limit=limit, offset=offset
    )
    return resultado


@router.get("/api/item-venda/{item_id}")
def obter_detalhes_item_venda(
    item_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Any:
    """Busca detalhes do produto para o modal de inspeção (imagem 23_MadeInLace Perfil2.1)."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"success": False, "message": "Usuário não autenticado."},
        )

    detalhes = PerfilService.obter_item_venda_detalhes(db, item_id, usuario.ID)
    if not detalhes:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "message": "Item de venda não localizado."},
        )

    return detalhes


@router.post("/api/troca")
def solicitar_troca_api(
    payload: TrocaPayload,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Cria solicitações de troca gerando múltiplos registros individuais se quantidade > 1."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    sucesso, erro = PerfilService.solicitar_troca(db, usuario.ID, payload)
    if not sucesso:
        return {"success": False, "message": erro or "Falha ao registrar solicitação de troca."}

    return {"success": True, "message": "Solicitação de troca registrada com sucesso!"}


@router.post("/api/reembolso")
def solicitar_reembolso_api(
    payload: ReembolsoPayload,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Cria solicitações de reembolso gerando múltiplos registros individuais se quantidade > 1."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado."}

    sucesso, erro = PerfilService.solicitar_reembolso(db, usuario.ID, payload)
    if not sucesso:
        return {"success": False, "message": erro or "Falha ao registrar solicitação de reembolso."}

    return {"success": True, "message": "Solicitação de reembolso registrada com sucesso!"}


@router.get("/api/trocas-reembolsos")
def listar_trocas_reembolsos_api(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query()] = 2,
    offset: Annotated[int, Query()] = 0,
) -> dict[str, Any]:
    """Retorna listagem unificada de trocas e reembolsos paginados de 2 em 2."""
    usuario = _obter_usuario_sessao(request, db)
    if not usuario:
        return {"success": False, "message": "Usuário não autenticado.", "itens": [], "tem_mais": False}

    resultado = PerfilService.listar_trocas_e_reembolsos(
        db, usuario.ID, limit=limit, offset=offset
    )
    return resultado
