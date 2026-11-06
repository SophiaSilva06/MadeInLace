import math
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import obter_usuario_logado
from app.core.templates import templates
from app.services.carrinho_service import CarrinhoService
from app.services.home_service import HomeService
from app.services.produto_service import ProdutoService

router = APIRouter(tags=["Catálogo e Produtos"])


def _render_catalogo_view(
    request: Request,
    db: Session,
    *,
    titulo_pagina: str,
    tipo_fixo: str | None = None,
    apenas_promocao: bool = False,
    apenas_plus_size: bool = False,
    mostrar_categoria: bool = True,
    mostrar_tamanho_roupa: bool = True,
    mostrar_tamanho_sapato: bool = True,
    q: str | None = None,
    tipo_busca: str | None = None,
    linha: str | None = None,
    nome: str | None = None,
    categorias: list[str] | None = None,
    tamanhos_roupa: list[str] | None = None,
    tamanhos_sapato: list[str] | None = None,
    preco_min: Decimal | None = None,
    preco_max: Decimal | None = None,
    ordenacao: str | None = None,
) -> HTMLResponse:
    """Função central para renderização com SSR e dados completos de filtros."""
    # Normaliza termos de busca
    termo_q = q.strip() if q else None
    linha_filtro = linha.strip() if linha else None
    nome_filtro = nome.strip() if nome else None

    # Se a busca via pesquisa especificou tipo_busca == 'linhas', preenche a linha
    if termo_q and (tipo_busca or "").strip().lower() == "linhas" and not linha_filtro:
        linha_filtro = termo_q
        termo_q = None
    elif termo_q and (tipo_busca or "").strip().lower() == "produtos" and not nome_filtro:
        nome_filtro = termo_q
        termo_q = None

    produtos = ProdutoService.obter_catalogo_detalhado(
        session=db,
        q=nome_filtro or termo_q,
        tipo_busca=tipo_busca,
        linha_nome=linha_filtro,
        tipo=tipo_fixo,
        categorias=categorias,
        apenas_promocao=apenas_promocao,
        apenas_plus_size=apenas_plus_size,
        tamanhos_roupa=tamanhos_roupa,
        tamanhos_sapato=tamanhos_sapato,
        preco_min=preco_min,
        preco_max=preco_max,
        ordenacao=ordenacao or "best_sellers",
    )

    if produtos:
        preco_teto = math.ceil(max(float(p.preco_efetivo) for p in produtos))
    else:
        preco_teto = ProdutoService.obter_preco_maximo(db)

    # Se a listagem for na página geral (/produtos ou /catalogo), o catálogo completo da loja
    # é serializado no JSON para que o cliente possa desmarcar o filtro pré-adicionado pela pesquisa
    # ou por linha e restaurar a lista com todos os produtos (ou demais filtros ativos).
    # Em rotas restritas de teste ou categoria fixa, respeita o escopo da requisição.
    path_atual = request.scope.get("path", request.url.path).split("?")[0]
    if path_atual in ("/produtos", "/catalogo"):
        produtos_base = ProdutoService.obter_catalogo_detalhado(
            session=db,
            tipo=tipo_fixo,
            apenas_promocao=apenas_promocao,
            apenas_plus_size=apenas_plus_size,
            ordenacao=ordenacao or "best_sellers",
        )
    else:
        produtos_base = produtos

    # Serializa produtos para permitir filtragem ultra-rápida e modular no cliente
    produtos_json = [
        {
            "id": p.id,
            "nome": p.nome,
            "descricao": p.descricao or "",
            "tipo": p.tipo,
            "linha_nome": p.linha_nome,
            "preco": float(p.preco),
            "preco_promocional": float(p.preco_promocional) if p.preco_promocional is not None else None,
            "preco_efetivo": float(p.preco_efetivo),
            "porcentagem_promocao": float(p.porcentagem_promocao),
            "tem_promocao": p.tem_promocao,
            "imagem_principal": p.imagem_principal,
            "media_avaliacoes": p.media_avaliacoes,
            "total_avaliacoes": p.total_avaliacoes,
            "is_best_seller": p.is_best_seller,
            "tamanhos": p.tamanhos,
            "data_criacao": p.data_criacao.isoformat() if p.data_criacao else "",
        }
        for p in produtos_base
    ]

    def _url_sem_params(*params_remover: str) -> str:
        raw_qs = request.scope.get("query_string", b"")
        if isinstance(raw_qs, bytes):
            qs_str = raw_qs.decode("latin-1")
        else:
            qs_str = str(raw_qs or "")
        from urllib.parse import parse_qsl, urlencode

        query_items = [(k, v) for k, v in parse_qsl(qs_str) if k not in params_remover]
        nova_query = urlencode(query_items)
        path = request.scope.get("path", request.url.path)
        if nova_query:
            return f"{path}?{nova_query}"
        return path

    context = {
        "titulo_pagina": titulo_pagina,
        "produtos": produtos,
        "produtos_json": produtos_json,
        "total_encontrados": len(produtos),
        "mostrar_categoria": mostrar_categoria,
        "mostrar_tamanho_roupa": mostrar_tamanho_roupa,
        "mostrar_tamanho_sapato": mostrar_tamanho_sapato,
        "mostrar_preco": True,
        "preco_max_loja": preco_teto,
        "linha_ativa": linha_filtro or "",
        "nome_ativo": nome_filtro or "",
        "pesquisa_ativa": termo_q or "",
        "tipo_busca_ativo": tipo_busca or "tudo",
        "ordenacao_ativa": ordenacao or "best_sellers",
        "url_remover_linha": _url_sem_params("linha", "q", "tipo_busca"),
        "url_remover_nome": _url_sem_params("nome", "q", "tipo_busca"),
        "url_remover_pesquisa": _url_sem_params("q", "tipo_busca"),
        # Variáveis legadas para manter compatibilidade com testes existentes
        "termo_busca": termo_q or nome_filtro or "",
        "linha_selecionada": linha_filtro or "",
        "tipo_selecionado": tipo_fixo or "",
        "apenas_promocao": apenas_promocao,
        "linhas_recentes": HomeService.get_linhas_recentes(db, limit=4),
    }

    current_user = obter_usuario_logado(request, db)
    cart_count = 0
    if current_user:
        carrinho_dto = CarrinhoService.obter_carrinho_dto(db, current_user.ID)
        cart_count = carrinho_dto.quantidade_total
    context["current_user"] = current_user
    context["cart_count"] = cart_count

    return templates.TemplateResponse(
        request=request,
        name="catalogo/index.html",
        context=context,
    )


@router.get("/produtos", response_class=HTMLResponse)
@router.get("/catalogo", response_class=HTMLResponse)
def listar_produtos(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(description="Termo de pesquisa por nome ou linha")] = None,
    tipo_busca: Annotated[str | None, Query(description="Tipo de pesquisa: tudo, produtos, linhas")] = None,
    linha: Annotated[str | None, Query(description="Filtrar por nome da linha")] = None,
    nome: Annotated[str | None, Query(description="Filtrar por nome do produto")] = None,
    tipo: Annotated[str | None, Query(description="Filtrar por tipo (roupa, calcado, corset)")] = None,
    promocao: Annotated[bool, Query(description="Filtrar apenas produtos em promoção")] = False,
    ordenacao: Annotated[str | None, Query(description="Ordenação global")] = None,
) -> HTMLResponse:
    """Página de listagem geral com todos os produtos e todos os filtros disponíveis."""
    return _render_catalogo_view(
        request=request,
        db=db,
        titulo_pagina="Todos Produtos",
        tipo_fixo=tipo,
        apenas_promocao=promocao,
        mostrar_categoria=True,
        mostrar_tamanho_roupa=True,
        mostrar_tamanho_sapato=True,
        q=q,
        tipo_busca=tipo_busca,
        linha=linha,
        nome=nome,
        ordenacao=ordenacao,
    )


# Mantém função antiga com nome e assinatura originais para retrocompatibilidade
def listar_catalogo(
    request: Request,
    db: Session,
    q: str | None = None,
    linha: str | None = None,
    tipo: str | None = None,
    promocao: bool = False,
) -> HTMLResponse:
    """Função compatível com a suíte de testes existente."""
    return listar_produtos(
        request=request,
        db=db,
        q=q,
        linha=linha,
        tipo=tipo,
        promocao=promocao,
    )


@router.get("/vestidos", response_class=HTMLResponse)
def listar_vestidos(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    linha: Annotated[str | None, Query(description="Filtrar por linha")] = None,
    ordenacao: Annotated[str | None, Query(description="Ordenação global")] = None,
) -> HTMLResponse:
    """Página de listagem exclusiva de Vestidos (somente filtro de tamanho de roupas)."""
    return _render_catalogo_view(
        request=request,
        db=db,
        titulo_pagina="Vestidos",
        tipo_fixo="roupa",
        mostrar_categoria=False,
        mostrar_tamanho_roupa=True,
        mostrar_tamanho_sapato=False,
        linha=linha,
        ordenacao=ordenacao,
    )


@router.get("/saltos", response_class=HTMLResponse)
def listar_saltos(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    linha: Annotated[str | None, Query(description="Filtrar por linha")] = None,
    ordenacao: Annotated[str | None, Query(description="Ordenação global")] = None,
) -> HTMLResponse:
    """Página de listagem exclusiva de Saltos e Calçados (somente filtro de tamanho de sapatos)."""
    return _render_catalogo_view(
        request=request,
        db=db,
        titulo_pagina="Saltos",
        tipo_fixo="calcado",
        mostrar_categoria=False,
        mostrar_tamanho_roupa=False,
        mostrar_tamanho_sapato=True,
        linha=linha,
        ordenacao=ordenacao,
    )


@router.get("/corsets", response_class=HTMLResponse)
def listar_corsets(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    linha: Annotated[str | None, Query(description="Filtrar por linha")] = None,
    ordenacao: Annotated[str | None, Query(description="Ordenação global")] = None,
) -> HTMLResponse:
    """Página de listagem exclusiva de Corsets (somente filtro de tamanho de roupas)."""
    return _render_catalogo_view(
        request=request,
        db=db,
        titulo_pagina="Corsets",
        tipo_fixo="corset",
        mostrar_categoria=False,
        mostrar_tamanho_roupa=True,
        mostrar_tamanho_sapato=False,
        linha=linha,
        ordenacao=ordenacao,
    )


@router.get("/promocao", response_class=HTMLResponse)
def listar_promocoes(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    linha: Annotated[str | None, Query(description="Filtrar por linha")] = None,
    ordenacao: Annotated[str | None, Query(description="Ordenação global")] = None,
) -> HTMLResponse:
    """Página de listagem exclusiva de produtos em Promoção."""
    return _render_catalogo_view(
        request=request,
        db=db,
        titulo_pagina="Em Promoção",
        apenas_promocao=True,
        mostrar_categoria=True,
        mostrar_tamanho_roupa=True,
        mostrar_tamanho_sapato=True,
        linha=linha,
        ordenacao=ordenacao,
    )


@router.get("/plus-size", response_class=HTMLResponse)
def listar_plus_size(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    linha: Annotated[str | None, Query(description="Filtrar por linha")] = None,
    ordenacao: Annotated[str | None, Query(description="Ordenação global")] = None,
) -> HTMLResponse:
    """Página de listagem exclusiva de produtos Plus Size (tamanhos G1 a G5)."""
    return _render_catalogo_view(
        request=request,
        db=db,
        titulo_pagina="Plus Size",
        apenas_plus_size=True,
        mostrar_categoria=False,
        mostrar_tamanho_roupa=True,
        mostrar_tamanho_sapato=False,
        linha=linha,
        ordenacao=ordenacao,
    )


@router.get("/pesquisa", response_class=HTMLResponse)
def pesquisar_produtos(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(description="Termo da busca")] = None,
    tipo: Annotated[str | None, Query(description="Tipo de pesquisa: tudo, produtos, linhas")] = None,
    linha: Annotated[str | None, Query(description="Nome da linha")] = None,
    nome: Annotated[str | None, Query(description="Nome do produto")] = None,
) -> HTMLResponse:
    """Endpoint de busca acessado a partir do formulário de pesquisa do Header."""
    return _render_catalogo_view(
        request=request,
        db=db,
        titulo_pagina="Todos Produtos",
        mostrar_categoria=True,
        mostrar_tamanho_roupa=True,
        mostrar_tamanho_sapato=True,
        q=q,
        tipo_busca=tipo,
        linha=linha,
        nome=nome,
    )


@router.get("/produtos/{produto_id}", response_class=HTMLResponse)
def detalhe_produto(
    request: Request,
    produto_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> HTMLResponse:
    """Endpoint com página de detalhe do produto selecionado no carrossel ou catálogo."""
    produto_dto = ProdutoService.get_produto_por_id(session=db, produto_id=produto_id)
    if not produto_dto:
        raise HTTPException(status_code=404, detail="Produto não encontrado ou inativo")

    current_user = obter_usuario_logado(request, db)
    cart_count = 0
    if current_user:
        carrinho_dto = CarrinhoService.obter_carrinho_dto(db, current_user.ID)
        cart_count = carrinho_dto.quantidade_total

    return templates.TemplateResponse(
        request=request,
        name="catalogo/produto_detalhe.html",
        context={"produto": produto_dto, "current_user": current_user, "cart_count": cart_count},
    )


@router.get("/api/linhas/recentes", tags=["Linhas"])
def obter_linhas_recentes_api(
    db: Annotated[Session, Depends(get_db)],
) -> list[dict[str, object]]:
    """Retorna as 4 linhas mais recentes em formato JSON para a aba de Explorar."""
    linhas = HomeService.get_linhas_recentes(db, limit=4)
    if not linhas:
        # Fallback padrão das 4 linhas da imagem de design (18_Made In lace Explorar.png)
        return [
            {"id": 1, "nome": "Cunty", "imagem_url": "img/linhas/linha_cunty.png", "link_url": "/produtos?linha=Cunty"},
            {"id": 2, "nome": "Summer", "imagem_url": "img/linhas/linha_summer.png", "link_url": "/produtos?linha=Summer"},
            {"id": 3, "nome": "Christmas", "imagem_url": "img/linhas/linha_christmas.png", "link_url": "/produtos?linha=Christmas"},
            {"id": 4, "nome": "Fairycore", "imagem_url": "img/linhas/linha_fairycore.png", "link_url": "/produtos?linha=Fairycore"},
        ]
    return [
        {
            "id": linha_obj.id,
            "nome": linha_obj.nome,
            "imagem_url": linha_obj.imagem_url,
            "link_url": linha_obj.link_url,
        }
        for linha_obj in linhas
    ]
