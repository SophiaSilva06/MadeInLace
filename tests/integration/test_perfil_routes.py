"""Testes de integração para todos os endpoints da página de Perfil."""

from collections.abc import Generator
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import Base
from app.core.security import hash_password
from app.main import app
from app.models import (
    Carrinho,
    EnderecoUsuario,
    Fornecedor,
    Linha,
    MetodoPagamento,
    StatusTroca,
    StatusVenda,
    Usuario,
    Venda,
)
from app.routers.perfil import (
    definir_endereco_principal_api,
    enviar_codigo_email_atual,
    enviar_codigo_email_novo,
    get_perfil,
    listar_pedidos_api,
    post_salvar_perfil,
    remover_endereco_api,
    salvar_novo_endereco_perfil_api,
    validar_troca_email_api,
)
from app.schemas.perfil import (
    AtualizarPerfilPayload,
    EnderecoPerfilPayload,
    SolicitarCodigoEmailPayload,
    ValidarCodigoEmailPayload,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Cria banco SQLite em memória para os testes de integração das rotas de perfil."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Status de venda
    for sid, estado, desc in [
        (1, "EM_PROCESSAMENTO", "Em Processamento"),
        (2, "NA_TRANSPORTADORA", "Na Transportadora"),
        (3, "EM_TRANSITO", "Em Trânsito"),
        (4, "ENTREGANDO", "Entregando"),
        (5, "ENTREGUE", "Entregue"),
        (6, "TENTATIVA_FALHA", "Tentativa Falha"),
        (7, "CANCELADO", "Cancelado"),
    ]:
        session.add(StatusVenda(ID=sid, ESTADO_ANDAMENTO=estado, DESCRICAO=desc))

    # Status de troca
    for sid, estado, desc in [
        (1, "SOLICITADA", "Solicitada"),
        (2, "APROVADA", "Aprovada"),
        (3, "DEVOLUCAO_RECEBIDA", "Devolução Recebida"),
        (4, "EM_PROCESSAMENTO", "Em Processamento"),
        (5, "NA_TRANSPORTADORA", "Na Transportadora"),
        (6, "ENTREGANDO", "Entregando"),
        (7, "ENTREGUE", "Entregue"),
        (8, "RECUSADA", "Recusada"),
    ]:
        session.add(StatusTroca(ID=sid, ESTADO_ANDAMENTO=estado, DESCRICAO=desc))

    # Métodos de pagamento
    for mid, met in [(1, "PIX"), (2, "Cartão de Crédito"), (3, "Cartão de Débito"), (4, "Boleto")]:
        session.add(MetodoPagamento(ID=mid, METODO=met))

    forn = Fornecedor(ID=1, NOME="Fornecedor Principal", CNPJ="11111111000100", RAZAO_SOCIAL="Fornecedor LTDA", ATIVO=True)
    linha = Linha(ID=1, NOME="Coleção Exclusiva")
    session.add_all([forn, linha])
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def usuario_autenticado(db_session: Session) -> Usuario:
    """Cria e retorna usuário de teste para sessão."""
    u = Usuario(
        NOME="Sophia",
        SOBRENOME="Silva",
        EMAIL="sophia.gamer.silva93@gmail.com",
        SENHA_HASH=hash_password("SenhaForte@2026"),
        NASCIMENTO=date(1993, 11, 17),
        CPF="51039590896",
        TELEFONE="16992912930",
        ATIVO=True,
    )
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)

    end = EnderecoUsuario(
        FK_USUARIO=u.ID,
        NOME="Casa",
        CEP="14093238",
        LOGRADOURO="Rua Dulce Pereira Bidurin",
        NUMERO="445",
        COMPLEMENTO="Casa perto da esquina",
        BAIRRO="Horizonte Verde",
        CIDADE="Ribeirão Preto",
        ESTADO="SP",
        ATIVO=True,
    )
    db_session.add(end)
    db_session.commit()
    return u


def _criar_request(path: str = "/perfil", user_id: int | None = None) -> Request:
    """Gera Starlette Request com cookie user_id mockado se autenticado."""
    headers = []
    if user_id is not None:
        headers.append((b"cookie", f"user_id={user_id}".encode("ascii")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "app": app,
    }
    return Request(scope)


def test_get_perfil_redireciona_se_nao_autenticado(db_session: Session) -> None:
    """Usuário não logado ao acessar /perfil deve ser redirecionado para /login?next=/perfil."""
    req = _criar_request(path="/perfil", user_id=None)
    resp = get_perfil(request=req, secao="dados", db=db_session)
    assert isinstance(resp, RedirectResponse)
    assert resp.status_code == 303
    assert "/login" in resp.headers["location"]


def test_get_perfil_autenticado_carrega_dados(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Usuário autenticado visualiza Meu Perfil com seus dados preenchidos."""
    req = _criar_request(path="/perfil", user_id=usuario_autenticado.ID)
    resp = get_perfil(request=req, secao="dados", db=db_session)
    assert resp.status_code == 200
    conteudo = bytes(resp.body).decode("utf-8")
    assert "Meu Perfil" in conteudo
    assert "Sophia" in conteudo
    assert "Silva" in conteudo
    assert "sophia.gamer.silva93@gmail.com" in conteudo


def test_get_perfil_tamanhos_e_contatos_permitem_acesso_publico(db_session: Session) -> None:
    """Aba de tamanhos e contatos devem ser acessíveis mesmo sem login."""
    req_t = _criar_request(path="/perfil/tamanhos", user_id=None)
    resp_t = get_perfil(request=req_t, secao="tamanhos", db=db_session)
    assert resp_t.status_code == 200
    assert "Medidas Corporais por Tamanho" in bytes(resp_t.body).decode("utf-8") or "Guia de Tamanhos" in bytes(resp_t.body).decode("utf-8")

    req_c = _criar_request(path="/perfil/contatos", user_id=None)
    resp_c = get_perfil(request=req_c, secao="contatos", db=db_session)
    assert resp_c.status_code == 200
    assert "Contatos" in bytes(resp_c.body).decode("utf-8")


def test_post_salvar_perfil_atualiza_informacoes(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Endpoint de salvar perfil persiste dados quando usuário clica em salvar informações."""
    req = _criar_request(path="/perfil/salvar", user_id=usuario_autenticado.ID)
    payload = AtualizarPerfilPayload(
        nome="Sophia Modificada",
        sobrenome="Silva Ramos",
        telefone="16988887777",
    )
    resp = post_salvar_perfil(payload=payload, request=req, response=Response(), db=db_session)
    assert resp["success"] is True

    db_session.refresh(usuario_autenticado)
    assert usuario_autenticado.NOME == "Sophia Modificada"
    assert usuario_autenticado.TELEFONE == "16988887777"


def test_fluxo_alteracao_email_endpoints(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Verifica envio de códigos para e-mail atual e novo via endpoints."""
    req = _criar_request(path="/perfil", user_id=usuario_autenticado.ID)

    # 1. Enviar código para e-mail atual
    resp_envio_atual = enviar_codigo_email_atual(request=req, db=db_session)
    assert resp_envio_atual["success"] is True
    assert resp_envio_atual["expira_em_segundos"] == 900
    cod_atual = resp_envio_atual["debug_code"]

    # 2. Enviar código para novo e-mail
    payload_novo = SolicitarCodigoEmailPayload(email="novo.email@teste.com")
    resp_envio_novo = enviar_codigo_email_novo(payload=payload_novo, request=req, db=db_session)
    assert resp_envio_novo["success"] is True
    assert resp_envio_novo["expira_em_segundos"] == 900
    cod_novo = resp_envio_novo["debug_code"]

    # 3. Validar ambos com senha atual
    payload_val = ValidarCodigoEmailPayload(
        email_atual=usuario_autenticado.EMAIL,
        codigo_atual=cod_atual,
        novo_email="novo.email@teste.com",
        codigo_novo=cod_novo,
        senha_atual="SenhaForte@2026",
    )
    resp_val = validar_troca_email_api(payload=payload_val, request=req, db=db_session)
    assert resp_val["success"] is True


def test_listar_pedidos_api_paginacao(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Endpoint de listagem de pedidos retorna 2 itens por vez."""
    req = _criar_request(path="/perfil/api/pedidos", user_id=usuario_autenticado.ID)

    # Cria 3 pedidos
    for i in range(1, 4):
        carrinho = Carrinho(FK_USUARIO=usuario_autenticado.ID, STATUS="CONVERTIDO", TOTAL=Decimal("100.00"))
        db_session.add(carrinho)
        db_session.commit()
        v = Venda(
            FK_CARRINHO=carrinho.ID,
            FK_USUARIO=usuario_autenticado.ID,
            FK_ENDERECO_USUARIO=usuario_autenticado.enderecos[0].ID,
            FK_METODO_PAGAMENTO=1,
            FK_STATUS=5,
            SUBTOTAL=Decimal("100.00"),
            FRETE=Decimal("10.00"),
            TOTAL=Decimal("110.00"),
            DATA=datetime(2026, 10, i),
        )
        db_session.add(v)
        db_session.commit()

    resultado = listar_pedidos_api(request=req, db=db_session, filtro="todos", limit=2, offset=0)
    assert len(resultado["pedidos"]) == 2
    assert resultado["tem_mais"] is True
    assert resultado["pedidos"][0]["nome_exibicao"] == "Pedido 1"
    assert resultado["pedidos"][1]["nome_exibicao"] == "Pedido 2"


def test_definir_endereco_principal_api(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Endpoint para definir endereço principal atualiza a preferência do usuário."""
    end2 = EnderecoUsuario(
        FK_USUARIO=usuario_autenticado.ID,
        NOME="Trabalho",
        CEP="14093238",
        LOGRADOURO="Rua Dulce Pereira Bidurin",
        NUMERO="445",
        BAIRRO="Jardim Horizonte Verde",
        CIDADE="Ribeirão Preto",
        ESTADO="SP",
        ATIVO=True,
    )
    db_session.add(end2)
    db_session.commit()

    req = _criar_request(path=f"/perfil/enderecos/definir-principal/{end2.ID}", user_id=usuario_autenticado.ID)
    resp = definir_endereco_principal_api(endereco_id=end2.ID, request=req, response=Response(), db=db_session)
    assert resp["success"] is True


def test_remover_endereco_api(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Endpoint para remover endereço inativa o registro quando houver mais de um endereço."""
    end2 = EnderecoUsuario(
        FK_USUARIO=usuario_autenticado.ID,
        NOME="Trabalgo",
        CEP="14093238",
        LOGRADOURO="Rua Dulce Pereira Bidurin",
        NUMERO="445",
        BAIRRO="Jardim Horizonte Verde",
        CIDADE="Ribeirão Preto",
        ESTADO="SP",
        ATIVO=True,
    )
    db_session.add(end2)
    db_session.commit()

    req = _criar_request(path=f"/perfil/enderecos/remover/{end2.ID}", user_id=usuario_autenticado.ID)
    resp = remover_endereco_api(endereco_id=end2.ID, request=req, db=db_session)
    assert resp["success"] is True

    db_session.refresh(end2)
    assert end2.ATIVO is False


def test_salvar_novo_endereco_perfil_api(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Endpoint /perfil/enderecos/salvar cadastra o endereço diretamente e retorna formatado."""
    req = _criar_request(path="/perfil/enderecos/salvar", user_id=usuario_autenticado.ID)
    payload = EnderecoPerfilPayload(
        nome="Consultório",
        cep="14095-190",
        logradouro="Rua Vicente Oranges",
        numero="560",
        complemento="Sala 3",
        bairro="Parque Residencial Lagoinha",
        cidade="Ribeirão Preto",
        estado="SP",
    )
    resp = salvar_novo_endereco_perfil_api(
        payload=payload,
        request=req,
        response=Response(),
        db=db_session,
    )
    assert resp["success"] is True
    assert "endereco" in resp
    assert resp["endereco"]["nome"] == "Consultório"
    assert resp["endereco"]["numero"] == "560"
    assert resp["endereco"]["id"] > 0
    assert resp["endereco"]["is_principal"] is True


def test_remover_unico_endereco_perfil_api_rejeita(db_session: Session, usuario_autenticado: Usuario) -> None:
    """Garante que a rota de perfil recusa remover quando o usuário possui apenas 1 endereço ativo."""
    # usuario_autenticado possui apenas 1 endereço da fixture
    assert len(usuario_autenticado.enderecos) == 1
    end_unico = usuario_autenticado.enderecos[0]

    req = _criar_request(path=f"/perfil/enderecos/remover/{end_unico.ID}", user_id=usuario_autenticado.ID)
    resp = remover_endereco_api(endereco_id=end_unico.ID, request=req, db=db_session)
    assert resp["success"] is False
    assert "único endereço" in resp["message"].lower()

    # Confirma que continua ativo no banco
    db_session.refresh(end_unico)
    assert end_unico.ATIVO is True


def test_remover_endereco_perfil_preserva_registro_fisico_no_banco(
    db_session: Session, usuario_autenticado: Usuario
) -> None:
    """Verifica que a remoção é estritamente lógica (ATIVO=False) e o registro permanece na tabela ENDERECO_USUARIO."""
    end2 = EnderecoUsuario(
        FK_USUARIO=usuario_autenticado.ID,
        NOME="Endereço Teste Lógico",
        CEP="14093238",
        LOGRADOURO="Rua Dulce Pereira Bidurin",
        NUMERO="999",
        BAIRRO="Jardim",
        CIDADE="Ribeirão Preto",
        ESTADO="SP",
        ATIVO=True,
    )
    db_session.add(end2)
    db_session.commit()
    end_id = end2.ID

    req = _criar_request(path=f"/perfil/enderecos/remover/{end_id}", user_id=usuario_autenticado.ID)
    resp = remover_endereco_api(endereco_id=end_id, request=req, db=db_session)
    assert resp["success"] is True

    # Verifica persistência física: o registro NÃO foi deletado do banco
    registro_no_banco = db_session.get(EnderecoUsuario, end_id)
    assert registro_no_banco is not None
    assert registro_no_banco.ATIVO is False
    assert registro_no_banco.NOME == "Endereço Teste Lógico"


