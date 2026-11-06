"""Testes de integração para todos os endpoints de Autenticação e Registro."""

from datetime import date

import pytest
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import Base
from app.core.security import hash_password
from app.main import app
from app.models import Usuario
from app.routers.auth import (
    enviar_codigo_cadastro,
    get_logout,
    post_api_registro,
    post_login,
    recuperar_email_por_cpf,
    redefinir_senha,
    solicitar_recuperacao_senha,
    validar_codigo_cadastro,
    validar_codigo_recuperacao,
    verificar_unicidade,
)
from app.schemas.auth import (
    EnderecoCadastroPayload,
    RecuperarEmailPayload,
    RedefinirSenhaPayload,
    RegistroPayload,
    SolicitarRecuperacaoPayload,
    ValidarCodigoPayload,
    VerificarUnicidadePayload,
)


@pytest.fixture
def db_session() -> Session:
    """Cria engine SQLite em memória para os testes de integração das rotas de autenticação."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        return session
    finally:
        session.close()


def test_login_post_credenciais_invalidas(db_session: Session) -> None:
    """Verifica que credenciais inválidas retornam a mensagem exigida 'email ou senha estão errados'."""
    scope = {"type": "http", "method": "POST", "path": "/login", "headers": [], "app": app}
    req = Request(scope)
    res = Response()

    response = post_login(
        request=req,
        response=res,
        db=db_session,
        email="inexistente@exemplo.com",
        password="SenhaQualquer123!",
    )
    assert isinstance(response, HTMLResponse)
    assert response.status_code == 200
    html = bytes(response.body).decode("utf-8")
    assert "email ou senha estão errados" in html


def test_login_post_sucesso_com_email_e_cpf(db_session: Session) -> None:
    """Verifica que o login com credenciais corretas autentica e define o cookie user_id."""
    # Cria usuário de teste
    user = Usuario(
        NOME="Beatriz",
        SOBRENOME="Melo",
        EMAIL="beatriz@exemplo.com",
        SENHA_HASH=hash_password("SenhaForte2026!#"),
        NASCIMENTO=date(1996, 7, 10),
        CPF="11122233344",
        TELEFONE="11988887777",
        ATIVO=True,
    )
    db_session.add(user)
    db_session.commit()

    scope = {"type": "http", "method": "POST", "path": "/login", "headers": [], "app": app}
    req = Request(scope)

    # 1. Login com Email
    res1 = Response()
    resp_email = post_login(
        request=req,
        response=res1,
        db=db_session,
        email="beatriz@exemplo.com",
        password="SenhaForte2026!#",
    )
    assert isinstance(resp_email, RedirectResponse)
    assert resp_email.status_code == 303
    assert "user_id" in resp_email.headers.get("set-cookie", "")

    # 2. Login com CPF
    res2 = Response()
    resp_cpf = post_login(
        request=req,
        response=res2,
        db=db_session,
        email="111.222.333-44",
        password="SenhaForte2026!#",
    )
    assert isinstance(resp_cpf, RedirectResponse)
    assert resp_cpf.status_code == 303
    assert "user_id" in resp_cpf.headers.get("set-cookie", "")


def test_login_redireciona_para_origem_ou_carrinho(db_session: Session) -> None:
    """Garante que o login redireciona de volta para a página de origem ou para o carrinho já logado."""
    user = Usuario(
        NOME="Carla",
        SOBRENOME="Souza",
        EMAIL="carla@exemplo.com",
        SENHA_HASH=hash_password("SenhaCarla2026!#"),
        NASCIMENTO=date(1995, 5, 20),
        CPF="99988877766",
        TELEFONE="11999998888",
        ATIVO=True,
    )
    db_session.add(user)
    db_session.commit()

    # 1. get_login com ?next=/carrinho deve renderizar o input hidden next_url
    scope_get = {
        "type": "http",
        "method": "GET",
        "path": "/login",
        "query_string": b"next=/carrinho",
        "headers": [],
        "app": app,
    }
    req_get = Request(scope_get)
    from app.routers.auth import get_login
    resp_get = get_login(req_get, next="/carrinho")
    assert isinstance(resp_get, HTMLResponse)
    html_get = bytes(resp_get.body).decode("utf-8")
    assert '<input type="hidden" name="next_url" id="login-next-url" value="/carrinho">' in html_get

    # 2. post_login via form com next_url="/carrinho"
    scope_post_carrinho = {
        "type": "http",
        "method": "POST",
        "path": "/login",
        "headers": [],
        "app": app,
    }
    req_post_carrinho = Request(scope_post_carrinho)
    res_post_carrinho = Response()
    resp_carrinho = post_login(
        request=req_post_carrinho,
        response=res_post_carrinho,
        db=db_session,
        email="carla@exemplo.com",
        password="SenhaCarla2026!#",
        next_url="/carrinho",
    )
    assert isinstance(resp_carrinho, RedirectResponse)
    assert resp_carrinho.status_code == 303
    assert resp_carrinho.headers.get("location") == "/carrinho"
    assert "user_id" in resp_carrinho.headers.get("set-cookie", "")

    # 3. post_login com query_string next=/produtos (sem next_url no form)
    scope_query = {
        "type": "http",
        "method": "POST",
        "path": "/login",
        "query_string": b"next=/produtos",
        "headers": [(b"accept", b"application/json")],
        "app": app,
    }
    req_query = Request(scope_query)
    resp_ajax = post_login(
        request=req_query,
        response=Response(),
        db=db_session,
        email="carla@exemplo.com",
        password="SenhaCarla2026!#",
        next_url=None,
    )
    assert isinstance(resp_ajax, JSONResponse)
    assert resp_ajax.status_code == 200
    import json
    data_ajax = json.loads(bytes(resp_ajax.body).decode("utf-8"))
    assert data_ajax["success"] is True
    assert data_ajax["redirect_url"] == "/produtos"
    assert "user_id" in resp_ajax.headers.get("set-cookie", "")


def test_fluxo_recuperacao_endpoints(db_session: Session) -> None:
    """Testa os endpoints POST /auth/recuperar-senha/solicitar, validar e redefinir."""
    user = Usuario(
        NOME="Helena",
        SOBRENOME="Ramos",
        EMAIL="helena@exemplo.com",
        SENHA_HASH=hash_password("SenhaAntiga123!#"),
        NASCIMENTO=date(1997, 4, 12),
        CPF="55566677788",
        TELEFONE="16988889999",
        ATIVO=True,
    )
    db_session.add(user)
    db_session.commit()

    # 1. Solicitar código
    data_sol = solicitar_recuperacao_senha(
        payload=SolicitarRecuperacaoPayload(email="helena@exemplo.com"),
        db=db_session,
    )
    assert data_sol["success"] is True
    assert data_sol["expira_em_segundos"] == 3600
    assert data_sol["timer"] == 3600
    code = data_sol["debug_code"]
    assert len(code) == 6

    # 2. Validar código
    data_val = validar_codigo_recuperacao(
        payload=ValidarCodigoPayload(email="helena@exemplo.com", codigo=code),
        db=db_session,
    )
    assert data_val["success"] is True

    # 3. Redefinir senha
    nova_senha = "NovaSenhaForte2026!#"
    res_mock = Response()
    data_red = redefinir_senha(
        payload=RedefinirSenhaPayload(
            email="helena@exemplo.com",
            codigo=code,
            nova_senha=nova_senha,
            confirmar_senha=nova_senha,
        ),
        response=res_mock,
        db=db_session,
    )
    assert data_red["success"] is True
    assert data_red["redirect_url"] == "/"

    # 4. Login com a nova senha
    scope = {"type": "http", "method": "POST", "path": "/login", "headers": [], "app": app}
    req = Request(scope)
    res_login = post_login(
        request=req,
        response=Response(),
        db=db_session,
        email="helena@exemplo.com",
        password=nova_senha,
    )
    assert isinstance(res_login, RedirectResponse)
    assert res_login.status_code == 303


def test_fluxo_recuperacao_por_cpf(db_session: Session) -> None:
    """Testa o resgate de e-mail censurado pelo CPF e data de nascimento (Modal 3)."""
    user = Usuario(
        NOME="Julia",
        SOBRENOME="Castro",
        EMAIL="julia.castro@gmail.com",
        SENHA_HASH=hash_password("SenhaJulia2026!#"),
        NASCIMENTO=date(1995, 8, 25),
        CPF="14647756807",
        TELEFONE="11977778888",
        ATIVO=True,
    )
    db_session.add(user)
    db_session.commit()

    res_mock = Response()

    # 0. Busca com dados inexistentes retorna erro
    data_inexistente = recuperar_email_por_cpf(
        payload=RecuperarEmailPayload(cpf="99999999999", nascimento="01/01/2000"),
        response=res_mock,
        db=db_session,
    )
    assert data_inexistente["success"] is False

    # 1. Busca e-mail censurado dinamicamente a partir do banco
    data = recuperar_email_por_cpf(
        payload=RecuperarEmailPayload(cpf="14647756807", nascimento="25/08/1995"),
        response=res_mock,
        db=db_session,
    )
    assert data["success"] is True
    assert "ju" in data["masked_email"]
    assert "@g" in data["masked_email"]
    assert data["masked_email"] == "ju**********@g****.com"

    # 2. Senha incorreta não autentica
    data_senha_errada = recuperar_email_por_cpf(
        payload=RecuperarEmailPayload(cpf="14647756807", nascimento="25/08/1995", senha="SenhaIncorreta!#"),
        response=res_mock,
        db=db_session,
    )
    assert data_senha_errada["success"] is False
    assert "Senha incorreta" in data_senha_errada["message"]

    # 3. Busca e login direto com senha correta
    res_login_mock = Response()
    data_login = recuperar_email_por_cpf(
        payload=RecuperarEmailPayload(cpf="14647756807", nascimento="25/08/1995", senha="SenhaJulia2026!#"),
        response=res_login_mock,
        db=db_session,
    )
    assert data_login["success"] is True
    assert data_login["redirect_url"] in ["/", "/perfil"]
    assert "user_id" in res_login_mock.headers.get("set-cookie", "")


def test_verificar_unicidade_endpoint(db_session: Session) -> None:
    """Valida o endpoint POST /auth/verificar-unicidade."""
    user = Usuario(
        NOME="Marina",
        SOBRENOME="Silva",
        EMAIL="marina@exemplo.com",
        SENHA_HASH=hash_password("SenhaMarina2026!#"),
        CPF="33344455566",
        ATIVO=True,
    )
    db_session.add(user)
    db_session.commit()

    res_existente = verificar_unicidade(
        payload=VerificarUnicidadePayload(email="marina@exemplo.com", cpf="33344455566"),
        db=db_session,
    )
    assert res_existente["email_ja_usado"] is True
    assert res_existente["cpf_ja_usado"] is True

    res_novo = verificar_unicidade(
        payload=VerificarUnicidadePayload(email="outro@exemplo.com", cpf="99988877766"),
        db=db_session,
    )
    assert res_novo["email_ja_usado"] is False
    assert res_novo["cpf_ja_usado"] is False


def test_api_registro_completo(db_session: Session) -> None:
    """Testa o endpoint POST /api/registro com envio prévio de código na VERIFICACAO_EMAIL."""
    email = "novo.usuario@exemplo.com"

    # 1. Enviar código de cadastro
    res_code = enviar_codigo_cadastro(
        payload=SolicitarRecuperacaoPayload(email=email),
        db=db_session,
    )
    assert res_code["success"] is True
    assert res_code["expira_em_segundos"] == 900
    assert res_code["timer"] == 900
    code = res_code["debug_code"]

    # 2. Validar código
    res_val = validar_codigo_cadastro(
        payload=ValidarCodigoPayload(email=email, codigo=code),
        db=db_session,
    )
    assert res_val["success"] is True

    # 3. Submeter cadastro com endereço
    payload = RegistroPayload(
        email=email,
        cpf="12312312399",
        nome="Marina",
        sobrenome="Alves",
        senha="SenhaValida2026!#",
        nascimento="10/02/1994",
        telefone="16999887766",
        codigo_verificacao=code,
        enderecos=[
            EnderecoCadastroPayload(
                nome="Casa",
                cep="01310100",
                logradouro="Avenida Paulista",
                numero="1000",
                bairro="Bela Vista",
                cidade="São Paulo",
                estado="SP",
                complemento="Apto 42",
                principal=True,
            )
        ],
    )
    res_reg = post_api_registro(payload=payload, db=db_session)
    assert isinstance(res_reg, JSONResponse)
    assert res_reg.status_code == 201

    # 4. Login com o usuário cadastrado
    scope = {"type": "http", "method": "POST", "path": "/login", "headers": [], "app": app}
    req = Request(scope)
    res_login = post_login(
        request=req,
        response=Response(),
        db=db_session,
        email=email,
        password="SenhaValida2026!#",
    )
    assert isinstance(res_login, RedirectResponse)
    assert res_login.status_code == 303


def test_logout_endpoint() -> None:
    """Valida se GET /logout remove o cookie de autenticação e redireciona."""
    resp = get_logout()
    assert resp.status_code == 303
    assert resp.headers.get("location") == "/"
    assert "user_id" in resp.headers.get("set-cookie", "")
