from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import (
    clean_digits,
    generate_verification_code,
    hash_password,
    hash_token,
    mask_email,
    validate_password_strength,
    verify_password,
)
from app.models import Carrinho, EnderecoUsuario, Recuperacao, Usuario, VerificacaoEmail
from app.services.email_service import EmailService

logger = logging.getLogger("madeinlace.auth")


class AuthService:
    """Camada de serviço para autenticação, cadastro, segurança e recuperação de contas."""

    @classmethod
    def authenticate_user(cls, db: Session, identifier: str, password: str) -> Usuario | None:
        """Autentica o usuário por e-mail ou CPF.

        Conforme requisitos do projeto:
        - A interface exibe estritamente o campo 'Email:'
        - O backend aceita autenticação tanto pelo e-mail quanto pelo CPF
        """
        clean_id = identifier.strip().lower()
        if not clean_id or not password:
            return None

        user: Usuario | None = None

        # 1. Busca por e-mail
        if "@" in clean_id:
            user = db.scalar(select(Usuario).where(Usuario.EMAIL == clean_id, Usuario.ATIVO.is_(True)))

        # 2. Busca por CPF caso não seja e-mail ou caso a busca por e-mail não tenha encontrado
        if not user:
            cpf_digits = clean_digits(clean_id)
            if len(cpf_digits) == 11:
                user = db.scalar(select(Usuario).where(Usuario.CPF == cpf_digits, Usuario.ATIVO.is_(True)))

        if not user:
            return None

        # 3. Validação do hash de senha (Argon2id)
        if verify_password(password, user.SENHA_HASH):
            return user

        return None

    @classmethod
    def check_uniqueness(cls, db: Session, email: str | None = None, cpf: str | None = None) -> dict[str, bool]:
        """Verifica se e-mail ou CPF já estão cadastrados na base."""
        res = {"email_ja_usado": False, "cpf_ja_usado": False}

        if email:
            clean_email = email.strip().lower()
            existing_email = db.scalar(select(Usuario.ID).where(Usuario.EMAIL == clean_email))
            if existing_email:
                res["email_ja_usado"] = True

        if cpf:
            clean_cpf = clean_digits(cpf)
            if len(clean_cpf) == 11:
                existing_cpf = db.scalar(select(Usuario.ID).where(Usuario.CPF == clean_cpf))
                if existing_cpf:
                    res["cpf_ja_usado"] = True

        return res

    @classmethod
    def request_password_recovery(cls, db: Session, email: str) -> tuple[bool, str, int]:
        """Gera código de recuperação, armazena hash em RECUPERACAO e envia por e-mail."""
        clean_email = email.strip().lower()
        user = db.scalar(select(Usuario).where(Usuario.EMAIL == clean_email, Usuario.ATIVO.is_(True)))

        code = generate_verification_code(6)
        duracao_segundos = 3600

        if user:
            # Invalida pedidos de recuperação anteriores
            db.execute(
                update(Recuperacao)
                .where(Recuperacao.FK_USUARIO == user.ID, Recuperacao.EXPIRADO.is_(False))
                .values(EXPIRADO=True)
            )

            # Grava hash SHA-256 do token com validade de 1 hora
            token_hashed = hash_token(code)
            agora = datetime.now()
            data_expira = agora + timedelta(hours=1)
            recup = Recuperacao(
                FK_USUARIO=user.ID,
                TOKEN=token_hashed,
                DATA_CRIACAO=agora,
                DATA_EXPIRA=data_expira,
                EXPIRADO=False,
            )
            db.add(recup)
            db.commit()
            db.refresh(recup)

            duracao_segundos = int((recup.DATA_EXPIRA - recup.DATA_CRIACAO).total_seconds())

            # Envia e-mail
            EmailService.send_password_recovery_email(clean_email, code)

        return True, code, duracao_segundos

    @classmethod
    def verify_recovery_code(cls, db: Session, email: str, code: str) -> bool:
        """Verifica se o código de recuperação é válido e não expirado."""
        clean_email = email.strip().lower()
        user = db.scalar(select(Usuario).where(Usuario.EMAIL == clean_email, Usuario.ATIVO.is_(True)))
        if not user:
            return False

        token_hashed = hash_token(code)
        agora = datetime.now()

        recup = db.scalar(
            select(Recuperacao).where(
                Recuperacao.FK_USUARIO == user.ID,
                Recuperacao.TOKEN == token_hashed,
                Recuperacao.EXPIRADO.is_(False),
                Recuperacao.DATA_EXPIRA > agora,
            )
        )
        return recup is not None

    @classmethod
    def reset_password(
        cls, db: Session, email: str, code: str, new_password: str, confirm_password: str
    ) -> tuple[bool, str | None]:
        """Redefine a senha do usuário após validação das regras de negócio."""
        if new_password != confirm_password:
            return False, "A confirmação da senha não confere."

        valida, msg = validate_password_strength(new_password, email)
        if not valida:
            return False, msg

        clean_email = email.strip().lower()
        user = db.scalar(select(Usuario).where(Usuario.EMAIL == clean_email, Usuario.ATIVO.is_(True)))
        if not user:
            return False, "Usuário não encontrado."

        token_hashed = hash_token(code)
        agora = datetime.now()

        recup = db.scalar(
            select(Recuperacao).where(
                Recuperacao.FK_USUARIO == user.ID,
                Recuperacao.TOKEN == token_hashed,
                Recuperacao.EXPIRADO.is_(False),
                Recuperacao.DATA_EXPIRA > agora,
            )
        )
        if not recup:
            return False, "Código de verificação inválido ou expirado."

        # Atualiza a senha em hash Argon2id e expira o token
        user.SENHA_HASH = hash_password(new_password)
        recup.EXPIRADO = True
        db.commit()

        return True, None

    @classmethod
    def find_masked_email_by_cpf_nasc(cls, db: Session, cpf: str, nascimento: str) -> tuple[str | None, Usuario | None]:
        """Busca o e-mail censurado pelo CPF e data de nascimento (ex: so******@g******.com)."""
        clean_cpf = clean_digits(cpf)
        if len(clean_cpf) != 11:
            return None, None

        # Converte data de nascimento (DD/MM/AAAA ou YYYY-MM-DD)
        dt_nasc: date | None = None
        if "/" in nascimento:
            try:
                parts = nascimento.strip().split("/")
                dt_nasc = date(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                return None, None
        elif "-" in nascimento:
            try:
                dt_nasc = date.fromisoformat(nascimento.strip())
            except ValueError:
                return None, None

        if not dt_nasc:
            return None, None

        user = db.scalar(
            select(Usuario).where(
                Usuario.CPF == clean_cpf,
                Usuario.NASCIMENTO == dt_nasc,
                Usuario.ATIVO.is_(True),
            )
        )
        if not user:
            return None, None

        return mask_email(user.EMAIL), user

    @classmethod
    def send_registration_email_code(cls, db: Session, email: str) -> tuple[bool, str, int]:
        """Gera código, grava na nova tabela VERIFICACAO_EMAIL e envia por e-mail."""
        clean_email = email.strip().lower()
        code = generate_verification_code(6)
        token_hashed = hash_token(code)
        agora = datetime.now()
        data_expira = agora + timedelta(minutes=15)

        # Invalida códigos anteriores para este e-mail
        db.execute(
            update(VerificacaoEmail)
            .where(VerificacaoEmail.EMAIL == clean_email, VerificacaoEmail.EXPIRADO.is_(False))
            .values(EXPIRADO=True)
        )

        verif = VerificacaoEmail(
            EMAIL=clean_email,
            TOKEN=token_hashed,
            DATA_CRIACAO=agora,
            DATA_EXPIRA=data_expira,
            EXPIRADO=False,
            TENTATIVAS=0,
        )
        db.add(verif)
        db.commit()
        db.refresh(verif)

        duracao_segundos = int((verif.DATA_EXPIRA - verif.DATA_CRIACAO).total_seconds())

        # Envia e-mail
        EmailService.send_verification_email(clean_email, code)
        return True, code, duracao_segundos

    @classmethod
    def verify_registration_email_code(cls, db: Session, email: str, code: str) -> bool:
        """Verifica se o código da tabela VERIFICACAO_EMAIL confere e não expirou."""
        clean_email = email.strip().lower()
        token_hashed = hash_token(code)
        agora = datetime.now()

        verif = db.scalar(
            select(VerificacaoEmail).where(
                VerificacaoEmail.EMAIL == clean_email,
                VerificacaoEmail.EXPIRADO.is_(False),
                VerificacaoEmail.DATA_EXPIRA > agora,
            )
        )
        if not verif:
            return False

        if verif.TOKEN != token_hashed:
            verif.TENTATIVAS += 1
            if verif.TENTATIVAS >= 5:
                verif.EXPIRADO = True
            db.commit()
            return False

        return True

    @classmethod
    def register_user(
        cls,
        db: Session,
        dados_usuario: dict[str, Any],
        enderecos: list[dict[str, Any]],
        codigo_verificacao: str,
    ) -> tuple[bool, str | None, Usuario | None]:
        """Conclui o registro criando usuário, endereços e carrinho inicial na mesma transação."""
        email = dados_usuario.get("email", "").strip().lower()
        cpf = clean_digits(dados_usuario.get("cpf"))
        nome = dados_usuario.get("nome", "").strip()
        sobrenome = dados_usuario.get("sobrenome", "").strip()
        senha = dados_usuario.get("senha", "")
        telefone = clean_digits(dados_usuario.get("telefone"))
        nascimento_raw = dados_usuario.get("nascimento", "")

        # 1. Validações preliminares
        if not all([email, cpf, nome, sobrenome, senha, nascimento_raw, telefone]):
            return False, "Todos os campos cadastrais são obrigatórios.", None

        if len(cpf) != 11:
            return False, "CPF inválido. Deve conter 11 dígitos.", None

        if not enderecos or len(enderecos) == 0:
            return False, "É obrigatório cadastrar ao menos um endereço de entrega.", None

        for end_data in enderecos:
            cep_clean = clean_digits(end_data.get("cep"))
            logr = str(end_data.get("logradouro", "")).strip()
            num = str(end_data.get("numero", "")).strip()
            if not cep_clean or len(cep_clean) < 8 or not logr or not num:
                return (
                    False,
                    "Todos os endereços devem ter CEP, logradouro e número preenchidos.",
                    None,
                )

        # 2. Validação da regra da senha
        valida, msg_senha = validate_password_strength(senha, email)
        if not valida:
            return False, msg_senha, None

        # 3. Validação do código de e-mail na tabela VERIFICACAO_EMAIL
        if not cls.verify_registration_email_code(db, email, codigo_verificacao):
            return False, "Código de verificação de e-mail inválido ou expirado.", None

        # 4. Unicidade de e-mail e CPF
        uniq = cls.check_uniqueness(db, email=email, cpf=cpf)
        if uniq["email_ja_usado"]:
            return False, "E-mail já cadastrado.", None
        if uniq["cpf_ja_usado"]:
            return False, "CPF já cadastrado.", None

        # 5. Data de nascimento e maioridade (18 anos)
        dt_nasc: date | None = None
        if "/" in nascimento_raw:
            try:
                p = nascimento_raw.strip().split("/")
                dt_nasc = date(int(p[2]), int(p[1]), int(p[0]))
            except (ValueError, IndexError):
                return False, "Data de nascimento inválida.", None
        elif "-" in nascimento_raw:
            try:
                dt_nasc = date.fromisoformat(nascimento_raw.strip())
            except ValueError:
                return False, "Data de nascimento inválida.", None

        if not dt_nasc:
            return False, "Data de nascimento inválida.", None

        hoje = date.today()
        idade = hoje.year - dt_nasc.year - ((hoje.month, hoje.day) < (dt_nasc.month, dt_nasc.day))
        if idade < 18:
            return False, "O cadastro exige idade mínima de 18 anos.", None

        # 6. Gravação na mesma transação (Regra 07 / Documentação Seção 2.1)
        try:
            # 6.1 Criar Usuário
            novo_usuario = Usuario(
                NOME=nome,
                SOBRENOME=sobrenome,
                EMAIL=email,
                SENHA_HASH=hash_password(senha),
                NASCIMENTO=dt_nasc,
                CPF=cpf,
                TELEFONE=telefone,
                ATIVO=True,
                IS_ADM=False,
            )
            db.add(novo_usuario)
            db.flush()  # obtém novo_usuario.ID

            # 6.2 Criar Endereços
            for idx, end_data in enumerate(enderecos):
                cep_clean = clean_digits(end_data.get("cep"))
                comp_raw = end_data.get("complemento")
                comp_val = str(comp_raw)[:80] if comp_raw else None
                novo_end = EnderecoUsuario(
                    FK_USUARIO=novo_usuario.ID,
                    NOME=str(end_data.get("nome", f"Endereço {idx + 1}"))[:50],
                    CEP=cep_clean[:8],
                    LOGRADOURO=str(end_data.get("logradouro", ""))[:120],
                    NUMERO=str(end_data.get("numero", ""))[:10],
                    COMPLEMENTO=comp_val,
                    BAIRRO=str(end_data.get("bairro", ""))[:80],
                    CIDADE=str(end_data.get("cidade", ""))[:60],
                    ESTADO=str(end_data.get("estado", "SP"))[:2].upper(),
                    ATIVO=True,
                )
                db.add(novo_end)

            # 6.3 Criar Carrinho Ativo inicial
            carrinho = Carrinho(
                FK_USUARIO=novo_usuario.ID,
                STATUS="ATIVO",
                TOTAL=Decimal("0.00"),
                FRETE_GRATIS=False,
            )
            db.add(carrinho)

            # 6.4 Marcar token de e-mail como expirado/utilizado
            token_hashed = hash_token(codigo_verificacao)
            db.execute(
                update(VerificacaoEmail)
                .where(VerificacaoEmail.EMAIL == email, VerificacaoEmail.TOKEN == token_hashed)
                .values(EXPIRADO=True)
            )

            db.commit()
            return True, None, novo_usuario
        except Exception as e:
            db.rollback()
            logger.error("Erro na transação de cadastro: %s", e)
            return False, "Ocorreu um erro ao salvar o cadastro. Tente novamente.", None
