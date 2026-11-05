---
trigger: glob
description: "Como escrever testes: determinismo, casos adversariais, segredos de teste, banco de teste."
globs: "tests/**, **/test_*.py, **/*_test.py, **/conftest.py"
---

# Escrita de testes

- Um comportamento por teste, com nome que o descreve (`test_rejeita_quantidade_negativa`). Estrutura Arrange-Act-Assert e asserts específicos (`pytest.raises(Tipo, match="...")`), nunca `assert True`.
- **Determinismo:** tempo congelado, seed fixa, sem rede real, sem depender de ordem. Nunca `sleep`; em E2E use `expect(...)` com auto-wait.
- **Casos adversariais mínimos por entrada:** vazio/`None`, limites (0, -1, máximo+1), tipo errado, unicode, payload enorme, duplicado ou concorrente, injeção inofensiva (`' OR '1'='1`).
- **Segredos:** gere na hora (`secrets.token_hex()`) ou use fixture; sem literal em variável chamada `password`, `token` ou `key`, pois o scanner de segredos bloqueia o PR.
- **Banco:** MySQL de teste com sufixo `_test`, criado a partir do schema real (`db/schema.sql`). Dinheiro, estoque, constraints e concorrência não se testam em SQLite. Concorrência exige conexões separadas.
- Dependências de teste pinadas em `requirements-dev.txt`.

Aprofundamento: skill `qa-adversarial-tester`.
