from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.security import (
    clean_digits,
    generate_verification_code,
    hash_password,
    hash_token,
    validate_password_strength,
    verify_password,
)
from app.core.templates import formatar_moeda
from app.models.pos_venda import HistoricoStatusTroca, Reembolso, Troca
from app.models.produto import Variacao
from app.models.usuario import EnderecoUsuario, Usuario, VerificacaoEmail
from app.models.venda import ItemVenda, Venda
from app.schemas.perfil import (
    AtualizarPerfilPayload,
    EnderecoPerfilPayload,
    ReembolsoPayload,
    TrocaPayload,
)
from app.services.email_service import EmailService


class PerfilService:
    """Serviço centralizador de regras de negócio, persistência e auditoria do Meu Perfil."""

    @staticmethod
    def formatar_url_imagem(url: str | None) -> str:
        """Garante que caminhos relativos de imagem sejam prefixados com /static/ para evitar erro 404."""
        if not url or not url.strip():
            return "/static/img/site/MadeInLaceLogo.png"
        url_limpa = url.strip()
        if (
            url_limpa.startswith("http://")
            or url_limpa.startswith("https://")
            or url_limpa.startswith("/static/")
        ):
            return url_limpa
        if url_limpa.startswith("/"):
            return f"/static{url_limpa}"
        return f"/static/{url_limpa}"

    @staticmethod
    def obter_perfil_usuario(
        db: Session, usuario_id: int, endereco_principal_id: int | None = None
    ) -> dict[str, Any] | None:
        """Busca os dados do cliente com CPF e nascimento devidamente formatados."""
        stmt = (
            select(Usuario)
            .options(selectinload(Usuario.enderecos))
            .where(Usuario.ID == usuario_id, Usuario.ATIVO.is_(True))
        )
        usuario = db.scalars(stmt).first()
        if not usuario:
            return None

        # Formatação de CPF: 51039590896 -> 510.395.908-96
        cpf_limpo = clean_digits(usuario.CPF)
        cpf_fmt = (
            f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"
            if len(cpf_limpo) == 11
            else (usuario.CPF or "")
        )

        # Formatação de nascimento: 17/11/1993
        nasc_fmt = usuario.NASCIMENTO.strftime("%d/%m/%Y") if usuario.NASCIMENTO else ""

        # Identifica o endereço principal se selecionado
        ends_ativos = [e for e in usuario.enderecos if e.ATIVO]
        principal_id = endereco_principal_id
        if principal_id is None or not any(e.ID == principal_id for e in ends_ativos):
            principal_id = ends_ativos[0].ID if ends_ativos else None

        enderecos_formatados = [
            {
                "id": e.ID,
                "nome": e.NOME,
                "cep": f"{e.CEP[:5]}-{e.CEP[5:]}" if len(e.CEP) == 8 else e.CEP,
                "cep_raw": e.CEP,
                "logradouro": e.LOGRADOURO,
                "numero": e.NUMERO,
                "complemento": e.COMPLEMENTO or "",
                "bairro": e.BAIRRO,
                "cidade": e.CIDADE,
                "estado": e.ESTADO,
                "ativo": e.ATIVO,
                "is_principal": bool(e.ID == principal_id),
            }
            for e in ends_ativos
        ]

        # Garante que o endereço principal fique ordenado em primeiro lugar
        enderecos_formatados.sort(key=lambda x: not x["is_principal"])

        return {
            "id": usuario.ID,
            "nome": usuario.NOME,
            "sobrenome": usuario.SOBRENOME,
            "email": usuario.EMAIL,
            "telefone": usuario.TELEFONE or "",
            "cpf_formatado": cpf_fmt,
            "nascimento_formatado": nasc_fmt,
            "enderecos": enderecos_formatados,
            "endereco_principal_id": principal_id,
        }

    @staticmethod
    def enviar_codigo_verificacao_email(
        db: Session, email: str, tempo_expiracao_minutos: int = 15
    ) -> tuple[bool, str, int]:
        """Gera um código de 6 dígitos numéricos e persiste o hash SHA-256 em VERIFICACAO_EMAIL."""
        email_limpo = email.strip().lower()
        codigo = generate_verification_code(6)
        token_hash = hash_token(codigo)
        agora = datetime.now()
        expira = agora + timedelta(minutes=tempo_expiracao_minutos)

        # Invalida códigos anteriores ativos para este e-mail
        antigos = db.scalars(
            select(VerificacaoEmail).where(
                VerificacaoEmail.EMAIL == email_limpo,
                VerificacaoEmail.EXPIRADO.is_(False),
            )
        ).all()
        for a in antigos:
            a.EXPIRADO = True

        registro = VerificacaoEmail(
            EMAIL=email_limpo,
            TOKEN=token_hash,
            DATA_CRIACAO=agora,
            DATA_EXPIRA=expira,
            EXPIRADO=False,
            TENTATIVAS=0,
        )
        db.add(registro)
        db.commit()
        db.refresh(registro)

        duracao_segundos = int((registro.DATA_EXPIRA - registro.DATA_CRIACAO).total_seconds())

        # Envia e-mail / emite no terminal console
        EmailService.send_verification_email(email_limpo, codigo)
        return True, codigo, duracao_segundos

    @staticmethod
    def validar_codigo_verificacao(
        db: Session, email: str, codigo: str, marcar_usado: bool = False
    ) -> bool:
        """Confere se o hash SHA-256 do código bate com um token ativo em VERIFICACAO_EMAIL."""
        email_limpo = email.strip().lower()
        cod_limpo = codigo.strip()
        agora = datetime.now()

        registro = db.scalars(
            select(VerificacaoEmail)
            .where(
                VerificacaoEmail.EMAIL == email_limpo,
                VerificacaoEmail.EXPIRADO.is_(False),
                VerificacaoEmail.DATA_EXPIRA > agora,
            )
            .order_by(VerificacaoEmail.DATA_CRIACAO.desc())
        ).first()

        if not registro:
            return False

        registro.TENTATIVAS += 1
        esperado_hash = hash_token(cod_limpo)
        if registro.TOKEN == esperado_hash:
            if marcar_usado:
                registro.EXPIRADO = True
            db.commit()
            return True

        if registro.TENTATIVAS >= 5:
            registro.EXPIRADO = True

        db.commit()
        return False

    @staticmethod
    def validar_troca_email(
        db: Session,
        usuario_id: int,
        email_atual: str,
        codigo_atual: str,
        novo_email: str,
        codigo_novo: str,
        senha_atual: str,
        marcar_usados: bool = False,
    ) -> tuple[bool, str | None]:
        """Valida a senha atual e os dois códigos numéricos para liberar a troca de e-mail."""
        usuario = db.get(Usuario, usuario_id)
        if not usuario or not usuario.ATIVO:
            return False, "Usuário não localizado ou inativo."

        if not verify_password(senha_atual, usuario.SENHA_HASH):
            return False, "A senha atual informada está incorreta."

        novo_email_limpo = novo_email.strip().lower()
        if novo_email_limpo == usuario.EMAIL.lower():
            return False, "O novo e-mail não pode ser idêntico ao e-mail cadastrado atualmente."

        # Verifica unicidade do novo e-mail
        existente = db.scalars(
            select(Usuario).where(Usuario.EMAIL == novo_email_limpo, Usuario.ID != usuario_id)
        ).first()
        if existente:
            return False, "Este novo e-mail já está em uso por outro usuário."

        # Validação do código do e-mail atual
        if not PerfilService.validar_codigo_verificacao(
            db, email_atual, codigo_atual, marcar_usado=marcar_usados
        ):
            return False, "Código de verificação inválido para o e-mail atual."

        # Validação do código do novo e-mail
        if not PerfilService.validar_codigo_verificacao(
            db, novo_email_limpo, codigo_novo, marcar_usado=marcar_usados
        ):
            return False, "Código de verificação inválido para o novo e-mail."

        return True, None

    @staticmethod
    def salvar_endereco(
        db: Session, usuario_id: int, payload: EnderecoPerfilPayload
    ) -> tuple[bool, str | None]:
        """Salva ou modifica endereço garantindo a imutabilidade caso já tenha sido usado em venda."""
        cep_limpo = clean_digits(payload.cep)
        if len(cep_limpo) != 8:
            return False, "O CEP deve conter exatamente 8 dígitos numéricos."

        if payload.id:
            endereco_existente = db.scalars(
                select(EnderecoUsuario).where(
                    EnderecoUsuario.ID == payload.id,
                    EnderecoUsuario.FK_USUARIO == usuario_id,
                )
            ).first()

            if not endereco_existente:
                return False, "Endereço não localizado."

            # Verifica se já foi utilizado em alguma venda (Seção 5.3)
            venda_vinculada = db.scalars(
                select(Venda).where(Venda.FK_ENDERECO_USUARIO == payload.id)
            ).first()

            if venda_vinculada:
                # Imutável: inativa o antigo e cria novo
                endereco_existente.ATIVO = False
                novo_end = EnderecoUsuario(
                    FK_USUARIO=usuario_id,
                    NOME=payload.nome.strip(),
                    CEP=cep_limpo,
                    LOGRADOURO=payload.logradouro.strip(),
                    NUMERO=payload.numero.strip(),
                    COMPLEMENTO=payload.complemento.strip() if payload.complemento else None,
                    BAIRRO=payload.bairro.strip(),
                    CIDADE=payload.cidade.strip(),
                    ESTADO=payload.estado.strip().upper()[:2],
                    ATIVO=True,
                )
                db.add(novo_end)
            else:
                # Pode atualizar diretamente
                endereco_existente.NOME = payload.nome.strip()
                endereco_existente.CEP = cep_limpo
                endereco_existente.LOGRADOURO = payload.logradouro.strip()
                endereco_existente.NUMERO = payload.numero.strip()
                endereco_existente.COMPLEMENTO = (
                    payload.complemento.strip() if payload.complemento else None
                )
                endereco_existente.BAIRRO = payload.bairro.strip()
                endereco_existente.CIDADE = payload.cidade.strip()
                endereco_existente.ESTADO = payload.estado.strip().upper()[:2]
        else:
            # Novo endereço: previne duplicação se o usuário já tiver exatamente o mesmo endereço ativo
            duplicado = db.scalars(
                select(EnderecoUsuario).where(
                    EnderecoUsuario.FK_USUARIO == usuario_id,
                    EnderecoUsuario.ATIVO.is_(True),
                    EnderecoUsuario.CEP == cep_limpo,
                    EnderecoUsuario.NUMERO == payload.numero.strip(),
                    EnderecoUsuario.NOME == payload.nome.strip(),
                )
            ).first()
            if duplicado:
                # Já existe endereço idêntico cadastrado, não duplica
                return True, None

            total_ativos = db.scalars(
                select(EnderecoUsuario).where(
                    EnderecoUsuario.FK_USUARIO == usuario_id,
                    EnderecoUsuario.ATIVO.is_(True),
                )
            ).all()
            if len(total_ativos) >= 10:
                return False, "Limite máximo de 10 endereços ativos atingido."

            novo_end = EnderecoUsuario(
                FK_USUARIO=usuario_id,
                NOME=payload.nome.strip(),
                CEP=cep_limpo,
                LOGRADOURO=payload.logradouro.strip(),
                NUMERO=payload.numero.strip(),
                COMPLEMENTO=payload.complemento.strip() if payload.complemento else None,
                BAIRRO=payload.bairro.strip(),
                CIDADE=payload.cidade.strip(),
                ESTADO=payload.estado.strip().upper()[:2],
                ATIVO=True,
            )
            db.add(novo_end)

        db.commit()
        return True, None

    @staticmethod
    def remover_endereco(
        db: Session, usuario_id: int, endereco_id: int
    ) -> tuple[bool, str | None]:
        """Inativa logicamente um endereço do usuário garantindo que o último ativo não seja removido (Seção 5.1)."""
        endereco = db.scalars(
            select(EnderecoUsuario).where(
                EnderecoUsuario.ID == endereco_id,
                EnderecoUsuario.FK_USUARIO == usuario_id,
                EnderecoUsuario.ATIVO.is_(True),
            )
        ).first()
        if not endereco:
            return False, "Endereço não localizado ou já inativo."

        total_ativos = db.scalars(
            select(EnderecoUsuario).where(
                EnderecoUsuario.FK_USUARIO == usuario_id,
                EnderecoUsuario.ATIVO.is_(True),
            )
        ).all()
        if len(total_ativos) <= 1:
            return False, "Não é possível remover o único endereço ativo da conta."

        endereco.ATIVO = False
        db.commit()
        return True, None

    @staticmethod
    def salvar_informacoes_completas(
        db: Session, usuario_id: int, payload: AtualizarPerfilPayload
    ) -> tuple[bool, str | None]:
        """Persiste todas as alterações de nome, sobrenome, telefone, senha e e-mail no banco."""
        usuario = db.get(Usuario, usuario_id)
        if not usuario or not usuario.ATIVO:
            return False, "Usuário não localizado ou inativo."

        # 1. Atualização dos campos de perfil direto
        usuario.NOME = payload.nome.strip()
        usuario.SOBRENOME = payload.sobrenome.strip()
        if payload.telefone:
            usuario.TELEFONE = clean_digits(payload.telefone)

        # 2. Alteração de senha
        if payload.nova_senha:
            if not payload.senha_atual or not verify_password(payload.senha_atual, usuario.SENHA_HASH):
                return False, "A senha atual informada está incorreta."

            if payload.nova_senha != payload.confirmar_nova_senha:
                return False, "A confirmação da nova senha não confere."

            valida, msg_senha = validate_password_strength(payload.nova_senha, usuario.EMAIL)
            if not valida:
                return False, msg_senha or "Nova senha não atende aos requisitos de segurança."

            usuario.SENHA_HASH = hash_password(payload.nova_senha)

        # 3. Alteração de e-mail (se fornecido novo_email)
        if payload.novo_email and payload.novo_email.strip().lower() != usuario.EMAIL.lower():
            if not payload.senha_atual or not verify_password(payload.senha_atual, usuario.SENHA_HASH):
                return False, "A senha atual informada está incorreta para alteração de e-mail."

            if not payload.codigo_email_atual or not payload.codigo_email_novo:
                return False, "Códigos de verificação do e-mail atual e do novo são obrigatórios."

            valido_email, erro_email = PerfilService.validar_troca_email(
                db,
                usuario_id=usuario_id,
                email_atual=usuario.EMAIL,
                codigo_atual=payload.codigo_email_atual,
                novo_email=payload.novo_email,
                codigo_novo=payload.codigo_email_novo,
                senha_atual=payload.senha_atual,
                marcar_usados=True,
            )
            if not valido_email:
                return False, erro_email

            usuario.EMAIL = payload.novo_email.strip().lower()

        # 4. Endereços
        if payload.enderecos:
            for end in payload.enderecos:
                ok_end, err_end = PerfilService.salvar_endereco(db, usuario_id, end)
                if not ok_end:
                    return False, err_end

        db.commit()
        return True, None

    @staticmethod
    def listar_pedidos_usuario(
        db: Session, usuario_id: int, filtro: str = "todos", limit: int = 2, offset: int = 0
    ) -> dict[str, Any]:
        """Retorna pedidos paginados com nomenclatura 'Pedido <ordem crescente>' e carrossel de itens."""
        # Busca todas as vendas do usuário ordenadas por DATA crescente para fixar o número do pedido
        stmt_todas = (
            select(Venda)
            .options(
                joinedload(Venda.status),
                joinedload(Venda.metodo_pagamento),
                joinedload(Venda.endereco_usuario),
                selectinload(Venda.itens).joinedload(ItemVenda.variacao).joinedload(Variacao.produto).selectinload(Variacao.produto.property.mapper.class_.imagens),  # type: ignore[attr-defined]
            )
            .where(Venda.FK_USUARIO == usuario_id)
            .order_by(Venda.DATA.asc(), Venda.ID.asc())
        )
        todas_vendas = db.scalars(stmt_todas).unique().all()

        pedidos_completos = []
        agora = datetime.now()

        for idx, venda in enumerate(todas_vendas, start=1):
            status_desc = venda.status.DESCRICAO if venda.status else "Pendente"
            status_estado = venda.status.ESTADO_ANDAMENTO if venda.status else ""

            # Filtro
            if filtro == "processando" and status_estado != "EM_PROCESSAMENTO":
                continue
            if filtro == "enviados" and status_estado not in (
                "NA_TRANSPORTADORA",
                "EM_TRANSITO",
                "ENTREGANDO",
            ):
                continue

            itens_formatados = []
            for item in venda.itens:
                prod = item.variacao.produto if item.variacao else None
                nome_prod = prod.NOME if prod else "Produto MadeInLace"
                raw_img = prod.imagens[0].URL_IMAGEM if (prod and prod.imagens) else None
                img_url = PerfilService.formatar_url_imagem(raw_img)

                # Verifica se pedido é entregue e elegível para troca/reembolso (<= 30 dias)
                dias_desde_pedido = (agora - venda.DATA).days if venda.DATA else 999
                pode_trocar_reembolsar = (status_estado == "ENTREGUE") and (dias_desde_pedido <= 30)

                # Quantidade já solicitada em trocas e reembolsos
                qtd_trocada = sum(
                    t.QNT
                    for t in db.scalars(select(Troca).where(Troca.FK_ITEM_VENDA == item.ID, Troca.ATIVO.is_(True))).all()
                )
                qtd_reembolsada = sum(
                    r.QNT
                    for r in db.scalars(
                        select(Reembolso).where(Reembolso.FK_ITEM_VENDA == item.ID, Reembolso.ATIVO.is_(True))
                    ).all()
                )
                qtd_disponivel = max(0, item.QNT - (qtd_trocada + qtd_reembolsada))

                itens_formatados.append(
                    {
                        "item_venda_id": item.ID,
                        "produto_nome": nome_prod,
                        "imagem_url": img_url,
                        "tamanho": item.variacao.TAMANHO if item.variacao else "-",
                        "cor": item.variacao.COR if item.variacao else "-",
                        "quantidade": item.QNT,
                        "quantidade_disponivel": qtd_disponivel,
                        "preco_unitario_formatado": formatar_moeda(item.PRECO_UNITARIO).replace("R$ ", ""),
                        "pode_trocar_reembolsar": pode_trocar_reembolsar and (qtd_disponivel > 0),
                    }
                )

            end_nome = (
                venda.endereco_usuario.NOME
                if venda.endereco_usuario
                else f"Endereço {idx}"
            )
            metodo_nome = (
                venda.metodo_pagamento.METODO
                if venda.metodo_pagamento
                else "PIX"
            )

            pedidos_completos.append(
                {
                    "venda_id": venda.ID,
                    "numero_sequencial": idx,
                    "nome_exibicao": f"Pedido {idx}",
                    "data_formatada": venda.DATA.strftime("%d/%m/%Y") if venda.DATA else "",
                    "endereco_nome": end_nome,
                    "metodo_pagamento": metodo_nome,
                    "frete_formatado": formatar_moeda(venda.FRETE).replace("R$ ", ""),
                    "preco_total_formatado": formatar_moeda(venda.TOTAL).replace("R$ ", ""),
                    "status_descricao": status_desc,
                    "status_estado": status_estado,
                    "itens": itens_formatados,
                }
            )

        total_filtrados = len(pedidos_completos)
        paginados = pedidos_completos[offset : offset + limit]
        tem_mais = total_filtrados > (offset + limit)

        return {
            "pedidos": paginados,
            "total": total_filtrados,
            "tem_mais": tem_mais,
        }

    @staticmethod
    def obter_item_venda_detalhes(db: Session, item_venda_id: int, usuario_id: int) -> dict[str, Any] | None:
        """Retorna detalhes do item de venda e variações disponíveis para o modal de troca/reembolso."""
        stmt = (
            select(ItemVenda)
            .options(
                joinedload(ItemVenda.venda),
                joinedload(ItemVenda.variacao).joinedload(Variacao.produto).selectinload(Variacao.produto.property.mapper.class_.imagens),  # type: ignore[attr-defined]
                joinedload(ItemVenda.variacao).joinedload(Variacao.produto).selectinload(Variacao.produto.property.mapper.class_.variacoes),  # type: ignore[attr-defined]
            )
            .where(ItemVenda.ID == item_venda_id)
        )
        item = db.scalars(stmt).unique().first()
        if not item or not item.venda or item.venda.FK_USUARIO != usuario_id:
            return None

        prod = item.variacao.produto
        nome_prod = prod.NOME if prod else "Produto MadeInLace"
        raw_img = prod.imagens[0].URL_IMAGEM if (prod and prod.imagens) else None
        img_url = PerfilService.formatar_url_imagem(raw_img)

        # Quantidade já solicitada em trocas/reembolsos
        qtd_trocada = sum(
            t.QNT for t in db.scalars(select(Troca).where(Troca.FK_ITEM_VENDA == item.ID, Troca.ATIVO.is_(True))).all()
        )
        qtd_reembolsada = sum(
            r.QNT
            for r in db.scalars(
                select(Reembolso).where(Reembolso.FK_ITEM_VENDA == item.ID, Reembolso.ATIVO.is_(True))
            ).all()
        )
        qtd_disponivel = max(0, item.QNT - (qtd_trocada + qtd_reembolsada))

        # Variações ativas do produto para troca
        variacoes_disponiveis = []
        if prod and prod.variacoes:
            for v in prod.variacoes:
                if v.ATIVO and v.ESTOQUE > 0:
                    variacoes_disponiveis.append(
                        {
                            "id": v.ID,
                            "tamanho": v.TAMANHO,
                            "cor": v.COR,
                            "estoque": v.ESTOQUE,
                        }
                    )

        return {
            "item_venda_id": item.ID,
            "produto_nome": nome_prod,
            "imagem_url": img_url,
            "tamanho": item.variacao.TAMANHO,
            "cor": item.variacao.COR,
            "quantidade": item.QNT,
            "quantidade_disponivel": qtd_disponivel,
            "preco_unitario_formatado": formatar_moeda(item.PRECO_UNITARIO).replace("R$ ", ""),
            "variacoes_disponiveis": variacoes_disponiveis,
        }

    @staticmethod
    def solicitar_troca(
        db: Session, usuario_id: int, payload: TrocaPayload
    ) -> tuple[bool, str | None]:
        """Cria solicitações de troca individualizando cada unidade (QNT=1) para rastreio exato."""
        item = db.get(ItemVenda, payload.item_venda_id)
        if not item or not item.venda or item.venda.FK_USUARIO != usuario_id:
            return False, "Item de venda não localizado para o cliente."

        venda = item.venda
        if not venda.status or venda.status.ESTADO_ANDAMENTO != "ENTREGUE":
            return False, "Trocas só podem ser solicitadas para pedidos com status Entregue."

        dias = (datetime.now() - venda.DATA).days if venda.DATA else 999
        if dias > 30:
            return False, "O prazo de 30 dias após a entrega para solicitar trocas expirou."

        qtd_trocada = sum(
            t.QNT for t in db.scalars(select(Troca).where(Troca.FK_ITEM_VENDA == item.ID, Troca.ATIVO.is_(True))).all()
        )
        qtd_reembolsada = sum(
            r.QNT
            for r in db.scalars(
                select(Reembolso).where(Reembolso.FK_ITEM_VENDA == item.ID, Reembolso.ATIVO.is_(True))
            ).all()
        )
        disponivel = item.QNT - (qtd_trocada + qtd_reembolsada)
        if payload.quantidade > disponivel:
            return False, f"Quantidade máxima disponível para troca é de {disponivel} unidade(s)."

        if len(payload.variacoes_novas) != payload.quantidade:
            return False, "É necessário selecionar uma variação para cada unidade a trocar."

        # Para cada unidade, gera uma troca individual com QNT=1
        agora = datetime.now()
        for var_id in payload.variacoes_novas:
            nova_troca = Troca(
                FK_ITEM_VENDA=item.ID,
                FK_STATUS_TROCA=1,  # SOLICITADA
                FK_VARIACAO_NOVA=var_id,
                QNT=1,
                MOTIVO=payload.motivo.strip() if payload.motivo else None,
                DATA_CRIACAO=agora,
                ATIVO=True,
                CONCLUSAO=False,
            )
            db.add(nova_troca)
            db.flush()

            hist = HistoricoStatusTroca(
                FK_TROCA=nova_troca.ID,
                FK_STATUS_TROCA=1,
                DATA_EVENTO=agora,
            )
            db.add(hist)

        db.commit()
        return True, None

    @staticmethod
    def solicitar_reembolso(
        db: Session, usuario_id: int, payload: ReembolsoPayload
    ) -> tuple[bool, str | None]:
        """Cria solicitações de reembolso individualizando cada unidade (QNT=1) para rastreio exato."""
        item = db.get(ItemVenda, payload.item_venda_id)
        if not item or not item.venda or item.venda.FK_USUARIO != usuario_id:
            return False, "Item de venda não localizado para o cliente."

        venda = item.venda
        if not venda.status or venda.status.ESTADO_ANDAMENTO != "ENTREGUE":
            return False, "Reembolsos só podem ser solicitados para pedidos com status Entregue."

        dias = (datetime.now() - venda.DATA).days if venda.DATA else 999
        if dias > 30:
            return False, "O prazo de 30 dias após a entrega para solicitar reembolso expirou."

        if not payload.motivo or not payload.motivo.strip():
            return False, "O motivo do reembolso é obrigatório."

        qtd_trocada = sum(
            t.QNT for t in db.scalars(select(Troca).where(Troca.FK_ITEM_VENDA == item.ID, Troca.ATIVO.is_(True))).all()
        )
        qtd_reembolsada = sum(
            r.QNT
            for r in db.scalars(
                select(Reembolso).where(Reembolso.FK_ITEM_VENDA == item.ID, Reembolso.ATIVO.is_(True))
            ).all()
        )
        disponivel = item.QNT - (qtd_trocada + qtd_reembolsada)
        if payload.quantidade > disponivel:
            return False, f"Quantidade máxima disponível para reembolso é de {disponivel} unidade(s)."

        agora = datetime.now()
        for _ in range(payload.quantidade):
            novo_reembolso = Reembolso(
                FK_ITEM_VENDA=item.ID,
                QNT=1,
                MOTIVO=payload.motivo.strip(),
                DATA_CRIACAO=agora,
                ATIVO=True,
                CONCLUSAO=False,
            )
            db.add(novo_reembolso)

        db.commit()
        return True, None

    @staticmethod
    def listar_trocas_e_reembolsos(
        db: Session, usuario_id: int, limit: int = 2, offset: int = 0
    ) -> dict[str, Any]:
        """Retorna a lista unificada de trocas e reembolsos paginados de 2 em 2."""
        # 1. Trocas
        stmt_trocas = (
            select(Troca)
            .options(
                joinedload(Troca.status_troca),
                joinedload(Troca.variacao_nova),
                joinedload(Troca.item_venda)
                .joinedload(ItemVenda.variacao)
                .joinedload(Variacao.produto)
                .selectinload(Variacao.produto.property.mapper.class_.imagens),  # type: ignore[attr-defined]
            )
            .join(ItemVenda, Troca.FK_ITEM_VENDA == ItemVenda.ID)
            .join(Venda, ItemVenda.FK_VENDA == Venda.ID)
            .where(Venda.FK_USUARIO == usuario_id, Troca.ATIVO.is_(True))
            .order_by(Troca.DATA_CRIACAO.asc(), Troca.ID.asc())
        )
        todas_trocas = db.scalars(stmt_trocas).unique().all()

        # 2. Reembolsos
        stmt_reembolsos = (
            select(Reembolso)
            .options(
                joinedload(Reembolso.item_venda)
                .joinedload(ItemVenda.variacao)
                .joinedload(Variacao.produto)
                .selectinload(Variacao.produto.property.mapper.class_.imagens),  # type: ignore[attr-defined]
            )
            .join(ItemVenda, Reembolso.FK_ITEM_VENDA == ItemVenda.ID)
            .join(Venda, ItemVenda.FK_VENDA == Venda.ID)
            .where(Venda.FK_USUARIO == usuario_id, Reembolso.ATIVO.is_(True))
            .order_by(Reembolso.DATA_CRIACAO.asc(), Reembolso.ID.asc())
        )
        todos_reembolsos = db.scalars(stmt_reembolsos).unique().all()

        # Agrupa e formata
        itens_pos_venda = []
        for idx, t in enumerate(todas_trocas, start=1):
            prod = (
                t.item_venda.variacao.produto
                if (t.item_venda and t.item_venda.variacao)
                else None
            )
            raw_img_t = prod.imagens[0].URL_IMAGEM if (prod and prod.imagens) else None
            img_url = PerfilService.formatar_url_imagem(raw_img_t)

            status_str = t.status_troca.DESCRICAO if t.status_troca else "Solicitada"
            data_conc = t.DATA_CONCLUSAO.strftime("%d/%m/%Y") if t.DATA_CONCLUSAO else "-"

            itens_pos_venda.append(
                {
                    "tipo": "troca",
                    "id": t.ID,
                    "titulo": f"Troca {idx}",
                    "imagem_url": img_url,
                    "data_criacao": t.DATA_CRIACAO.strftime("%d/%m/%Y") if t.DATA_CRIACAO else "",
                    "data_criacao_raw": t.DATA_CRIACAO,
                    "status": status_str,
                    "data_conclusao": data_conc,
                    "novo_tamanho": t.variacao_nova.TAMANHO if t.variacao_nova else "-",
                    "nova_cor": t.variacao_nova.COR if t.variacao_nova else "-",
                }
            )

        for idx, r in enumerate(todos_reembolsos, start=1):
            prod = (
                r.item_venda.variacao.produto
                if (r.item_venda and r.item_venda.variacao)
                else None
            )
            raw_img_r = prod.imagens[0].URL_IMAGEM if (prod and prod.imagens) else None
            img_url = PerfilService.formatar_url_imagem(raw_img_r)

            data_conc = r.DATA_CONCLUSAO.strftime("%d/%m/%Y") if r.DATA_CONCLUSAO else "-"

            itens_pos_venda.append(
                {
                    "tipo": "reembolso",
                    "id": r.ID,
                    "titulo": f"Reembolso {idx}",
                    "imagem_url": img_url,
                    "data_criacao": r.DATA_CRIACAO.strftime("%d/%m/%Y") if r.DATA_CRIACAO else "",
                    "data_criacao_raw": r.DATA_CRIACAO,
                    "concluido": "Sim" if r.CONCLUSAO else "Não",
                    "data_conclusao": data_conc,
                }
            )

        # Ordenação consistente
        itens_pos_venda.sort(key=lambda x: str(x.get("data_criacao_raw", "")))
        total = len(itens_pos_venda)
        paginados = itens_pos_venda[offset : offset + limit]
        tem_mais = total > (offset + limit)

        return {
            "itens": paginados,
            "total": total,
            "tem_mais": tem_mais,
        }
