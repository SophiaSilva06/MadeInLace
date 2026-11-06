from decimal import Decimal, DecimalException
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates

# Diretório base do projeto e pasta de templates
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Inicialização centralizada de templates Jinja2
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def formatar_moeda(valor: Any) -> str:
    """Formata um valor numérico para o padrão de moeda brasileiro (BRL).

    Exemplos:
        >>> formatar_moeda(Decimal("149.90"))
        'R$ 149,90'
        >>> formatar_moeda(1250.5)
        'R$ 1.250,50'
        >>> formatar_moeda(None)
        'R$ 0,00'
    """
    if valor is None or valor == "":
        return "R$ 0,00"

    try:
        if isinstance(valor, (int, float, str, Decimal)):
            d = Decimal(str(valor))
        else:
            return "R$ 0,00"
    except (ValueError, TypeError, DecimalException):
        return "R$ 0,00"

    # Formatação com '.' para milhar e ',' para casas decimais
    formatado = f"{d:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatado}"


def formatar_desconto(valor: Any) -> str:
    """Formata um valor percentual de desconto.

    Exemplos:
        >>> formatar_desconto(Decimal("10.00"))
        '-10%'
        >>> formatar_desconto(15.5)
        '-15,5%'
        >>> formatar_desconto(0)
        '0%'
    """
    if valor is None or valor == "":
        return "0%"

    try:
        if isinstance(valor, (int, float, str, Decimal)):
            d = Decimal(str(valor))
        else:
            return "0%"
    except (ValueError, TypeError, DecimalException):
        return "0%"

    if d <= 0:
        return "0%"

    # Se for número inteiro, exibe sem decimais (ex: -10%)
    if d == d.to_integral():
        return f"-{int(d)}%"

    formatado = f"{d:.1f}".replace(".", ",")
    return f"-{formatado}%"


# Registro dos filtros customizados no ambiente do Jinja2
templates.env.filters["moeda"] = formatar_moeda
templates.env.filters["desconto"] = formatar_desconto
