"""Testes unitários rigorosos para AuthService e Security (MadeInLace)."""

from collections.abc import Generator
from datetime import date

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.security import (
    clean_digits,
    hash_password,
    mask_email,
    validate_password_strength,
    verify_password,
)
from app.models import Carrinho, EnderecoUsuario, Usuario, VerificacaoEmail
from app.services.auth_service import AuthService


@pytest.fixture
def memory_db() -> Generator[Session, None, None]:
    """Cria banco isolado em memória SQLite para os testes do AuthService."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


def test_argon2_hash_and_verify() -> None:
    """Garante que o hash Argon2id cifra e verifica senhas com salt único."""
    raw = "LaceMade2026!#"
    h1 = hash_password(raw)
    h2 = hash_password(raw)

    assert h1 != h2, "Salts aleatórios devem gerar hashes diferentes"
    assert verify_password(raw, h1) is True
    assert verify_password(raw, h2) is True
    assert verify_password("SenhaIncorreta123!", h1) is False
    assert verify_password("", h1) is False


def test_password_strength_business_rules() -> None:
    """Valida as regras da Seção 2.3 da Documentação (mínimo 12 caracteres, maiúscula, minúscula, número, símbolo, != email)."""
    # 1. Menos de 12 caracteres
    ok, _ = validate_password_strength("Curta123!")
    assert ok is False

    # 2. Sem maiúscula
    ok, _ = validate_password_strength("semmaiuscula123!#")
    assert ok is False

    # 3. Sem minúscula
    ok, _ = validate_password_strength("SEMMINUSCULA123!#")
    assert ok is False

    # 4. Sem número
    ok, _ = validate_password_strength("SemNumeroPeloMenos!")
    assert ok is False

    # 5. Sem símbolo
    ok, _ = validate_password_strength("SemSimbolo123456")
    assert ok is False

    # 6. Igual ao e-mail
    ok, _ = validate_password_strength("cliente@exemplo.com", email="cliente@exemplo.com")
    assert ok is False

    # 7. Válida
    ok, err = validate_password_strength("MinhaSenhaForte2026!#", email="outro@exemplo.com")
    assert ok is True
    assert err is None


def test_mask_email() -> None:
    """Valida a censura parcial de e-mail conforme exibido no design 30_MadeInLace Recuperacao1.1."""
    assert mask_email("sophia.designer@gmail.com") == "so*************@g****.com"
    assert mask_email("so@test.org") == "so****@t***.org"


def test_clean_digits() -> None:
    """Garante a remoção de formatação de CPF, CEP e telefones."""
    assert clean_digits("123.456.789-00") == "12345678900"
    assert clean_digits("01310-100") == "01310100"
    assert clean_digits("(16) 99876-5432") == "16998765432"
    assert clean_digits(None) == ""


def test_fluxo_completo_registro_e_autenticacao(memory_db: Session) -> None:
    """Valida o registro atômico com verificação de código e login por email ou CPF."""
    email = "camila@exemplo.com"
    cpf = "12345678901"
    senha = "MinhaSenhaForte2026!#"

    # 1. Envia código de cadastro
    ok_send, code, expira_segundos = AuthService.send_registration_email_code(memory_db, email)
    assert ok_send is True
    assert len(code) == 6
    assert expira_segundos == 900

    # 2. Verifica se o código é válido
    assert AuthService.verify_registration_email_code(memory_db, email, code) is True

    # 3. Registra usuário e endereço
    dados_usuario = {
        "email": email,
        "cpf": cpf,
        "nome": "Camila",
        "sobrenome": "Silveira",
        "senha": senha,
        "nascimento": "15/05/1995",
        "telefone": "11987654321",
    }
    enderecos = [
        {
            "nome": "Casa",
            "cep": "01310100",
            "logradouro": "Avenida Paulista",
            "numero": "1000",
            "bairro": "Bela Vista",
            "cidade": "São Paulo",
            "estado": "SP",
            "complemento": "Apto 42",
            "principal": True,
        }
    ]

    ok_reg, err, user = AuthService.register_user(
        db=memory_db,
        dados_usuario=dados_usuario,
        enderecos=enderecos,
        codigo_verificacao=code,
    )
    assert ok_reg is True
    assert err is None
    assert user is not None
    assert user.ID is not None

    # 4. Garante que o endereço foi gravado na mesma transação
    ends = memory_db.scalars(select(EnderecoUsuario).where(EnderecoUsuario.FK_USUARIO == user.ID)).all()
    assert len(ends) == 1
    assert ends[0].LOGRADOURO == "Avenida Paulista"

    # 5. Garante que o código na VERIFICACAO_EMAIL foi marcado como expirado
    verif = memory_db.scalar(select(VerificacaoEmail).where(VerificacaoEmail.EMAIL == email))
    assert verif is not None
    assert verif.EXPIRADO is True

    # 6. Autenticação por e-mail
    auth_email = AuthService.authenticate_user(memory_db, identifier=email, password=senha)
    assert auth_email is not None
    assert auth_email.ID == user.ID

    # 7. Autenticação por CPF
    auth_cpf = AuthService.authenticate_user(memory_db, identifier="123.456.789-01", password=senha)
    assert auth_cpf is not None
    assert auth_cpf.ID == user.ID

    # 8. Autenticação com senha incorreta
    assert AuthService.authenticate_user(memory_db, identifier=email, password="SenhaErrada123!") is None


def test_recuperacao_de_senha_fluxo(memory_db: Session) -> None:
    """Valida o ciclo completo de solicitação, validação de token e redefinição de senha."""
    email = "paula@exemplo.com"
    user = Usuario(
        NOME="Paula",
        SOBRENOME="Moraes",
        EMAIL=email,
        SENHA_HASH=hash_password("AntigaSenha123!#"),
        NASCIMENTO=date(1998, 3, 20),
        CPF="98765432100",
        TELEFONE="16999998888",
        ATIVO=True,
    )
    memory_db.add(user)
    memory_db.commit()

    # 1. Solicita código
    ok_sol, code, expira_segundos = AuthService.request_password_recovery(memory_db, email)
    assert ok_sol is True
    assert len(code) == 6
    assert expira_segundos == 3600

    # 2. Valida código
    assert AuthService.verify_recovery_code(memory_db, email, code) is True
    assert AuthService.verify_recovery_code(memory_db, email, "000000") is False

    # 3. Redefine senha com sucesso
    nova_senha = "NovaSenhaSegura2026!#"
    ok_reset, err_reset = AuthService.reset_password(
        db=memory_db,
        email=email,
        code=code,
        new_password=nova_senha,
        confirm_password=nova_senha,
    )
    assert ok_reset is True
    assert err_reset is None

    # 4. Antiga senha não funciona mais, nova senha funciona
    assert AuthService.authenticate_user(memory_db, identifier=email, password="AntigaSenha123!#") is None
    auth_novo = AuthService.authenticate_user(memory_db, identifier=email, password=nova_senha)
    assert auth_novo is not None
    assert auth_novo.ID == user.ID


def test_recuperacao_email_por_cpf_e_nascimento(memory_db: Session) -> None:
    """Valida a consulta do e-mail mascarado a partir do CPF e data de nascimento."""
    email = "larissa.estudante@gmail.com"
    cpf = "14647756807"
    nasc = "17/11/1993"
    senha = "SenhaLarissa2026!#"

    user = Usuario(
        NOME="Larissa",
        SOBRENOME="Costa",
        EMAIL=email,
        SENHA_HASH=hash_password(senha),
        NASCIMENTO=date(1993, 11, 17),
        CPF=cpf,
        TELEFONE="11977776666",
        ATIVO=True,
    )
    memory_db.add(user)
    memory_db.commit()

    # Busca com dados corretos
    masked, u_found = AuthService.find_masked_email_by_cpf_nasc(memory_db, cpf="146.477.568-07", nascimento=nasc)
    assert masked is not None
    assert masked.startswith("la")
    assert "@g" in masked
    assert u_found is not None
    assert u_found.ID == user.ID

    # Busca com CPF inexistente
    masked_err, _ = AuthService.find_masked_email_by_cpf_nasc(memory_db, cpf="00011122233", nascimento=nasc)
    assert masked_err is None


def test_cadastro_rejeita_endereco_vazio_ou_incompleto(memory_db: Session) -> None:
    """Garante que o cadastro rejeita lista de endereços vazia ou com campos incompletos."""
    email = "sem.endereco@exemplo.com"
    _, code, _ = AuthService.send_registration_email_code(memory_db, email)

    dados_usuario = {
        "email": email,
        "cpf": "12345678909",
        "nome": "Carla",
        "sobrenome": "Dias",
        "senha": "SenhaForte2026!#",
        "nascimento": "12/05/1990",
        "telefone": "11988889999",
    }

    # 1. Lista de endereços vazia
    ok_vazio, err_vazio, _ = AuthService.register_user(
        db=memory_db,
        dados_usuario=dados_usuario,
        enderecos=[],
        codigo_verificacao=code,
    )
    assert ok_vazio is False
    assert err_vazio == "É obrigatório cadastrar ao menos um endereço de entrega."

    # 2. Endereço com campos incompletos (sem CEP ou número)
    ok_incomp, err_incomp, _ = AuthService.register_user(
        db=memory_db,
        dados_usuario=dados_usuario,
        enderecos=[{"nome": "Casa", "cep": "", "logradouro": "", "numero": ""}],
        codigo_verificacao=code,
    )
    assert ok_incomp is False
    assert err_incomp == "Todos os endereços devem ter CEP, logradouro e número preenchidos."


def test_login_usuarios_da_seed(memory_db: Session) -> None:
    """Garante que todos os perfis de usuários cadastrados no seed oficial conseguem logar com email, CPF e senha."""
    seed_users = [
        ("Admin", "Loja", "admin@madeinlace.example.com", "Admin@MadeInLace2026!", "$argon2id$v=19$m=65536,t=3,p=4$9g4YM5lI3bG4VUx3FTt7pg$XMlHB3sBRctJ8AYsz4dgUi+WFvWpbouFZKbElucYV2I", None),
        ("Mariana", "Costa", "mariana.costa@example.com", "Mariana@Lace2026!", "$argon2id$v=19$m=65536,t=3,p=4$pRBORo4P2dTDPQcyka71bQ$r/zQy1yPq0jFdkPHaKkxYAAua0FxW1u9/FECXK8Dyyk", "12345678909"),
        ("Beatriz", "Almeida", "beatriz.almeida@example.com", "Beatriz@Lace2026!", "$argon2id$v=19$m=65536,t=3,p=4$4jzvv8DWSN79aNkGc/qXQQ$0R1KXaMNuNjrlaBsM1EP0euyOsa/LtrUZYAPjiInpZg", "23456789173"),
        ("Camila", "Ferreira", "camila.ferreira@example.com", "Camila@Lace2026!", "$argon2id$v=19$m=65536,t=3,p=4$nAtsZhK7m5OZiL+emZYN+A$d26cgzN6WQ27JuOot5LQXQMnM78B31Vjj9B5Dt/aJVE", "34567891228"),
        ("Juliana", "Souza", "juliana.souza@example.com", "Juliana@Lace2026!", "$argon2id$v=19$m=65536,t=3,p=4$5LyxPv/OpSfcX1eXKSv+mw$93zqiZzmuh51Xq0qZmZvB3NOmJSFzoe9zqTF7xKRMlk", "45678912364"),
        ("Larissa", "Martins", "larissa.martins@example.com", "Larissa@Lace2026!", "$argon2id$v=19$m=65536,t=3,p=4$OnEr5/zZGbdjfUskcm6IKQ$o2JJ6uthltQqBa71dz1DUX3IUIW9TWZpfB1QNl7Ojy0", "56789123482"),
        ("Fernanda", "Lima", "fernanda.lima@example.com", "Fernanda@Lace2026!", "$argon2id$v=19$m=65536,t=3,p=4$gsTFMvFbOfgsD8UJaQkBUA$WskTGXiTvsKN3ZYaxZF3NMiVtZuCN5QVTz+W98U4TmM", "52998224725"),
    ]

    for nome, sobrenome, email, _senha, senha_hash, cpf in seed_users:
        u = Usuario(
            NOME=nome,
            SOBRENOME=sobrenome,
            EMAIL=email,
            SENHA_HASH=senha_hash,
            CPF=cpf,
            ATIVO=True,
        )
        memory_db.add(u)
    memory_db.commit()

    # Valida login de cada usuário pelo e-mail e senha
    for _, _, email, senha, _, cpf in seed_users:
        auth_user = AuthService.authenticate_user(memory_db, identifier=email, password=senha)
        assert auth_user is not None, f"Falha ao autenticar usuário da seed por email: {email}"
        assert auth_user.EMAIL == email

        # Valida login pelo CPF quando disponível
        if cpf:
            auth_cpf = AuthService.authenticate_user(memory_db, identifier=cpf, password=senha)
            assert auth_cpf is not None, f"Falha ao autenticar usuário da seed por CPF: {cpf}"
            assert auth_cpf.EMAIL == email


def test_persistencia_real_novo_usuario_no_banco() -> None:
    """Garante que novos cadastros persistem fisicamente no banco entre sessões isoladas (sem cache em memória)."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    email = "permanente@exemplo.com"
    senha = "SenhaForte2026!#"

    # Sessão 1: Realiza o cadastro e comita
    with Session(engine) as session1:
        _, code, _ = AuthService.send_registration_email_code(session1, email)
        dados = {
            "email": email,
            "cpf": "12345678909",
            "nome": "Tatiana",
            "sobrenome": "Rios",
            "senha": senha,
            "nascimento": "14/03/1993",
            "telefone": "11988887777",
        }
        enderecos = [
            {
                "nome": "Casa",
                "cep": "01310100",
                "logradouro": "Avenida Paulista",
                "numero": "1000",
                "bairro": "Bela Vista",
                "cidade": "São Paulo",
                "estado": "SP",
                "complemento": "Apto 42",
                "principal": True,
            }
        ]
        ok, err, novo_u = AuthService.register_user(session1, dados, enderecos, code)
        assert ok is True
        assert err is None
        assert novo_u is not None
        user_id = novo_u.ID

    # Sessão 2: Sessão COMPLETAMENTE NOVA a partir do engine (zero cache)
    with Session(engine) as session2:
        persisted_user = session2.get(Usuario, user_id)
        assert persisted_user is not None
        assert persisted_user.EMAIL == email
        assert persisted_user.NOME == "Tatiana"

        # Garante persistência dos endereços vinculados
        ends = session2.scalars(select(EnderecoUsuario).where(EnderecoUsuario.FK_USUARIO == user_id)).all()
        assert len(ends) == 1
        assert ends[0].LOGRADOURO == "Avenida Paulista"

        # Garante persistência do carrinho inicial ativo
        carrinho = session2.scalar(select(Carrinho).where(Carrinho.FK_USUARIO == user_id, Carrinho.STATUS == "ATIVO"))
        assert carrinho is not None

        # Garante que o usuário consegue autenticar na nova sessão
        auth_u = AuthService.authenticate_user(session2, identifier=email, password=senha)
        assert auth_u is not None
        assert auth_u.ID == user_id


def test_email_service_modo_console_emite_codigo_terminal(capsys: pytest.CaptureFixture[str]) -> None:
    """Garante que o modo console emite o banner e o código no terminal e registra em memória."""
    from app.core.config import settings
    from app.services.email_service import EmailService

    original_mode = settings.email_mode
    try:
        settings.email_mode = "console"
        email = "sophia.silva93@gmail.com"
        code = "987654"

        ok = EmailService.send_verification_email(email, code)
        assert ok is True
        assert EmailService.last_sent_codes.get(email) == code

        captured = capsys.readouterr()
        assert "[SIMULAÇÃO DE E-MAIL MADEINLACE]" in captured.out
        assert email in captured.out
        assert code in captured.out
    finally:
        settings.email_mode = original_mode

