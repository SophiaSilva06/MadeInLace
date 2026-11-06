from __future__ import annotations

import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.core.config import settings

logger = logging.getLogger("madeinlace.email")


class EmailService:
    """Serviço de envio de e-mails para autenticação e recuperação de contas.

    Suporta:
    1. Modo 'console' (padrão estudantil): Seguro, offline, não depende de senhas nem portas bloqueadas em laboratórios.
    2. Modo 'smtp': Envio real via Gmail (smtp.gmail.com) ou Outlook/Hotmail/Office365 (smtp-mail.outlook.com) com TLS 587.
    3. Modo 'brevo': Envio via API transacional HTTP (Porta 443), imune a bloqueios de portas SMTP de faculdades.
    """

    # Memória temporária para fins de testes e inspeção rápida em ambiente acadêmico
    last_sent_codes: dict[str, str] = {}

    @classmethod
    def send_verification_email(cls, to_email: str, code: str) -> bool:
        """Envia o código de verificação para autenticação de e-mail no cadastro."""
        subject = "Made In Lace — Código de Verificação de Cadastro"
        plain_body = (
            f"Olá!\n\n"
            f"Seu código de verificação para concluir o cadastro na Made In Lace é: {code}\n\n"
            f"Este código expira em 15 minutos.\n"
            f"Se você não solicitou este código, por favor desconsidere este e-mail.\n"
        )
        html_body = f"""
        <div style="font-family: 'Playfair Display', Georgia, serif; background-color: #EEE6D3; padding: 24px; color: #2D1D13;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #ECCBB5; border: 1.5px solid #512E11; padding: 32px; text-align: center;">
                <h1 style="color: #4A2E19; font-size: 24px; margin-bottom: 16px;">Made In Lace</h1>
                <p style="font-size: 16px; color: #2D1D13; margin-bottom: 24px;">Código de Autenticação de E-mail</p>
                <div style="background-color: #512E11; color: #F6EFE5; font-size: 32px; letter-spacing: 6px; padding: 16px; font-weight: bold; margin-bottom: 24px;">
                    {code}
                </div>
                <p style="font-size: 13px; color: #5F422E;">Válido por 15 minutos. Não compartilhe com ninguém.</p>
            </div>
        </div>
        """
        return cls._send(to_email=to_email, subject=subject, plain_text=plain_body, html_text=html_body, code=code)

    @classmethod
    def send_password_recovery_email(cls, to_email: str, code: str) -> bool:
        """Envia o código/token de recuperação de senha."""
        subject = "Made In Lace — Recuperação de Conta"
        plain_body = (
            f"Olá!\n\n"
            f"Recebemos uma solicitação para redefinir a senha da sua conta Made In Lace.\n"
            f"Seu código de recuperação é: {code}\n\n"
            f"Este código tem validade de 1 hora.\n"
            f"Se você não solicitou a redefinição, proteja sua conta e ignore este e-mail.\n"
        )
        html_body = f"""
        <div style="font-family: 'Playfair Display', Georgia, serif; background-color: #EEE6D3; padding: 24px; color: #2D1D13;">
            <div style="max-width: 500px; margin: 0 auto; background-color: #ECCBB5; border: 1.5px solid #512E11; padding: 32px; text-align: center;">
                <h1 style="color: #4A2E19; font-size: 24px; margin-bottom: 16px;">Made In Lace</h1>
                <p style="font-size: 16px; color: #2D1D13; margin-bottom: 24px;">Recuperação de Acesso</p>
                <div style="background-color: #512E11; color: #F6EFE5; font-size: 32px; letter-spacing: 6px; padding: 16px; font-weight: bold; margin-bottom: 24px;">
                    {code}
                </div>
                <p style="font-size: 13px; color: #5F422E;">Válido por 1 hora. Insira na tela de recuperação da loja.</p>
            </div>
        </div>
        """
        return cls._send(to_email=to_email, subject=subject, plain_text=plain_body, html_text=html_body, code=code)

    @classmethod
    def _send(cls, to_email: str, subject: str, plain_text: str, html_text: str, code: str) -> bool:
        """Roteia o envio de acordo com a configuração ativa."""
        cls.last_sent_codes[to_email.strip().lower()] = code

        mode = (settings.email_mode or "console").lower()

        # 1. Modo Console / Mock (ideal para apresentação acadêmica e testes)
        if mode == "console" or (not settings.smtp_user and not settings.brevo_api_key):
            banner = (
                "\n" + "=" * 60 + "\n"
                " [SIMULAÇÃO DE E-MAIL MADEINLACE]\n"
                f" Para:    {to_email}\n"
                f" Assunto: {subject}\n"
                f" CÓDIGO:  {code}\n"
                + "=" * 60 + "\n"
            )
            print(banner, flush=True)
            logger.info("[SIMULAÇÃO DE E-MAIL MADEINLACE] Para: %s | CÓDIGO: %s", to_email, code)
            return True

        # 2. Modo API Transacional (Brevo - Porta 443 HTTPS, imune a bloqueio de portas)
        if mode == "brevo" and settings.brevo_api_key:
            try:
                url = "https://api.brevo.com/v3/smtp/email"
                sender_email = settings.brevo_sender_email or settings.smtp_user or "contato@madeinlace.com"
                payload = {
                    "sender": {"name": "Made In Lace", "email": sender_email},
                    "to": [{"email": to_email}],
                    "subject": subject,
                    "htmlContent": html_text,
                    "textContent": plain_text,
                }
                headers = {
                    "api-key": settings.brevo_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                }
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(url, json=payload, headers=headers)
                    if resp.status_code in (200, 201, 202):
                        return True
                    logger.warning("Falha ao enviar via Brevo API: %s %s", resp.status_code, resp.text)
            except Exception as e:
                logger.error("Erro na comunicação com a API do Brevo: %s", e)

        # 3. Modo SMTP TLS (Gmail, Outlook, Hotmail, Microsoft 365)
        if mode == "smtp" and settings.smtp_user and settings.smtp_password:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.email_from
                msg["To"] = to_email

                part1 = MIMEText(plain_text, "plain", "utf-8")
                part2 = MIMEText(html_text, "html", "utf-8")
                msg.attach(part1)
                msg.attach(part2)

                context = ssl.create_default_context()
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.ehlo()
                    server.login(settings.smtp_user, settings.smtp_password)
                    server.sendmail(settings.email_from, [to_email], msg.as_string())
                return True
            except (smtplib.SMTPException, OSError) as err:
                logger.warning(
                    "Falha ao enviar e-mail via SMTP (%s:%s). "
                    "Rede de laboratório pode estar bloqueando portas SMTP 587/465: %s",
                    settings.smtp_host,
                    settings.smtp_port,
                    err,
                )

        # Fallback resiliente: loga no console caso o SMTP falhe na rede do laboratório
        print(f"\n[FALLBACK CONSOLE] E-mail para {to_email} | Código: {code}\n", flush=True)
        logger.info("[FALLBACK CONSOLE] E-mail para %s | Código: %s", to_email, code)
        return True
