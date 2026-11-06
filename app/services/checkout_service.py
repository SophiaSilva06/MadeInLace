from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.templates import formatar_moeda
from app.models.carrinho import Carrinho, ItemCarrinho
from app.models.dominio import MetodoPagamento, StatusVenda
from app.models.produto import Produto, Variacao
from app.models.usuario import EnderecoUsuario, Usuario
from app.models.venda import HistoricoStatusVenda, ItemVenda, Venda
from app.schemas.checkout import SalvarEnderecoCheckoutPayload
from app.services.carrinho_service import CarrinhoService

# ==============================================================================
# TABELA DE FRETE OFICIAL — ANEXO A (docs/MadeInLace_Documentacao.md)
# ==============================================================================
TABELA_FRETE_ANEXO_A: dict[str, Decimal] = {
    # Sudeste
    "SP": Decimal("14.90"),
    "RJ": Decimal("19.90"),
    "MG": Decimal("21.90"),
    "ES": Decimal("24.90"),
    # Sul
    "PR": Decimal("22.90"),
    "SC": Decimal("24.90"),
    "RS": Decimal("27.90"),
    # Centro-Oeste
    "DF": Decimal("29.90"),
    "GO": Decimal("29.90"),
    "MS": Decimal("31.90"),
    "MT": Decimal("34.90"),
    # Nordeste
    "BA": Decimal("34.90"),
    "SE": Decimal("36.90"),
    "AL": Decimal("37.90"),
    "PE": Decimal("37.90"),
    "PB": Decimal("38.90"),
    "RN": Decimal("39.90"),
    "CE": Decimal("39.90"),
    "PI": Decimal("41.90"),
    "MA": Decimal("42.90"),
    # Norte
    "TO": Decimal("38.90"),
    "PA": Decimal("44.90"),
    "RO": Decimal("47.90"),
    "AC": Decimal("52.90"),
    "AM": Decimal("54.90"),
    "AP": Decimal("56.90"),
    "RR": Decimal("59.90"),
}

META_FRETE_GRATIS = Decimal("160.00")


class CheckoutService:
    """Regras de negócio, cálculos tributários/promocionais e persistência de checkout."""

    @staticmethod
    def formatar_url_imagem(url: str | None) -> str:
        """Garante que caminhos relativos de imagem sejam prefixados com /static/ para evitar erro 404."""
        if not url or not url.strip():
            return "/static/img/site/MadeInLaceLogo.png"
        url_limpa = url.strip()
        if url_limpa.startswith("http://") or url_limpa.startswith("https://") or url_limpa.startswith("/static/"):
            return url_limpa
        if url_limpa.startswith("/"):
            return f"/static{url_limpa}"
        return f"/static/{url_limpa}"

    @classmethod
    def verificar_primeira_compra(cls, db: Session, usuario_id: int) -> bool:
        """Verifica se o usuário não possui nenhuma venda anterior com status diferente de CANCELADO."""
        stmt = (
            select(func.count(Venda.ID))
            .join(StatusVenda, Venda.FK_STATUS == StatusVenda.ID)
            .where(
                Venda.FK_USUARIO == usuario_id,
                StatusVenda.ESTADO_ANDAMENTO != "CANCELADO",
            )
        )
        total_vendas = db.scalar(stmt) or 0
        return bool(total_vendas == 0)

    @classmethod
    def obter_resumo_checkout(
        cls,
        db: Session,
        usuario_id: int,
        endereco_id_selecionado: int | None = None,
    ) -> dict[str, Any]:
        """Calcula todos os valores e consolida os dados para renderização da tela de pagamento."""
        stmt_carrinho = (
            select(Carrinho)
            .where(Carrinho.FK_USUARIO == usuario_id, Carrinho.STATUS == "ATIVO")
            .options(
                selectinload(Carrinho.itens)
                .joinedload(ItemCarrinho.variacao)
                .joinedload(Variacao.produto)
                .selectinload(Produto.imagens)
            )
        )
        carrinho = db.scalar(stmt_carrinho)
        if not carrinho or not carrinho.itens or len(carrinho.itens) == 0:
            raise ValueError("Carrinho vazio ou inexistente.")

        # Recalcula preços unitários a partir do catálogo
        subtotal = Decimal("0.00")
        itens_dto = []
        for item in carrinho.itens:
            if not item.variacao or not item.variacao.ATIVO:
                continue
            preco_unit = CarrinhoService.calcular_preco_unitario(item.variacao)
            item.PRECO_UNITARIO = preco_unit
            sub_item = (preco_unit * Decimal(item.QNT)).quantize(Decimal("0.01"))
            subtotal += sub_item

            # Identifica imagem principal do produto com caminho seguro /static/
            raw_img = "/static/img/site/MadeInLaceLogo.png"
            if item.variacao.produto and item.variacao.produto.imagens:
                for img in item.variacao.produto.imagens:
                    if getattr(img, "ATIVO", True):
                        raw_img = img.URL_IMAGEM
                        break
            img_url = cls.formatar_url_imagem(raw_img)

            itens_dto.append(
                {
                    "item_carrinho_id": item.ID,
                    "variacao_id": item.variacao.ID,
                    "produto_id": item.variacao.produto.ID if item.variacao.produto else 0,
                    "nome": item.variacao.produto.NOME if item.variacao.produto else "Produto",
                    "tamanho": item.variacao.TAMANHO,
                    "cor": item.variacao.COR,
                    "qnt": item.QNT,
                    "preco_unitario": preco_unit,
                    "preco_unitario_formatado": formatar_moeda(preco_unit),
                    "subtotal": sub_item,
                    "subtotal_formatado": formatar_moeda(sub_item),
                    "imagem_url": img_url,
                }
            )

        if len(itens_dto) == 0:
            raise ValueError("Carrinho não possui itens válidos.")

        # Verifica elegibilidade aos 10% de desconto na primeira compra
        primeira_compra = cls.verificar_primeira_compra(db, usuario_id)
        if primeira_compra:
            valor_desconto = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
            subtotal_com_desconto = (subtotal * Decimal("0.90")).quantize(Decimal("0.01"))
        else:
            valor_desconto = Decimal("0.00")
            subtotal_com_desconto = subtotal

        base_frete = subtotal - valor_desconto

        # Busca endereços ativos do usuário
        stmt_enderecos = (
            select(EnderecoUsuario)
            .where(
                EnderecoUsuario.FK_USUARIO == usuario_id,
                EnderecoUsuario.ATIVO.is_(True),
            )
            .order_by(EnderecoUsuario.ID.asc())
        )
        enderecos = list(db.scalars(stmt_enderecos).all())

        # Seleção automática do endereço principal
        endereco_selecionado: EnderecoUsuario | None = None
        if endereco_id_selecionado:
            for end in enderecos:
                if end.ID == endereco_id_selecionado:
                    endereco_selecionado = end
                    break

        if not endereco_selecionado and len(enderecos) > 0:
            endereco_selecionado = enderecos[0]

        # Cálculo de Frete
        frete_gratis = bool(base_frete >= META_FRETE_GRATIS)
        if frete_gratis or not endereco_selecionado:
            frete = Decimal("0.00")
        else:
            uf = endereco_selecionado.ESTADO.strip().upper()
            frete = TABELA_FRETE_ANEXO_A.get(uf, Decimal("25.00"))

        total = (subtotal_com_desconto + frete).quantize(Decimal("0.01"))

        # Métodos de pagamento do banco
        metodos_stmt = select(MetodoPagamento).order_by(MetodoPagamento.ID.asc())
        metodos_db = list(db.scalars(metodos_stmt).all())
        metodos_dto = []
        for m in metodos_db:
            nome_m = m.METODO
            nome_lower = nome_m.lower()
            if "pix" in nome_lower:
                slug = "pix"
                label = "PIX"
            elif "boleto" in nome_lower:
                slug = "boleto"
                label = "Boleto"
            elif "crédito" in nome_lower or "credito" in nome_lower:
                slug = "credito"
                label = "Crédito"
            elif "débito" in nome_lower or "debito" in nome_lower:
                slug = "debito"
                label = "Débito"
            else:
                slug = f"metodo-{m.ID}"
                label = m.METODO

            metodos_dto.append(
                {
                    "id": m.ID,
                    "metodo": m.METODO,
                    "label": label,
                    "slug": slug,
                }
            )

        enderecos_dto = [
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
                "is_selected": bool(endereco_selecionado and e.ID == endereco_selecionado.ID),
            }
            for e in enderecos
        ]

        endereco_sel_dto = None
        if endereco_selecionado:
            endereco_sel_dto = {
                "id": endereco_selecionado.ID,
                "nome": endereco_selecionado.NOME,
                "cep": f"{endereco_selecionado.CEP[:5]}-{endereco_selecionado.CEP[5:]}"
                if len(endereco_selecionado.CEP) == 8
                else endereco_selecionado.CEP,
                "logradouro": endereco_selecionado.LOGRADOURO,
                "numero": endereco_selecionado.NUMERO,
                "complemento": endereco_selecionado.COMPLEMENTO or "",
                "bairro": endereco_selecionado.BAIRRO,
                "cidade": endereco_selecionado.CIDADE,
                "estado": endereco_selecionado.ESTADO,
            }

        return {
            "subtotal": subtotal,
            "subtotal_formatado": formatar_moeda(subtotal),
            "primeira_compra": primeira_compra,
            "valor_desconto": valor_desconto,
            "valor_desconto_formatado": formatar_moeda(valor_desconto),
            "frete": frete,
            "frete_formatado": formatar_moeda(frete),
            "frete_gratis": frete_gratis,
            "total": total,
            "total_formatado": formatar_moeda(total),
            "endereco_selecionado": endereco_sel_dto,
            "enderecos_usuario": enderecos_dto,
            "itens": itens_dto,
            "metodos_pagamento": metodos_dto,
        }

    @classmethod
    def resolver_metodo_pagamento(cls, db: Session, metodo_input: str) -> MetodoPagamento:
        """Resolve flexivelmente o método de pagamento a partir do texto ou slug."""
        metodo_limpo = metodo_input.strip().lower()
        stmt = select(MetodoPagamento)
        todos = list(db.scalars(stmt).all())
        if not todos:
            raise ValueError("Nenhum método de pagamento cadastrado no sistema.")

        # 1. Correspondência exata ou por substring
        for m in todos:
            m_low = m.METODO.strip().lower()
            if metodo_limpo == m_low:
                return m

        # 2. Mapeamento dos 4 métodos do projeto
        for m in todos:
            m_low = m.METODO.strip().lower()
            if metodo_limpo == "pix" and "pix" in m_low:
                return m
            if metodo_limpo == "boleto" and "boleto" in m_low:
                return m
            if metodo_limpo in ("crédito", "credito") and ("crédito" in m_low or "credito" in m_low):
                return m
            if metodo_limpo in ("débito", "debito") and ("débito" in m_low or "debito" in m_low):
                return m

        # Se não achou, retorna o primeiro
        return todos[0]

    @classmethod
    def salvar_endereco_checkout(
        cls, db: Session, usuario_id: int, payload: SalvarEnderecoCheckoutPayload
    ) -> EnderecoUsuario:
        """Cria ou atualiza um endereço a partir do modal 'Modificar Endereços'."""
        cep_limpo = payload.cep.replace("-", "").strip()
        if len(cep_limpo) != 8 or not cep_limpo.isdigit():
            raise ValueError("CEP deve conter 8 dígitos numéricos.")

        # Verifica limite de 10 endereços ativos
        stmt_count = select(func.count(EnderecoUsuario.ID)).where(
            EnderecoUsuario.FK_USUARIO == usuario_id,
            EnderecoUsuario.ATIVO.is_(True),
        )
        if (db.scalar(stmt_count) or 0) >= 10 and not payload.id:
            raise ValueError("Limite máximo de 10 endereços ativos atingido.")

        if payload.id:
            end_existente = db.get(EnderecoUsuario, payload.id)
            if not end_existente or end_existente.FK_USUARIO != usuario_id:
                raise ValueError("Endereço não encontrado ou não pertence ao usuário.")

            # Verifica imutabilidade de endereço usado em venda
            venda_vinculada = db.scalar(select(Venda.ID).where(Venda.FK_ENDERECO_USUARIO == payload.id))
            if venda_vinculada:
                end_existente.ATIVO = False
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
                db.refresh(novo_end)
                return novo_end

            # Pode editar direto se nunca foi usado em venda
            end_existente.NOME = payload.nome.strip()
            end_existente.CEP = cep_limpo
            end_existente.LOGRADOURO = payload.logradouro.strip()
            end_existente.NUMERO = payload.numero.strip()
            end_existente.COMPLEMENTO = payload.complemento.strip() if payload.complemento else None
            end_existente.BAIRRO = payload.bairro.strip()
            end_existente.CIDADE = payload.cidade.strip()
            end_existente.ESTADO = payload.estado.strip().upper()[:2]
            db.commit()
            db.refresh(end_existente)
            return end_existente

        # Novo endereço
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
        db.refresh(novo_end)
        return novo_end

    @classmethod
    def finalizar_compra(
        cls,
        db: Session,
        usuario_id: int,
        endereco_id: int,
        metodo_pagamento: str,
    ) -> Venda:
        """Processa a venda simulada com transação estrita, bloqueio de linha, decremento de estoque e histórico."""
        # 1. Valida Usuário
        usuario = db.get(Usuario, usuario_id)
        if not usuario or not usuario.ATIVO:
            raise ValueError("Usuário inválido ou inativo.")

        # 2. Valida Endereço
        endereco = db.get(EnderecoUsuario, endereco_id)
        if not endereco or endereco.FK_USUARIO != usuario_id or not endereco.ATIVO:
            raise ValueError("Endereço de entrega inválido ou não pertence ao usuário.")

        # 3. Valida Carrinho Ativo
        stmt_carrinho = (
            select(Carrinho)
            .where(Carrinho.FK_USUARIO == usuario_id, Carrinho.STATUS == "ATIVO")
            .options(selectinload(Carrinho.itens).joinedload(ItemCarrinho.variacao))
        )
        carrinho = db.scalar(stmt_carrinho)
        if not carrinho or not carrinho.itens or len(carrinho.itens) == 0:
            raise ValueError("Não há itens no carrinho para finalizar a compra.")

        # 4. Resolve Método de Pagamento
        metodo_db = cls.resolver_metodo_pagamento(db, metodo_pagamento)

        # 5. Resolve Status Inicial (EM_PROCESSAMENTO)
        stmt_status = select(StatusVenda).where(StatusVenda.ESTADO_ANDAMENTO == "EM_PROCESSAMENTO")
        status_inicial = db.scalar(stmt_status)
        if not status_inicial:
            status_inicial = db.scalars(select(StatusVenda)).first()
            if not status_inicial:
                raise ValueError("Status inicial de venda não configurado no banco.")

        # 6. Validação Concorrente de Estoque
        var_ids = [item.FK_VARIACAO for item in carrinho.itens]
        stmt_vars = select(Variacao).where(Variacao.ID.in_(var_ids))
        if db.bind and db.bind.dialect.name == "mysql":
            stmt_vars = stmt_vars.with_for_update()

        vars_dict = {v.ID: v for v in db.scalars(stmt_vars).all()}

        for item in carrinho.itens:
            var = vars_dict.get(item.FK_VARIACAO)
            if not var or not var.ATIVO:
                raise ValueError(f"Produto indisponível (variação {item.FK_VARIACAO}).")
            if var.ESTOQUE < item.QNT:
                raise ValueError(
                    f"Estoque insuficiente para a variação {item.FK_VARIACAO}. "
                    f"Disponível: {var.ESTOQUE}, Solicitado: {item.QNT}."
                )

        # 7. Cálculo Financeiro
        subtotal = Decimal("0.00")
        itens_para_gravar = []
        for item in carrinho.itens:
            var = vars_dict[item.FK_VARIACAO]
            preco_unit = CarrinhoService.calcular_preco_unitario(var)
            sub_item = (preco_unit * Decimal(item.QNT)).quantize(Decimal("0.01"))
            subtotal += sub_item
            itens_para_gravar.append((var, item.QNT, preco_unit))

        primeira_compra = cls.verificar_primeira_compra(db, usuario_id)
        if primeira_compra:
            valor_desconto = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))
            subtotal_com_desconto = (subtotal * Decimal("0.90")).quantize(Decimal("0.01"))
            desconto_flag = True
        else:
            valor_desconto = Decimal("0.00")
            subtotal_com_desconto = subtotal
            desconto_flag = False

        base_frete = subtotal - valor_desconto
        frete_gratis = bool(base_frete >= META_FRETE_GRATIS)
        if frete_gratis:
            frete = Decimal("0.00")
        else:
            uf = endereco.ESTADO.strip().upper()
            frete = TABELA_FRETE_ANEXO_A.get(uf, Decimal("25.00"))

        total = (subtotal_com_desconto + frete).quantize(Decimal("0.01"))

        # 8. Persistência da VENDA
        venda = Venda(
            FK_CARRINHO=carrinho.ID,
            FK_USUARIO=usuario_id,
            FK_ENDERECO_USUARIO=endereco.ID,
            FK_METODO_PAGAMENTO=metodo_db.ID,
            FK_STATUS=status_inicial.ID,
            SUBTOTAL=subtotal,
            FRETE=frete,
            DESCONTO=desconto_flag,
            TOTAL=total,
            FRETE_GRATIS=frete_gratis,
            DATA=datetime.now(),
        )
        db.add(venda)
        db.flush()  # Obtém venda.ID

        # 9. Histórico de Status da Venda
        historico = HistoricoStatusVenda(
            FK_VENDA=venda.ID,
            FK_STATUS_VENDA=status_inicial.ID,
            DATA_EVENTO=datetime.now(),
        )
        db.add(historico)

        # 10. Persistência de ITEM_VENDA e Decremento de Estoque
        for var, qnt, preco_unit in itens_para_gravar:
            item_venda = ItemVenda(
                FK_VENDA=venda.ID,
                FK_VARIACAO=var.ID,
                QNT=qnt,
                PRECO_UNITARIO=preco_unit,
            )
            db.add(item_venda)

            # Consome estoque físico
            var.ESTOQUE = max(0, var.ESTOQUE - qnt)

        # 11. Conversão e esvaziamento do carrinho
        carrinho.STATUS = "CONVERTIDO"
        for item in list(carrinho.itens):
            db.delete(item)
        carrinho.TOTAL = Decimal("0.00")

        db.commit()

        # Recarrega relacionamentos essenciais
        stmt_reload = (
            select(Venda)
            .where(Venda.ID == venda.ID)
            .options(
                joinedload(Venda.metodo_pagamento),
                joinedload(Venda.status),
                selectinload(Venda.itens),
                selectinload(Venda.historico_status),
            )
        )
        venda_recarregada = db.scalar(stmt_reload)
        return venda_recarregada or venda
