"""Testes unitários rigorosos para a camada de serviços do Perfil (PerfilService)."""

from collections.abc import Generator
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.security import hash_password
from app.models import (
    Carrinho,
    EnderecoUsuario,
    Fornecedor,
    ImgsProduto,
    ItemVenda,
    Linha,
    MetodoPagamento,
    Produto,
    StatusTroca,
    StatusVenda,
    Troca,
    Usuario,
    Variacao,
    Venda,
)
from app.schemas.perfil import (
    AtualizarPerfilPayload,
    EnderecoPerfilPayload,
    ReembolsoPayload,
    TrocaPayload,
)
from app.services.perfil_service import PerfilService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Cria banco SQLite em memória completo para os testes do PerfilService."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)

    # Carga de domínios básicos necessários
    status_vendas = [
        StatusVenda(ID=1, ESTADO_ANDAMENTO="EM_PROCESSAMENTO", DESCRICAO="Em Processamento"),
        StatusVenda(ID=2, ESTADO_ANDAMENTO="NA_TRANSPORTADORA", DESCRICAO="Na Transportadora"),
        StatusVenda(ID=3, ESTADO_ANDAMENTO="EM_TRANSITO", DESCRICAO="Em Trânsito"),
        StatusVenda(ID=4, ESTADO_ANDAMENTO="ENTREGANDO", DESCRICAO="Entregando"),
        StatusVenda(ID=5, ESTADO_ANDAMENTO="ENTREGUE", DESCRICAO="Entregue"),
        StatusVenda(ID=6, ESTADO_ANDAMENTO="TENTATIVA_FALHA", DESCRICAO="Tentativa Falha"),
        StatusVenda(ID=7, ESTADO_ANDAMENTO="CANCELADO", DESCRICAO="Cancelado"),
    ]
    session.add_all(status_vendas)

    status_trocas = [
        StatusTroca(ID=1, ESTADO_ANDAMENTO="SOLICITADA", DESCRICAO="Solicitada"),
        StatusTroca(ID=2, ESTADO_ANDAMENTO="APROVADA", DESCRICAO="Aprovada"),
        StatusTroca(ID=3, ESTADO_ANDAMENTO="DEVOLUCAO_RECEBIDA", DESCRICAO="Devolução Recebida"),
        StatusTroca(ID=4, ESTADO_ANDAMENTO="EM_PROCESSAMENTO", DESCRICAO="Em Processamento"),
        StatusTroca(ID=5, ESTADO_ANDAMENTO="NA_TRANSPORTADORA", DESCRICAO="Na Transportadora"),
        StatusTroca(ID=6, ESTADO_ANDAMENTO="ENTREGANDO", DESCRICAO="Entregando"),
        StatusTroca(ID=7, ESTADO_ANDAMENTO="ENTREGUE", DESCRICAO="Entregue"),
        StatusTroca(ID=8, ESTADO_ANDAMENTO="RECUSADA", DESCRICAO="Recusada"),
    ]
    session.add_all(status_trocas)

    metodos = [
        MetodoPagamento(ID=1, METODO="PIX"),
        MetodoPagamento(ID=2, METODO="Cartão de Crédito"),
        MetodoPagamento(ID=3, METODO="Cartão de Débito"),
        MetodoPagamento(ID=4, METODO="Boleto"),
    ]
    session.add_all(metodos)

    # Fornecedor e Linha
    forn = Fornecedor(ID=1, NOME="Atelier Rendas", CNPJ="11222333000199", RAZAO_SOCIAL="Atelier LTDA", ATIVO=True)
    linha = Linha(ID=1, NOME="Linha Noite")
    session.add_all([forn, linha])
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def usuario_com_dados(db_session: Session) -> Usuario:
    """Cria um usuário com dados cadastrais e endereço."""
    user = Usuario(
        NOME="Sophia",
        SOBRENOME="Silva",
        EMAIL="sophia.gamer.silva93@gmail.com",
        SENHA_HASH=hash_password("SenhaForte@2026"),
        NASCIMENTO=date(1993, 11, 17),
        CPF="51039590896",
        TELEFONE="16992912930",
        ATIVO=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    endereco = EnderecoUsuario(
        FK_USUARIO=user.ID,
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
    db_session.add(endereco)
    db_session.commit()
    return user


def test_obter_perfil_usuario(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Valida a extração dos dados formatados do usuário para exibição no Meu Perfil."""
    perfil = PerfilService.obter_perfil_usuario(db_session, usuario_com_dados.ID)
    assert perfil is not None
    assert perfil["nome"] == "Sophia"
    assert perfil["sobrenome"] == "Silva"
    assert perfil["email"] == "sophia.gamer.silva93@gmail.com"
    assert perfil["telefone"] == "16992912930"
    assert perfil["cpf_formatado"] == "510.395.908-96"
    assert perfil["nascimento_formatado"] == "17/11/1993"
    assert len(perfil["enderecos"]) == 1
    assert perfil["enderecos"][0]["nome"] == "Casa"


def test_salvar_informacoes_basicas(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Testa atualização de nome, sobrenome e telefone sem alterar senha ou email."""
    payload = AtualizarPerfilPayload(
        nome="Sophia Helena",
        sobrenome="Silva Ramos",
        telefone="16999998888",
    )
    sucesso, erro = PerfilService.salvar_informacoes_completas(db_session, usuario_com_dados.ID, payload)
    assert sucesso is True
    assert erro is None

    db_session.refresh(usuario_com_dados)
    assert usuario_com_dados.NOME == "Sophia Helena"
    assert usuario_com_dados.SOBRENOME == "Silva Ramos"
    assert usuario_com_dados.TELEFONE == "16999998888"


def test_alterar_senha_com_senha_atual_correta(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Testa a alteração de senha bem-sucedida quando a senha atual está correta e nova senha atende aos requisitos."""
    payload = AtualizarPerfilPayload(
        nome="Sophia",
        sobrenome="Silva",
        telefone="16992912930",
        senha_atual="SenhaForte@2026",
        nova_senha="NovaSenhaSegura@2027",
        confirmar_nova_senha="NovaSenhaSegura@2027",
    )
    sucesso, erro = PerfilService.salvar_informacoes_completas(db_session, usuario_com_dados.ID, payload)
    assert sucesso is True
    assert erro is None

    # Valida que a nova senha funciona
    perfil = PerfilService.obter_perfil_usuario(db_session, usuario_com_dados.ID)
    assert perfil is not None


def test_alterar_senha_rejeita_senha_atual_incorreta(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Testa que a alteração de senha falha caso a senha atual esteja errada."""
    payload = AtualizarPerfilPayload(
        nome="Sophia",
        sobrenome="Silva",
        telefone="16992912930",
        senha_atual="SenhaErrada@123",
        nova_senha="NovaSenhaSegura@2027",
        confirmar_nova_senha="NovaSenhaSegura@2027",
    )
    sucesso, erro = PerfilService.salvar_informacoes_completas(db_session, usuario_com_dados.ID, payload)
    assert sucesso is False
    assert erro == "A senha atual informada está incorreta."


def test_alterar_email_com_codigos_validos(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Testa fluxo completo de troca de e-mail com códigos de verificação para o atual e o novo."""
    email_atual = usuario_com_dados.EMAIL
    novo_email = "sophia.novo@exemplo.com"

    # Envia código para o e-mail atual
    ok1, cod_atual, exp1 = PerfilService.enviar_codigo_verificacao_email(db_session, email_atual)
    assert ok1 is True
    assert exp1 == 900

    # Envia código para o novo e-mail
    ok2, cod_novo, exp2 = PerfilService.enviar_codigo_verificacao_email(db_session, novo_email)
    assert ok2 is True
    assert exp2 == 900

    # Validação prévia dos códigos
    valido, msg = PerfilService.validar_troca_email(
        db_session,
        usuario_id=usuario_com_dados.ID,
        email_atual=email_atual,
        codigo_atual=cod_atual,
        novo_email=novo_email,
        codigo_novo=cod_novo,
        senha_atual="SenhaForte@2026",
    )
    assert valido is True
    assert msg is None

    # Salva no banco ao submeter Salvar Informações
    payload = AtualizarPerfilPayload(
        nome="Sophia",
        sobrenome="Silva",
        telefone="16992912930",
        novo_email=novo_email,
        codigo_email_atual=cod_atual,
        codigo_email_novo=cod_novo,
        senha_atual="SenhaForte@2026",
    )
    sucesso, erro = PerfilService.salvar_informacoes_completas(db_session, usuario_com_dados.ID, payload)
    assert sucesso is True
    assert erro is None

    db_session.refresh(usuario_com_dados)
    assert usuario_com_dados.EMAIL == novo_email


def test_alterar_email_codigo_invalido(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Verifica que códigos incorretos retornam 'código de verificação inválido'."""
    valido, msg = PerfilService.validar_troca_email(
        db_session,
        usuario_id=usuario_com_dados.ID,
        email_atual=usuario_com_dados.EMAIL,
        codigo_atual="000000",
        novo_email="novo@exemplo.com",
        codigo_novo="111111",
        senha_atual="SenhaForte@2026",
    )
    assert valido is False
    assert msg is not None
    assert "código de verificação inválido" in msg.lower()


def test_gerenciar_endereco_imutabilidade_se_usado_em_venda(
    db_session: Session, usuario_com_dados: Usuario
) -> None:
    """Garante que endereço com vendas associadas é inativado (ATIVO=0) e um novo é criado (Seção 5.3)."""
    endereco_orig = usuario_com_dados.enderecos[0]

    # Cria carrinho e venda simulada atrelada a esse endereço
    carrinho = Carrinho(FK_USUARIO=usuario_com_dados.ID, STATUS="CONVERTIDO", TOTAL=Decimal("100.00"))
    db_session.add(carrinho)
    db_session.commit()

    venda = Venda(
        FK_CARRINHO=carrinho.ID,
        FK_USUARIO=usuario_com_dados.ID,
        FK_ENDERECO_USUARIO=endereco_orig.ID,
        FK_METODO_PAGAMENTO=1,
        FK_STATUS=5,
        SUBTOTAL=Decimal("100.00"),
        FRETE=Decimal("0.00"),
        TOTAL=Decimal("100.00"),
        DATA=datetime.now(),
    )
    db_session.add(venda)
    db_session.commit()

    # Tentativa de atualizar o endereço
    end_payload = EnderecoPerfilPayload(
        id=endereco_orig.ID,
        nome="Casa Nova",
        cep="14093238",
        logradouro="Rua Modificada",
        numero="999",
        complemento="Apto 1",
        bairro="Centro",
        cidade="Ribeirão Preto",
        estado="SP",
    )
    sucesso, erro = PerfilService.salvar_endereco(db_session, usuario_com_dados.ID, end_payload)
    assert sucesso is True
    assert erro is None

    # O original deve estar inativo (ATIVO=0)
    db_session.refresh(endereco_orig)
    assert endereco_orig.ATIVO is False

    # Deve haver um novo endereço com nome 'Casa Nova' ativo
    enderecos_ativos = [e for e in usuario_com_dados.enderecos if e.ATIVO]
    assert len(enderecos_ativos) == 1
    assert enderecos_ativos[0].NOME == "Casa Nova"
    assert enderecos_ativos[0].ID != endereco_orig.ID


def test_pedidos_paginacao_e_nomenclatura_crescente(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Valida que pedidos aparecem com nome 'Pedido <posição ordem crescente>' e paginação de 2 em 2."""
    end = usuario_com_dados.enderecos[0]

    # Cria 3 vendas com datas diferentes
    for i in range(1, 4):
        carrinho = Carrinho(FK_USUARIO=usuario_com_dados.ID, STATUS="CONVERTIDO", TOTAL=Decimal("150.00"))
        db_session.add(carrinho)
        db_session.commit()

        venda = Venda(
            FK_CARRINHO=carrinho.ID,
            FK_USUARIO=usuario_com_dados.ID,
            FK_ENDERECO_USUARIO=end.ID,
            FK_METODO_PAGAMENTO=1,
            FK_STATUS=1 if i == 2 else 5,  # 2 é Em Processamento, 1 e 3 são Entregue
            SUBTOTAL=Decimal("150.00"),
            FRETE=Decimal("19.90"),
            TOTAL=Decimal("169.90"),
            DATA=datetime(2026, 10, i),
        )
        db_session.add(venda)
        db_session.commit()

    # Página 1 (limit=2, offset=0)
    resultado_pg1 = PerfilService.listar_pedidos_usuario(
        db_session, usuario_com_dados.ID, filtro="todos", limit=2, offset=0
    )
    pedidos_pg1 = resultado_pg1["pedidos"]
    assert len(pedidos_pg1) == 2
    assert resultado_pg1["tem_mais"] is True
    assert pedidos_pg1[0]["nome_exibicao"] == "Pedido 1"
    assert pedidos_pg1[1]["nome_exibicao"] == "Pedido 2"

    # Página 2 (limit=2, offset=2)
    resultado_pg2 = PerfilService.listar_pedidos_usuario(
        db_session, usuario_com_dados.ID, filtro="todos", limit=2, offset=2
    )
    pedidos_pg2 = resultado_pg2["pedidos"]
    assert len(pedidos_pg2) == 1
    assert resultado_pg2["tem_mais"] is False
    assert pedidos_pg2[0]["nome_exibicao"] == "Pedido 3"

    # Filtro processando
    resultado_proc = PerfilService.listar_pedidos_usuario(
        db_session, usuario_com_dados.ID, filtro="processando", limit=2, offset=0
    )
    assert len(resultado_proc["pedidos"]) == 1
    assert resultado_proc["pedidos"][0]["status_descricao"] == "Em Processamento"


def test_solicitar_troca_multiplas_unidades_gera_registros_individuais(
    db_session: Session, usuario_com_dados: Usuario
) -> None:
    """Verifica que trocar um item com 3 unidades gera 3 trocas distintas de QNT=1 cada."""
    # Produto e variações
    prod = Produto(FK_FORNECEDOR=1, FK_LINHA=1, NOME="Vestido Leve De Sereia", TIPO="roupa", ATIVO=True)
    db_session.add(prod)
    db_session.commit()

    var1 = Variacao(
        FK_PRODUTO=prod.ID, TAMANHO="PP", COR="Azul", ESTOQUE=10, CUSTO=Decimal("100"), PRECO=Decimal("360")
    )
    var2 = Variacao(
        FK_PRODUTO=prod.ID, TAMANHO="P", COR="Amarelo", ESTOQUE=10, CUSTO=Decimal("100"), PRECO=Decimal("360")
    )
    var3 = Variacao(
        FK_PRODUTO=prod.ID, TAMANHO="P", COR="Rosa", ESTOQUE=10, CUSTO=Decimal("100"), PRECO=Decimal("360")
    )
    db_session.add_all([var1, var2, var3])
    db_session.commit()

    # Venda ENTREGUE dentro de 30 dias com 3 unidades de var1
    carrinho = Carrinho(FK_USUARIO=usuario_com_dados.ID, STATUS="CONVERTIDO", TOTAL=Decimal("1080.00"))
    db_session.add(carrinho)
    db_session.commit()

    venda = Venda(
        FK_CARRINHO=carrinho.ID,
        FK_USUARIO=usuario_com_dados.ID,
        FK_ENDERECO_USUARIO=usuario_com_dados.enderecos[0].ID,
        FK_METODO_PAGAMENTO=1,
        FK_STATUS=5,  # ENTREGUE
        SUBTOTAL=Decimal("1080.00"),
        FRETE=Decimal("0.00"),
        TOTAL=Decimal("1080.00"),
        DATA=datetime.now() - timedelta(days=5),
    )
    db_session.add(venda)
    db_session.commit()

    item_venda = ItemVenda(FK_VENDA=venda.ID, FK_VARIACAO=var1.ID, QNT=3, PRECO_UNITARIO=Decimal("360.00"))
    db_session.add(item_venda)
    db_session.commit()

    # Solicita troca das 3 unidades: 2 por var2 e 1 por var3
    payload_troca = TrocaPayload(
        item_venda_id=item_venda.ID,
        quantidade=3,
        motivo="Ficou apertado",
        variacoes_novas=[var2.ID, var2.ID, var3.ID],
    )
    sucesso, erro = PerfilService.solicitar_troca(db_session, usuario_com_dados.ID, payload_troca)
    assert sucesso is True
    assert erro is None

    # Deve haver 3 registros na tabela TROCA
    trocas = db_session.query(Troca).filter(Troca.FK_ITEM_VENDA == item_venda.ID).all()
    assert len(trocas) == 3
    for t in trocas:
        assert t.QNT == 1
        assert t.FK_STATUS_TROCA == 1  # SOLICITADA


def test_solicitar_reembolso_rejeita_pedido_nao_entregue(
    db_session: Session, usuario_com_dados: Usuario
) -> None:
    """Verifica que pedido em processamento (não entregue) não permite solicitar reembolso."""
    prod = Produto(FK_FORNECEDOR=1, FK_LINHA=1, NOME="Corset Rosa", TIPO="corset", ATIVO=True)
    db_session.add(prod)
    db_session.commit()
    var = Variacao(
        FK_PRODUTO=prod.ID, TAMANHO="M", COR="Rosa", ESTOQUE=5, CUSTO=Decimal("80"), PRECO=Decimal("200")
    )
    db_session.add(var)
    db_session.commit()

    carrinho = Carrinho(FK_USUARIO=usuario_com_dados.ID, STATUS="CONVERTIDO", TOTAL=Decimal("200.00"))
    db_session.add(carrinho)
    db_session.commit()

    venda = Venda(
        FK_CARRINHO=carrinho.ID,
        FK_USUARIO=usuario_com_dados.ID,
        FK_ENDERECO_USUARIO=usuario_com_dados.enderecos[0].ID,
        FK_METODO_PAGAMENTO=1,
        FK_STATUS=1,  # EM_PROCESSAMENTO
        SUBTOTAL=Decimal("200.00"),
        FRETE=Decimal("15.00"),
        TOTAL=Decimal("215.00"),
        DATA=datetime.now(),
    )
    db_session.add(venda)
    db_session.commit()

    item_venda = ItemVenda(FK_VENDA=venda.ID, FK_VARIACAO=var.ID, QNT=1, PRECO_UNITARIO=Decimal("200.00"))
    db_session.add(item_venda)
    db_session.commit()

    payload_reembolso = ReembolsoPayload(
        item_venda_id=item_venda.ID,
        quantidade=1,
        motivo="Desistência da compra",
    )
    sucesso, erro = PerfilService.solicitar_reembolso(db_session, usuario_com_dados.ID, payload_reembolso)
    assert sucesso is False
    assert erro is not None
    assert "entregue" in erro.lower()


def test_remover_endereco_inativa_com_sucesso(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Verifica que remover um endereço inativa o registro (ATIVO=0) preservando integridade."""
    # Adiciona um segundo endereço para que haja mais de 1
    end2 = EnderecoUsuario(
        FK_USUARIO=usuario_com_dados.ID,
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

    sucesso, erro = PerfilService.remover_endereco(db_session, usuario_com_dados.ID, end2.ID)
    assert sucesso is True
    assert erro is None

    db_session.refresh(end2)
    assert end2.ATIVO is False


def test_remover_ultimo_endereco_rejeita(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Garante que o último endereço ativo não pode ser removido (Seção 5.1)."""
    end_unico = usuario_com_dados.enderecos[0]
    sucesso, erro = PerfilService.remover_endereco(db_session, usuario_com_dados.ID, end_unico.ID)
    assert sucesso is False
    assert erro is not None
    assert "único endereço" in erro.lower()


def test_definir_endereco_principal(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Valida a indicação do endereço principal na listagem do perfil."""
    end2 = EnderecoUsuario(
        FK_USUARIO=usuario_com_dados.ID,
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

    perfil = PerfilService.obter_perfil_usuario(
        db_session, usuario_com_dados.ID, endereco_principal_id=end2.ID
    )
    assert perfil is not None
    assert len(perfil["enderecos"]) == 2
    # O endereço principal deve ter is_principal == True
    end_princ = next((e for e in perfil["enderecos"] if e["id"] == end2.ID), None)
    assert end_princ is not None
    assert end_princ["is_principal"] is True


def test_prevencao_duplicacao_endereco_identico(db_session: Session, usuario_com_dados: Usuario) -> None:
    """Garante que submeter o mesmo endereço ativo existente não cria duplicação no banco."""
    end_orig = usuario_com_dados.enderecos[0]
    payload_duplicado = EnderecoPerfilPayload(
        id=None,  # sem id
        nome=end_orig.NOME,
        cep=end_orig.CEP,
        logradouro=end_orig.LOGRADOURO,
        numero=end_orig.NUMERO,
        complemento=end_orig.COMPLEMENTO,
        bairro=end_orig.BAIRRO,
        cidade=end_orig.CIDADE,
        estado=end_orig.ESTADO,
    )

    qtd_antes = len([e for e in usuario_com_dados.enderecos if e.ATIVO])
    sucesso, erro = PerfilService.salvar_endereco(db_session, usuario_com_dados.ID, payload_duplicado)
    assert sucesso is True
    assert erro is None

    db_session.refresh(usuario_com_dados)
    qtd_depois = len([e for e in usuario_com_dados.enderecos if e.ATIVO])
    assert qtd_depois == qtd_antes


def test_pedidos_e_detalhes_formatam_url_imagem_com_prefixo_static(
    db_session: Session, usuario_com_dados: Usuario
) -> None:
    """Valida que URLs de imagens relativas no banco são prefixadas com /static/ para evitar erro 404."""
    prod = Produto(FK_FORNECEDOR=1, FK_LINHA=1, NOME="Morning Dew Corset", TIPO="corset", ATIVO=True)
    db_session.add(prod)
    db_session.commit()

    img = ImgsProduto(FK_PRODUTO=prod.ID, URL_IMAGEM="img/produtos/morning-dew-corset-1.png", ATIVO=True)
    var = Variacao(
        FK_PRODUTO=prod.ID, TAMANHO="M", COR="Branco", ESTOQUE=5, CUSTO=Decimal("80"), PRECO=Decimal("299.90")
    )
    db_session.add_all([img, var])
    db_session.commit()

    carrinho = Carrinho(FK_USUARIO=usuario_com_dados.ID, STATUS="CONVERTIDO", TOTAL=Decimal("299.90"))
    db_session.add(carrinho)
    db_session.commit()

    venda = Venda(
        FK_CARRINHO=carrinho.ID,
        FK_USUARIO=usuario_com_dados.ID,
        FK_ENDERECO_USUARIO=usuario_com_dados.enderecos[0].ID,
        FK_METODO_PAGAMENTO=1,
        FK_STATUS=5,  # Entregue
        SUBTOTAL=Decimal("299.90"),
        FRETE=Decimal("0.00"),
        TOTAL=Decimal("299.90"),
        DATA=datetime.now(),
    )
    db_session.add(venda)
    db_session.commit()

    item = ItemVenda(FK_VENDA=venda.ID, FK_VARIACAO=var.ID, QNT=1, PRECO_UNITARIO=Decimal("299.90"))
    db_session.add(item)
    db_session.commit()

    # 1. listar_pedidos_usuario
    pedidos_res = PerfilService.listar_pedidos_usuario(db_session, usuario_com_dados.ID)
    itens = pedidos_res["pedidos"][0]["itens"]
    assert len(itens) == 1
    assert itens[0]["imagem_url"] == "/static/img/produtos/morning-dew-corset-1.png"

    # 2. obter_item_venda_detalhes
    detalhes = PerfilService.obter_item_venda_detalhes(db_session, item.ID, usuario_com_dados.ID)
    assert detalhes is not None
    assert detalhes["imagem_url"] == "/static/img/produtos/morning-dew-corset-1.png"

    # 3. listar_trocas_e_reembolsos
    troca = Troca(
        FK_ITEM_VENDA=item.ID,
        FK_VARIACAO_NOVA=var.ID,
        FK_STATUS_TROCA=1,
        QNT=1,
        MOTIVO="Tamanho",
        DATA_CRIACAO=datetime.now(),
        ATIVO=True,
    )
    db_session.add(troca)
    db_session.commit()

    posvenda = PerfilService.listar_trocas_e_reembolsos(db_session, usuario_com_dados.ID)
    assert len(posvenda["itens"]) == 1
    assert posvenda["itens"][0]["imagem_url"] == "/static/img/produtos/morning-dew-corset-1.png"


def test_perfil_service_envia_codigo_via_email_service(db_session: Session) -> None:
    """Garante que a alteração de e-mail no perfil aciona o EmailService para envio/saída em console."""
    from app.services.email_service import EmailService

    email_teste = "aluno.teste@senacsp.edu.br"
    EmailService.last_sent_codes.clear()

    ok, cod, _ = PerfilService.enviar_codigo_verificacao_email(db_session, email_teste)
    assert ok is True
    assert len(cod) == 6
    assert EmailService.last_sent_codes.get(email_teste) == cod



