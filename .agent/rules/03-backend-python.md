---
trigger: glob
description: "Convenções do backend Python (FastAPI, SQLAlchemy): rota fina, tipagem, dinheiro, estoque, N+1, erros."
globs: "**/*.py"
---

# Backend Python (FastAPI, SQLAlchemy)

- **Rota fina:** valida, autoriza, chama um service/caso de uso e traduz a resposta. Regra de negócio não fica na rota nem no template.
- **Tipagem estrita:** anotações em tudo que é público, `Any` só com justificativa. Pydantic com tipos fortes, limites e `extra="forbid"`.
- **Dinheiro:** `Decimal`/`DECIMAL`, nunca `float`. Preço, desconto e total são calculados no servidor, nunca aceitos do cliente.
- **Estoque e saldo:** transação com `UPDATE` condicional ou lock, para evitar corrida e venda duplicada.
- **Banco:** sessão por requisição via dependência; commit e rollback na camada de service; sem consulta dentro de loop (N+1), use join ou eager loading.
- **Erros:** exceções de domínio mapeadas para HTTP em um handler; nunca `except Exception: pass`; `logging` em vez de `print`, sem dado pessoal nem segredo.

Aprofundamento: skill `fastapi-jinja2-sqlalchemy`.
