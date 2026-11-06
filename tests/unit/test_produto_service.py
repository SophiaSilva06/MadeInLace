"""Testes unitários para regras de negócio e cálculo de estrelas do ProdutoService."""

from app.services.produto_service import ProdutoService


def test_calcular_estrelas_visuais_regras() -> None:
    """Valida o cálculo das 5 estrelas ('full', 'half', 'empty') conforme especificação.

    Exemplos da regra de negócio:
    - 3.2: 3 cheias, 0 meias, 2 vazias
    - 4.7: 4 cheias, 1 meia, 0 vazias
    - 4.9: 4 cheias, 1 meia, 0 vazias
    - 5.0: 5 cheias
    - None ou 0: 5 vazias
    """
    assert ProdutoService._calcular_estrelas_visuais(None) == ["empty"] * 5
    assert ProdutoService._calcular_estrelas_visuais(0.0) == ["empty"] * 5

    estrelas_3_2 = ProdutoService._calcular_estrelas_visuais(3.2)
    assert estrelas_3_2 == ["full", "full", "full", "empty", "empty"]

    estrelas_4_7 = ProdutoService._calcular_estrelas_visuais(4.7)
    assert estrelas_4_7 == ["full", "full", "full", "full", "half"]

    estrelas_4_9 = ProdutoService._calcular_estrelas_visuais(4.9)
    assert estrelas_4_9 == ["full", "full", "full", "full", "half"]

    estrelas_5_0 = ProdutoService._calcular_estrelas_visuais(5.0)
    assert estrelas_5_0 == ["full", "full", "full", "full", "full"]
