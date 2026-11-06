"""Testes unitários dos templates Jinja2 da MadeInLace."""

from decimal import Decimal

import jinja2
import pytest

from app.core.templates import formatar_desconto, formatar_moeda
from app.services.produto_service import (
    AvaliacaoItemDTO,
    MidiaAvaliacaoDTO,
    ProdutoDetalheDTO,
    VariacaoOpcaoDTO,
)


def mock_url_for(endpoint: str, **values: str) -> str:
    if endpoint == "static":
        return f"/static/{values.get('path', '')}"
    return f"/{endpoint}"


@pytest.fixture
def jinja_env() -> jinja2.Environment:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(
            ["app/templates", "app/templates/home", "app/templates/auth", "app/templates/catalogo"]
        ),
        autoescape=True,
    )
    env.filters["moeda"] = formatar_moeda
    env.filters["desconto"] = formatar_desconto
    return env


def test_base_template_estrutura(jinja_env: jinja2.Environment) -> None:
    """Garante que base.html possui todas as seções e marcas de acessibilidade."""
    template = jinja_env.get_template("base.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=0,
    )

    # Top bar
    assert "10% Off Na Primeira Compra Fazendo Login" in rendered
    assert "Frete Grátis A Partir de R$160" in rendered
    assert "Reembolsos E Trocas Por Até 30 Dias" in rendered

    # Header
    assert "MadeInLaceLogo.png" in rendered
    assert "Explorar" in rendered
    assert "Saltos" in rendered
    assert "Corsets" in rendered
    assert "Vestidos" in rendered
    assert "Promoção" in rendered
    assert "Plus Size" in rendered
    assert "Produtos" in rendered

    # Barra de pesquisa sobreposta (27_MadeInLace Pesquisa & 9_MadeInLace Pesquisa2)
    assert 'id="search-drawer"' in rendered
    assert 'name="q"' in rendered
    assert 'name="tipo_busca"' in rendered
    assert "Pesquisar Por: Tudo" in rendered
    assert 'data-mode="linhas"' in rendered
    assert 'data-mode="produtos"' in rendered

    # Footer
    assert "Sobre Nós" in rendered
    assert "Ajuda e Informações" in rendered
    assert "Faça Login e Receba 10% Na Sua Primeira Compra" in rendered
    assert "footer-newsletter-form" in rendered
    assert "footer-socials" in rendered


def test_base_template_cart_button_redireciona_para_pagina_atual_ao_deslogado(
    jinja_env: jinja2.Environment,
) -> None:
    """Garante que o botão de sacola para visitante deslogado redireciona para login mantendo a página atual."""

    class DummyURL:
        path = "/produtos/8"
        query = ""

    class DummyRequest:
        cookies: dict[str, str] = {}
        url = DummyURL()

    template = jinja_env.get_template("base.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=0,
        request=DummyRequest(),
    )

    # Não deve apontar para next=/carrinho
    assert 'next=/carrinho"' not in rendered
    assert 'next=%2Fcarrinho"' not in rendered
    # Deve apontar para a página onde o usuário estava (/produtos/8) com parâmetro de abrir_carrinho
    assert "next=/produtos/8" in rendered
    assert "abrir_carrinho" in rendered


def test_home_index_template_render(jinja_env: jinja2.Environment) -> None:
    """Garante que a Home renderiza o Hero, Promoções, Best Sellers e Linhas."""
    template = jinja_env.get_template("index.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=1,
        promocoes=None,
        best_sellers=None,
        linhas=None,
    )

    # Hero Carrossel
    assert "MadeInLaceCarrossel1.png" in rendered
    assert "MadeInLaceCarrossel2.png" in rendered

    # Promoções
    assert "Promoções" in rendered

    # Best Sellers
    assert "Best Sellers" in rendered

    # Linhas
    assert "Linhas" in rendered
    assert "Belezas do Mar" in rendered
    assert "Florestal" in rendered
    assert "Elegância da Realeza" in rendered
    assert "Dia a Dia de Verão" in rendered


def test_login_template_fidelidade_e_modais(jinja_env: jinja2.Environment) -> None:
    """Garante que a página de login possui os campos de email e senha, mensagem de erro e os 3 modais."""
    template = jinja_env.get_template("auth/login.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=0,
        email_preenchido="cliente@exemplo.com",
        next_url="/carrinho",
        promo_ativa=False,
        error_login=True,
        registered=False,
    )

    # Página base (13_MadeInLace Login)
    assert "Fazer Login" in rendered
    assert '<input type="hidden" name="next_url" id="login-next-url" value="/carrinho">' in rendered
    assert "Email:" in rendered
    assert "Senha:" in rendered
    assert 'value="cliente@exemplo.com"' in rendered
    assert "email ou senha estão errados" in rendered
    assert "Criar Uma conta" in rendered
    assert "Problemas Para Fazer Login?" in rendered
    assert "Ao continuar, você concorda com nossa Política de Privacidade" in rendered

    # Modal 1: 19_MadeInLace Recuperacao
    assert "modal-recuperacao" in rendered
    assert "Código Enviado:" in rendered
    assert '<div class="modal-timer-box" id="recovery-timer-display" aria-label="Tempo restante para validação">0:00</div>' in rendered
    assert "3:29" not in rendered
    assert "Esqueceu o email? Clique aqui!" in rendered

    # Modal 2: 24_MadeInLace Recuperacao2
    assert "modal-mudar-senha" in rendered
    assert "Mudar Senha" in rendered
    assert "Senha Nova:" in rendered
    assert "Confirmar Senha:" in rendered

    # Modal 3: 30_MadeInLace Recuperacao1.1
    assert "modal-recuperacao-cpf" in rendered
    assert 'placeholder="CPF: 000.000.000-00"' in rendered
    assert 'placeholder="Data Nascimento: DD/MM/AAAA"' in rendered
    assert "14647756807" not in rendered
    assert "17/11/1993" not in rendered
    assert "Procurar" in rendered
    assert 'id="masked-email-display"' in rendered
    assert "so******@g******.com" not in rendered


def test_registro_template_fidelidade_e_modais(jinja_env: jinja2.Environment) -> None:
    """Garante que a página de cadastro possui os campos, validação de senha e modais de endereço e e-mail."""
    template = jinja_env.get_template("auth/registro.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=0,
        email_inicial="",
    )

    # Página base (3_MadeInLace Registro1)
    assert "Registrar-se" in rendered
    assert "Email:" in rendered
    assert "CPF:" in rendered
    assert "Nome:" in rendered
    assert "Sobrenome:" in rendered
    assert "Senha:" in rendered
    assert "password-check-badge" in rendered
    assert 'id="password-requirements-hint"' in rendered
    assert "12" in rendered
    assert "128" in rendered
    assert "maiúscula" in rendered
    assert "minúscula" in rendered
    assert "número" in rendered
    assert "símbolo" in rendered
    assert "Nascimento:" in rendered
    assert "Telefone:" in rendered
    assert "Adicionar Endereço" in rendered
    assert "Continuar" in rendered
    assert "email ja usado" in rendered
    assert "cpf ja usado" in rendered
    assert 'id="address-summary-badge" style="display: none;"' in rendered
    assert '<span id="address-summary-text"></span>' in rendered

    # Modal 4: 31_MadeInLace Registro2
    assert "modal-adicionar-endereco" in rendered
    assert "Adicionar Endereço" in rendered
    assert "btn-add-more-address" in rendered
    assert "+" in rendered

    # Modal 5: MadeInLace_Autenticar_Email
    assert "modal-autenticar-email" in rendered
    assert "Autenticar Email" in rendered
    assert "Enviar Código" in rendered
    assert "Código De Verificação:" in rendered
    assert '<div class="modal-timer-box" id="auth-email-timer-display" aria-label="Tempo restante para validação">0:00</div>' in rendered


def test_produto_detalhe_template_fidelidade_design(jinja_env: jinja2.Environment) -> None:
    """Garante fidelidade visual da página de produtos e do modal (25 e 8_MadeInLace Produtos)."""
    produto = ProdutoDetalheDTO(
        id=1,
        nome="Vestido Leve De Sereia",
        descricao="Um vestido de cetim sexy e elegante inspirado nas sedutores sereias do mar.",
        tipo="roupa",
        linha_nome="Belezas do Mar",
        imagem_principal="img/produtos/midday-phantom-dress-1.png",
        imagens=[
            "img/produtos/midday-phantom-dress-1.png",
            "img/produtos/morning-dew-corset-1.png",
        ],
        preco_base=Decimal("320.00"),
        preco_promocional=Decimal("280.00"),
        porcentagem_promocao=Decimal("12.50"),
        tem_promocao=True,
        tamanhos_disponiveis=["P", "M", "G", "GG"],
        cores_disponiveis=["Azul", "Amarelo", "Rosa"],
        tamanhos_todos=[
            {"tamanho": "PP", "disponivel": False},
            {"tamanho": "P", "disponivel": True},
            {"tamanho": "M", "disponivel": True},
            {"tamanho": "G", "disponivel": True},
            {"tamanho": "GG", "disponivel": True},
        ],
        cores_todas=[
            {"cor": "Azul", "disponivel": True},
            {"cor": "Amarelo", "disponivel": True},
            {"cor": "Rosa", "disponivel": True},
        ],
        tamanho_inicial="P",
        cor_inicial="Azul",
        variacoes=[
            VariacaoOpcaoDTO(
                id=1, tamanho="P", cor="Azul", estoque=5, preco=Decimal("320.00"), preco_promocional=Decimal("280.00"), disponivel=True
            ),
            VariacaoOpcaoDTO(
                id=2, tamanho="PP", cor="Azul", estoque=0, preco=Decimal("320.00"), preco_promocional=Decimal("280.00"), disponivel=False
            ),
        ],
        estoque_total=5,
        media_avaliacoes=4.9,
        total_avaliacoes=196,
        distribuicao_estrelas={5: 105, 4: 89, 3: 2, 2: 0, 1: 0},
        estrelas_visuais=["full", "full", "full", "full", "half"],
        avaliacoes_com_midia=[
            AvaliacaoItemDTO(
                id=10,
                autor_nome="Sandra",
                nota=5,
                tamanho_comprado="G",
                cor_comprada="Azul",
                comentario="Gente o vestido é maravilhoso cai super bem no busto e deixa mais aparentes as curvas corporais.",
                data_formatada="20/10/2026",
                midias=[
                    MidiaAvaliacaoDTO(url="img/avaliacoes/avaliacao_01.png", tipo="imagem"),
                    MidiaAvaliacaoDTO(url="img/avaliacoes/avaliacao_video.mp4", tipo="video"),
                ],
                tem_midia=True,
            )
        ],
        avaliacoes_sem_midia=[
            AvaliacaoItemDTO(
                id=20,
                autor_nome="Sandra",
                nota=5,
                tamanho_comprado="G",
                cor_comprada="Azul",
                comentario="Gente o vestido é maravilhoso cai super bem no busto...",
                data_formatada="20/10/2026",
                midias=[],
                tem_midia=False,
            ),
            AvaliacaoItemDTO(
                id=21,
                autor_nome="Natália",
                nota=5,
                tamanho_comprado="M",
                cor_comprada="Amarelo",
                comentario="Ficou um pouco apertadinho de mais na cintura...",
                data_formatada="21/10/2026",
                midias=[],
                tem_midia=False,
            ),
            AvaliacaoItemDTO(
                id=22,
                autor_nome="Isabella",
                nota=5,
                tamanho_comprado="P",
                cor_comprada="Rosa",
                comentario="Olha eu nunca vi um vestido tão bom...",
                data_formatada="22/10/2026",
                midias=[],
                tem_midia=False,
            ),
            AvaliacaoItemDTO(
                id=23,
                autor_nome="Juliana",
                nota=4,
                tamanho_comprado="M",
                cor_comprada="Azul",
                comentario="Muito confortável e delicado.",
                data_formatada="23/10/2026",
                midias=[],
                tem_midia=False,
            ),
        ],
    )

    template = jinja_env.get_template("catalogo/produto_detalhe.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        cart_count=0,
        produto=produto,
    )

    # 1. Galeria e navegação
    assert "produto-galeria__viewport" in rendered
    assert "btn-galeria-prev" in rendered
    assert "btn-galeria-next" in rendered
    assert "produto-galeria-principal" in rendered
    assert "produto-thumb-item" in rendered

    # 2. Informações de produto e nota média no topo
    assert "Vestido Leve De Sereia" in rendered
    assert "4.9" in rendered
    assert "R$ 280,00" in rendered
    assert "R$ 320,00" in rendered

    # 3. Variações e estado de indisponibilidade
    assert "Tamanho —" in rendered
    assert "is-unavailable" in rendered  # Tamanho PP indisponível com risco diagonal
    assert "Cor —" in rendered

    # 4. Botão Adicionar ao Carrinho
    assert "Adicionar Ao Carrinho" in rendered
    assert "form-add-carrinho" in rendered

    # 5. Acordeões dinâmicos
    assert "Descrição:" in rendered
    assert "Guia de Tamanhos:" in rendered
    assert "/perfil#guia-tamanhos" in rendered
    assert "Reembolso e Troca:" in rendered
    assert "Oferecemos 30 dias para o reembolso" in rendered

    # 6. Box principal de avaliações
    assert "avaliacoes-resumo-box" in rendered
    assert "Fotos E Videos De Compradores" in rendered
    assert "thumb-video-badge" in rendered  # Vídeo com sinal de play
    assert "196 Avaliações" in rendered
    assert "4.9 de 5" in rendered
    assert "halfStarSvg_" in rendered  # Meia estrela

    # 7. Grid de avaliações sem mídia (3 em 3) e nota com estrela
    assert "avaliacoes-cards-grid" in rendered
    assert "Sandra" in rendered
    assert "Natália" in rendered
    assert "Isabella" in rendered
    assert "btn-carregar-mais-avaliacoes" in rendered  # Mais de 3 cards gera botão carregar mais

    # 8. Modal de Mídias (8_MadeInLace Produtos2)
    assert "modal-avaliacao-backdrop" in rendered
    assert "modal-midia-img" in rendered
    assert "modal-midia-video" in rendered
    assert "modal-fechar-btn" in rendered
    assert "dados-avaliacoes-midia" in rendered


def test_perfil_template_modais_email_timer(jinja_env: jinja2.Environment) -> None:
    """Garante que o modal de alteração de e-mail no perfil possui caixas de timer inicializadas em 0:00."""
    template = jinja_env.get_template("perfil/index.html")
    rendered = template.render(
        url_for=mock_url_for,
        current_user=None,
        usuario_logado=None,
        cart_count=0,
        perfil=None,
        secao_ativa="meu-perfil",
        pedidos_iniciais=[],
        tem_mais_pedidos=False,
        trocas_iniciais=[],
        tem_mais_trocas=False,
    )
    assert "modal-alterar-email" in rendered
    assert '<div class="modal-timer-box" id="timer-cod-email-atual" aria-label="Tempo restante para validação">0:00</div>' in rendered
    assert '<div class="modal-timer-box" id="timer-cod-email-novo" aria-label="Tempo restante para validação">0:00</div>' in rendered


