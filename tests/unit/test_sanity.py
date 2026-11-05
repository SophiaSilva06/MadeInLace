"""Teste básico de sanidade do ambiente MadeInLace."""

from fastapi import FastAPI


def test_instancia_fastapi_inicializada_com_sucesso():
    # Arrange
    app = FastAPI(title="MadeInLace")

    # Act
    titulo = app.title

    # Assert
    assert titulo == "MadeInLace"
