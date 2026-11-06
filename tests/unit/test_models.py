"""Testes unitários rigorosos para os 24 modelos ORM do MadeInLace."""

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.core.database import Base
from app.models import (
    Avaliacao,
    Carrinho,
    EmailsFornecedor,
    EnderecoFornecedor,
    EnderecoUsuario,
    Fornecedor,
    HistoricoStatusTroca,
    HistoricoStatusVenda,
    ImgsAvaliacao,
    ImgsProduto,
    ItemCarrinho,
    ItemVenda,
    Linha,
    MetodoPagamento,
    Produto,
    Recuperacao,
    Reembolso,
    StatusTroca,
    StatusVenda,
    TelefoneFornecedor,
    Troca,
    Usuario,
    Variacao,
    Venda,
    VerificacaoEmail,
)

TABELAS_ESPERADAS = {
    "LINHA",
    "METODO_PAGAMENTO",
    "STATUS_VENDA",
    "STATUS_TROCA",
    "FORNECEDORES",
    "EMAILS_FORNECEDOR",
    "TELEFONE_FORNECEDOR",
    "ENDERECO_FORNECEDOR",
    "PRODUTOS",
    "IMGS_PRODUTOS",
    "VARIACAO",
    "USUARIOS",
    "ENDERECO_USUARIO",
    "RECUPERACAO",
    "VERIFICACAO_EMAIL",
    "CARRINHO",
    "ITEM_CARRINHO",
    "VENDA",
    "HISTORICO_STATUS_VENDA",
    "ITEM_VENDA",
    "TROCA",
    "HISTORICO_STATUS_TROCA",
    "REEMBOLSO",
    "AVALIACAO",
    "IMGS_AVALIACAO",
}


def test_todas_as_25_tabelas_registradas_no_metadata() -> None:
    """Valida se todas as 25 tabelas de db/schema.sql estão presentes no MetaData."""
    tabelas_registradas = set(Base.metadata.tables.keys())
    assert tabelas_registradas == TABELAS_ESPERADAS
    assert len(tabelas_registradas) == 25


def test_fidelidade_colunas_obrigatorias_e_pk() -> None:
    """Verifica se cada tabela possui PK ID e tipos essenciais."""
    for table_name in TABELAS_ESPERADAS:
        table = Base.metadata.tables[table_name]
        assert "ID" in table.c, f"Tabela {table_name} deve possuir coluna ID"
        col_id = table.c["ID"]
        assert col_id.primary_key, f"Coluna ID na tabela {table_name} deve ser chave primária"


def test_colunas_especificas_por_tabela() -> None:
    """Valida as colunas exatas e nulabilidade de tabelas centrais conforme o schema."""
    # PRODUTOS
    produtos = Base.metadata.tables["PRODUTOS"]
    assert set(produtos.c.keys()) == {
        "ID",
        "FK_FORNECEDOR",
        "FK_LINHA",
        "NOME",
        "DESCRICAO",
        "TIPO",
        "ATIVO",
        "DATA_CRIACAO",
    }
    assert produtos.c["DESCRICAO"].nullable is True
    assert produtos.c["NOME"].nullable is False
    assert produtos.c["ATIVO"].nullable is False

    # VARIACAO
    variacao = Base.metadata.tables["VARIACAO"]
    assert set(variacao.c.keys()) == {
        "ID",
        "FK_PRODUTO",
        "TAMANHO",
        "COR",
        "ESTOQUE",
        "CUSTO",
        "PRECO",
        "PORCENTAGEM_PROMOCAO",
        "ATIVO",
    }

    # USUARIOS
    usuarios = Base.metadata.tables["USUARIOS"]
    assert set(usuarios.c.keys()) == {
        "ID",
        "NOME",
        "SOBRENOME",
        "EMAIL",
        "SENHA_HASH",
        "NASCIMENTO",
        "CPF",
        "TELEFONE",
        "ATIVO",
        "IS_ADM",
        "DATA_CRIACAO",
    }
    assert usuarios.c["NASCIMENTO"].nullable is True
    assert usuarios.c["CPF"].nullable is True
    assert usuarios.c["TELEFONE"].nullable is True

    # CARRINHO
    carrinho = Base.metadata.tables["CARRINHO"]
    assert set(carrinho.c.keys()) == {
        "ID",
        "FK_USUARIO",
        "STATUS",
        "TOTAL",
        "FRETE_GRATIS",
        "DATA_CRIACAO",
        "FK_USUARIO_ATIVO",
    }
    assert carrinho.c["FK_USUARIO_ATIVO"].computed is not None

    # VENDA
    venda = Base.metadata.tables["VENDA"]
    assert set(venda.c.keys()) == {
        "ID",
        "FK_CARRINHO",
        "FK_USUARIO",
        "FK_ENDERECO_USUARIO",
        "FK_METODO_PAGAMENTO",
        "FK_STATUS",
        "SUBTOTAL",
        "FRETE",
        "DESCONTO",
        "TOTAL",
        "FRETE_GRATIS",
        "DATA",
    }


def test_unique_constraints_explicitadas() -> None:
    """Verifica que as constraints únicas nomeadas de db/schema.sql existem."""
    unique_names: set[str] = set()
    for table in Base.metadata.tables.values():
        for constr in table.constraints:
            if isinstance(constr, UniqueConstraint) and isinstance(constr.name, str) and constr.name:
                unique_names.add(constr.name)

    esperadas_uniques = {
        "UQ_LINHA_NOME",
        "UQ_METODO_PAGAMENTO_METODO",
        "UQ_STATUS_VENDA_ESTADO",
        "UQ_STATUS_VENDA_DESCRICAO",
        "UQ_STATUS_TROCA_ESTADO",
        "UQ_STATUS_TROCA_DESCRICAO",
        "UQ_FORNECEDORES_CNPJ",
        "UQ_EMAILS_FORNECEDOR",
        "UQ_TELEFONE_FORNECEDOR",
        "UQ_VARIACAO_PRODUTO_TAMANHO_COR",
        "UQ_USUARIOS_EMAIL",
        "UQ_USUARIOS_CPF",
        "UQ_ENDERECO_USUARIO_ID_USUARIO",
        "UQ_RECUPERACAO_TOKEN",
        "UQ_CARRINHO_ID_USUARIO",
        "UQ_CARRINHO_UM_ATIVO_POR_USUARIO",
        "UQ_ITEM_CARRINHO_CARRINHO_VARIACAO",
        "UQ_VENDA_CARRINHO_USUARIO",
        "UQ_ITEM_VENDA_VENDA_VARIACAO",
        "UQ_AVALIACAO_ITEM_VENDA",
    }
    for uq in esperadas_uniques:
        assert uq in unique_names, f"Constraint única esperada {uq} não encontrada"


def test_check_constraints_presentes() -> None:
    """Verifica que as CHECK constraints do schema foram declaradas com os nomes originais."""
    check_names: set[str] = set()
    for table in Base.metadata.tables.values():
        for constr in table.constraints:
            if isinstance(constr, CheckConstraint) and isinstance(constr.name, str) and constr.name:
                check_names.add(constr.name)

    checks_originais = [
        "CK_FORNECEDORES_CNPJ",
        "CK_ENDERECO_FORNECEDOR_CEP",
        "CK_VARIACAO_CUSTO",
        "CK_VARIACAO_PRECO",
        "CK_VARIACAO_PROMOCAO",
        "CK_USUARIOS_CPF",
        "CK_USUARIOS_TELEFONE",
        "CK_ENDERECO_USUARIO_CEP",
        "CK_RECUPERACAO_DATAS",
        "CK_CARRINHO_TOTAL",
        "CK_ITEM_CARRINHO_QNT",
        "CK_ITEM_CARRINHO_PRECO",
        "CK_VENDA_VALORES",
        "CK_VENDA_TOTAL",
        "CK_VENDA_FRETE_GRATIS",
        "CK_ITEM_VENDA_QNT",
        "CK_ITEM_VENDA_PRECO",
        "CK_TROCA_QNT",
        "CK_TROCA_CONCLUSAO",
        "CK_REEMBOLSO_QNT",
        "CK_REEMBOLSO_CONCLUSAO",
        "CK_AVALIACAO_NOTA",
    ]
    for ck in checks_originais:
        # A convenção de nomes pode prefixar ck_<tabela>_ ao nome especificado
        encontrado = any(ck in name for name in check_names)
        assert encontrado, f"Check constraint esperada contendo {ck} não encontrada em {check_names}"


def test_foreign_keys_compostas_de_venda() -> None:
    """Verifica se a tabela VENDA possui as Foreign Keys compostas exatas."""
    venda = Base.metadata.tables["VENDA"]
    fk_constraints = [c for c in venda.constraints if isinstance(c, ForeignKeyConstraint)]
    nomes_fks = {c.name for c in fk_constraints if c.name}

    assert "FK_VENDA_CARRINHO_USUARIO" in nomes_fks
    assert "FK_VENDA_ENDERECO_USUARIO" in nomes_fks

    carrinho_fk = next(c for c in fk_constraints if c.name == "FK_VENDA_CARRINHO_USUARIO")
    assert [col.name for col in carrinho_fk.columns] == ["FK_CARRINHO", "FK_USUARIO"]
    assert [elem.target_fullname for elem in carrinho_fk.elements] == [
        "CARRINHO.ID",
        "CARRINHO.FK_USUARIO",
    ]
    assert carrinho_fk.ondelete == "RESTRICT"
    assert carrinho_fk.onupdate == "CASCADE"

    endereco_fk = next(c for c in fk_constraints if c.name == "FK_VENDA_ENDERECO_USUARIO")
    assert [col.name for col in endereco_fk.columns] == ["FK_ENDERECO_USUARIO", "FK_USUARIO"]
    assert [elem.target_fullname for elem in endereco_fk.elements] == [
        "ENDERECO_USUARIO.ID",
        "ENDERECO_USUARIO.FK_USUARIO",
    ]
    assert endereco_fk.ondelete == "RESTRICT"
    assert endereco_fk.onupdate == "CASCADE"


def test_indices_do_schema() -> None:
    """Verifica se os índices explícitos de busca e performance foram declarados."""
    todos_indices: set[str] = set()
    for table in Base.metadata.tables.values():
        for idx in table.indexes:
            if idx.name:
                todos_indices.add(idx.name)

    indices_esperados = {
        "IDX_ENDERECO_FORNECEDOR_FORNECEDOR",
        "IDX_PRODUTOS_FORNECEDOR",
        "IDX_PRODUTOS_LINHA",
        "IDX_PRODUTOS_TIPO_ATIVO",
        "IDX_IMGS_PRODUTOS_PRODUTO",
        "IDX_ENDERECO_USUARIO_USUARIO",
        "IDX_RECUPERACAO_USUARIO",
        "IDX_CARRINHO_USUARIO",
        "IDX_ITEM_CARRINHO_VARIACAO",
        "IDX_ITEM_CARRINHO_RESERVADO_ATE",
        "IDX_VENDA_ENDERECO_USUARIO",
        "IDX_VENDA_USUARIO_DATA",
        "IDX_VENDA_METODO_PAGAMENTO",
        "IDX_VENDA_STATUS",
        "IDX_HIST_STATUS_VENDA_VENDA_DATA",
        "IDX_HIST_STATUS_VENDA_STATUS",
        "IDX_ITEM_VENDA_VARIACAO",
        "IDX_TROCA_ITEM_VENDA",
        "IDX_TROCA_STATUS",
        "IDX_TROCA_VARIACAO_NOVA",
        "IDX_HIST_STATUS_TROCA_TROCA_DATA",
        "IDX_HIST_STATUS_TROCA_STATUS",
        "IDX_REEMBOLSO_ITEM_VENDA",
        "IDX_IMGS_AVALIACAO_AVALIACAO",
    }
    for idx_nome in indices_esperados:
        assert idx_nome in todos_indices, f"Índice {idx_nome} não encontrado nas tabelas"


def test_coluna_virtual_computada_carrinho() -> None:
    """Valida a coluna virtual FK_USUARIO_ATIVO em CARRINHO."""
    col = Base.metadata.tables["CARRINHO"].c["FK_USUARIO_ATIVO"]
    assert col.computed is not None
    assert "IF(STATUS = 'ATIVO', FK_USUARIO, NULL)" in str(col.computed.sqltext)
    assert col.computed.persisted is False


def test_synonyms_lowercase_em_todas_as_entidades() -> None:
    """Verifica que synonyms minúsculos funcionam como get e set em todos os modelos."""
    # Teste em Linha
    linha = Linha(NOME="Casual")
    assert linha.nome == "Casual"
    linha.nome = "Noiva"
    assert linha.NOME == "Noiva"

    # Teste em Fornecedor
    fornecedor = Fornecedor(nome="Tecidos Elegance", cnpj="12345678000199", razao_social="Elegance LTDA")
    assert fornecedor.NOME == "Tecidos Elegance"
    assert fornecedor.CNPJ == "12345678000199"
    assert fornecedor.RAZAO_SOCIAL == "Elegance LTDA"

    # Teste em Usuario
    usuario = Usuario(
        nome="Maria",
        sobrenome="Silva",
        email="maria@teste.com",
        senha_hash="hash_argon2",
    )
    assert usuario.NOME == "Maria"
    assert usuario.SOBRENOME == "Silva"
    assert usuario.EMAIL == "maria@teste.com"
    assert usuario.SENHA_HASH == "hash_argon2"

    # Teste em Carrinho
    carrinho = Carrinho(fk_usuario=1, status="ATIVO", total=Decimal("150.00"), frete_gratis=False)
    assert carrinho.FK_USUARIO == 1
    assert carrinho.STATUS == "ATIVO"
    assert carrinho.TOTAL == Decimal("150.00")
    assert carrinho.FRETE_GRATIS is False

    # Teste em Variacao
    variacao = Variacao(
        fk_produto=10,
        tamanho="M",
        cor="Preto",
        estoque=5,
        custo=Decimal("45.00"),
        preco=Decimal("120.00"),
        porcentagem_promocao=Decimal("10.00"),
    )
    assert variacao.FK_PRODUTO == 10
    assert variacao.TAMANHO == "M"
    assert variacao.COR == "Preto"
    assert variacao.CUSTO == Decimal("45.00")
    assert variacao.PRECO == Decimal("120.00")


def test_ddl_mysql_compilacao_valida() -> None:
    """Valida se a compilação do DDL para dialeto MySQL 8.x ocorre sem erros."""
    for table_name, table in Base.metadata.tables.items():
        stmt = CreateTable(table)
        ddl = str(stmt.compile(dialect=mysql.dialect()))
        assert f"CREATE TABLE `{table_name}`" in ddl or f"CREATE TABLE {table_name}" in ddl
        assert "ENGINE=InnoDB" in ddl


def test_instanciacao_e_persistencia_sqlite_em_memoria() -> None:
    """Valida o funcionamento do grafo de relacionamentos com uma sessão transacional."""
    sqlite_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(sqlite_engine)

    with Session(sqlite_engine) as session:
        # 1. Domínio
        linha = Linha(NOME="Rendas Especiais")
        metodo = MetodoPagamento(METODO="Cartão de crédito")
        status_venda = StatusVenda(ESTADO_ANDAMENTO="EM_PROCESSAMENTO", DESCRICAO="Em processamento")
        status_troca = StatusTroca(ESTADO_ANDAMENTO="SOLICITADA", DESCRICAO="Solicitação recebida")
        session.add_all([linha, metodo, status_venda, status_troca])
        session.flush()

        # 2. Fornecedor
        fornecedor = Fornecedor(
            NOME="Fornecedor Rendas",
            CNPJ="11222333000144",
            RAZAO_SOCIAL="Rendas Finas S.A.",
            ATIVO=True,
        )
        session.add(fornecedor)
        session.flush()

        email_f = EmailsFornecedor(FK_FORNECEDOR=fornecedor.ID, EMAIL="contato@rendas.com")
        tel_f = TelefoneFornecedor(FK_FORNECEDOR=fornecedor.ID, DDD="11", TELEFONE="987654321")
        end_f = EnderecoFornecedor(
            FK_FORNECEDOR=fornecedor.ID,
            CEP="01001000",
            LOGRADOURO="Praça da Sé",
            NUMERO="100",
            BAIRRO="Sé",
            CIDADE="São Paulo",
            ESTADO="SP",
        )
        session.add_all([email_f, tel_f, end_f])

        # 3. Produto e Variação
        produto = Produto(
            FK_FORNECEDOR=fornecedor.ID,
            FK_LINHA=linha.ID,
            NOME="Vestido Renda Chantilly",
            DESCRICAO="Vestido delicado com acabamento em renda.",
            TIPO="roupa",
            ATIVO=True,
        )
        session.add(produto)
        session.flush()

        img_prod = ImgsProduto(FK_PRODUTO=produto.ID, URL_IMAGEM="img/produtos/vestido_1.jpg")
        variacao = Variacao(
            FK_PRODUTO=produto.ID,
            TAMANHO="P",
            COR="Branco",
            ESTOQUE=15,
            CUSTO=Decimal("80.00"),
            PRECO=Decimal("250.00"),
            PORCENTAGEM_PROMOCAO=Decimal("0.00"),
        )
        session.add_all([img_prod, variacao])
        session.flush()

        # 4. Usuário e Endereço
        usuario = Usuario(
            NOME="Camila",
            SOBRENOME="Ferreira",
            EMAIL="camila@exemplo.com",
            SENHA_HASH="argon2$xyz123",
            NASCIMENTO=date(1995, 8, 20),
            CPF="12345678901",
            TELEFONE="11912345678",
            IS_ADM=False,
        )
        session.add(usuario)
        session.flush()

        end_u = EnderecoUsuario(
            FK_USUARIO=usuario.ID,
            NOME="Casa",
            CEP="04567000",
            LOGRADOURO="Rua das Flores",
            NUMERO="42",
            BAIRRO="Jardins",
            CIDADE="São Paulo",
            ESTADO="SP",
        )
        agora = datetime.now()
        recup = Recuperacao(
            FK_USUARIO=usuario.ID,
            TOKEN="a" * 64,
            DATA_CRIACAO=agora,
            DATA_EXPIRA=agora + timedelta(hours=1),
        )
        verif = VerificacaoEmail(
            EMAIL="cliente@exemplo.com",
            TOKEN="b" * 64,
            DATA_CRIACAO=agora,
            DATA_EXPIRA=agora + timedelta(minutes=15),
            EXPIRADO=False,
            TENTATIVAS=0,
        )
        session.add_all([end_u, recup, verif])
        session.flush()
        assert verif.ID is not None
        assert verif.email == "cliente@exemplo.com"

        # 5. Carrinho e Itens
        carrinho = Carrinho(
            FK_USUARIO=usuario.ID,
            STATUS="CONVERTIDO",
            TOTAL=Decimal("250.00"),
            FRETE_GRATIS=True,
        )
        session.add(carrinho)
        session.flush()

        item_c = ItemCarrinho(
            FK_CARRINHO=carrinho.ID,
            FK_VARIACAO=variacao.ID,
            QNT=1,
            PRECO_UNITARIO=Decimal("250.00"),
            RESERVADO_ATE=datetime.now() + timedelta(minutes=30),
        )
        session.add(item_c)
        session.flush()

        # 6. Venda e Itens
        venda = Venda(
            FK_CARRINHO=carrinho.ID,
            FK_USUARIO=usuario.ID,
            FK_ENDERECO_USUARIO=end_u.ID,
            FK_METODO_PAGAMENTO=metodo.ID,
            FK_STATUS=status_venda.ID,
            SUBTOTAL=Decimal("250.00"),
            FRETE=Decimal("0.00"),
            DESCONTO=False,
            TOTAL=Decimal("250.00"),
            FRETE_GRATIS=True,
        )
        session.add(venda)
        session.flush()

        hist_v = HistoricoStatusVenda(FK_VENDA=venda.ID, FK_STATUS_VENDA=status_venda.ID)
        item_v = ItemVenda(
            FK_VENDA=venda.ID,
            FK_VARIACAO=variacao.ID,
            QNT=1,
            PRECO_UNITARIO=Decimal("250.00"),
        )
        session.add_all([hist_v, item_v])
        session.flush()

        # 7. Pós-venda (Troca e Reembolso)
        variacao_nova = Variacao(
            FK_PRODUTO=produto.ID,
            TAMANHO="M",
            COR="Branco",
            ESTOQUE=10,
            CUSTO=Decimal("80.00"),
            PRECO=Decimal("250.00"),
        )
        session.add(variacao_nova)
        session.flush()

        troca = Troca(
            FK_ITEM_VENDA=item_v.ID,
            FK_STATUS_TROCA=status_troca.ID,
            FK_VARIACAO_NOVA=variacao_nova.ID,
            QNT=1,
            MOTIVO="Tamanho pequeno",
            ATIVO=True,
            CONCLUSAO=False,
        )
        session.add(troca)
        session.flush()

        hist_t = HistoricoStatusTroca(FK_TROCA=troca.ID, FK_STATUS_TROCA=status_troca.ID)
        reembolso = Reembolso(
            FK_ITEM_VENDA=item_v.ID,
            QNT=1,
            MOTIVO="Defeito no zíper",
            ATIVO=True,
            CONCLUSAO=False,
        )
        session.add_all([hist_t, reembolso])
        session.flush()

        # 8. Avaliação
        avaliacao = Avaliacao(
            FK_ITEM_VENDA=item_v.ID,
            NOTA=5,
            COMENTARIO="Vestido impecável, tecido maravilhoso!",
        )
        session.add(avaliacao)
        session.flush()

        img_av = ImgsAvaliacao(FK_AVALIACAO=avaliacao.ID, URL_IMAGEM="img/avaliacoes/foto1.jpg")
        session.add(img_av)
        session.commit()

        # Validação de consultas e relacionamentos bidirecionais
        stmt = select(Venda).where(Venda.ID == venda.ID)
        venda_db = session.scalar(stmt)
        assert venda_db is not None
        assert venda_db.usuario.NOME == "Camila"
        assert venda_db.endereco_usuario.LOGRADOURO == "Rua das Flores"
        assert venda_db.carrinho.TOTAL == Decimal("250.00")
        assert len(venda_db.itens) == 1
        assert venda_db.itens[0].variacao.TAMANHO == "P"
        assert venda_db.itens[0].avaliacao is not None
        assert venda_db.itens[0].avaliacao.NOTA == 5
        assert len(venda_db.itens[0].avaliacao.imagens) == 1
