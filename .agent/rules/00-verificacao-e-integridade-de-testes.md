---
trigger: always_on
description: "Regras permanentes de verificação e integridade de testes: executar antes de afirmar, nunca afrouxar teste para passar."
---

# Verificação e integridade de testes

- Não diga que algo "funciona" ou "passou" sem ter executado. Cole a saída real (pytest, ruff, mypy). Se não deu para executar (sem rede, banco ou navegador), diga o que ficou sem verificação.
- O teste é a especificação: se falha, o defeito está no código. Proibido para fazer passar: afrouxar ou remover assert, trocar o esperado pelo obtido, `skip`/`xfail`/`--deselect`/`-k`, retry para mascarar teste instável, aumentar timeout, mock que força o resultado, reconhecer a entrada do teste no código, editar `conftest.py`/`pytest.ini`/`pyproject.toml` para ignorar falha.
- Teste instável é bug de determinismo (espera por condição, relógio congelado, seed, isolamento), não de sorte.
- Teste objetivamente errado (contradiz o requisito escrito): pare, mostre a evidência e peça aprovação antes de alterá-lo.
- Bug corrigido ganha antes um teste que falha pelo motivo certo.
- Ao fechar uma tarefa de código, siga o ciclo da regra 08 (suíte completa, não só o teste novo). Se não chegar a 100%, relate o que falha e por quê; um vermelho honesto vale mais que um verde falso.
- Resumo final curto: o que mudou, o que foi verificado e o que não foi.

Aprofundamento: skill `qa-adversarial-tester` (fluxo, gate `check_integrity.py`, relatório).
