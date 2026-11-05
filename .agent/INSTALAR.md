# Instalação no Google Antigravity (MadeInLace)

Conteúdo do pacote, todo relativo à **raiz do projeto**:

```
.agent/skills/   5 skills (carregadas sob demanda)
.agent/rules/    9 rules (00 a 08)
docs/MadeInLace_Documentacao.md   regras de negócio + dicionário de dados
db/schema.sql                     script de criação do banco (MySQL 8.0.16+)
tools/verify.py                   executor do ciclo da regra 08 (ruff, mypy, pytest + erros sanitizados)
```

Copie `.agent/`, `docs/`, `db/` e `tools/` para a raiz do repositório e reinicie a sessão do agente.
Se a sua versão do Antigravity usa `.agents/` (plural) como padrão, renomeie `.agent/`; o nome antigo continua aceito.

Skills globais: copie `skills/*` para `~/.gemini/antigravity/skills/` e troque, nos comandos de `scripts/`, o prefixo `.agent/skills/` pelo caminho global.

## Ativação das rules (confira em Customizations > Rules)
| Arquivo | Modo |
|---|---|
| 00-verificacao-e-integridade-de-testes, 01-seguranca-baseline, 02-contratos-e-dados, 07-projeto-madeinlace, 08-ciclo-de-verificacao | Always On |
| 03-backend-python, 04-frontend-apresentacao, 05-testes-pytest, 06-schema-sql | Glob (campo `globs` no frontmatter) |

Frontmatter das rules: `trigger` (always_on ou glob), `description` e, nas glob, `globs` como texto separado por vírgulas. Limite do Antigravity: 12.000 caracteres por rule.

## Ciclo de verificação (regra 08)
Requer `ruff` e `pytest` instalados (e `mypy` se houver configuração dele no projeto). Se `DATABASE_URL`, `DB_NAME` ou `MYSQL_DATABASE` estiverem definidos, o script só roda quando o valor contiver `_test`.

## Manutenção
- Regra de negócio mudou: edite `docs/MadeInLace_Documentacao.md`.
- Banco mudou: edite `db/schema.sql` e o dicionário (seção 17) no mesmo commit. O projeto não usa migrations.
