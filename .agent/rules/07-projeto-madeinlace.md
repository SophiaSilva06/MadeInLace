---
trigger: always_on
description: "Contexto do projeto MadeInLace: stack, fontes de verdade (docs e db), precedência e banco de teste."
---

# Projeto MadeInLace

Loja virtual de roupas e calçados femininos (projeto estudantil). Stack: FastAPI + Jinja2 + HTML/CSS/JS + MySQL 8.0.16+. Não use Flask, Django, React nem Vue. Pagamento e rastreamento de entrega são simulados.

## Fontes de verdade
- `docs/MadeInLace_Documentacao.md`: regras de negócio (seções 2 a 15), requisitos não funcionais (16) e dicionário de dados (17).
- `db/schema.sql`: script executável do banco, com os dados iniciais das tabelas de domínio.

Antes de implementar, testar ou revisar, leia a seção do assunto:

| Assunto | Seções |
|---|---|
| Cadastro, senha, login, recuperação | 2 a 4 |
| Endereços | 5 |
| Catálogo, promoção, busca | 6 e 7 |
| Estoque, reserva, carrinho | 8 e 9 |
| Checkout, desconto, frete, total | 10, 11 e Anexo A (tabela de frete) |
| Status, trocas, reembolsos | 12 e 13 |
| Avaliações, exclusão e LGPD | 14 e 15 |
| Tipos e colunas | 17 e `db/schema.sql` |

## Precedência
- Regras de negócio: a documentação vence. Tipos, constraints e nomes de colunas: o `schema.sql` vence.
- Se código, teste, documentação e schema divergirem, aponte a divergência e peça decisão. Não ajuste teste nem documentação só para acompanhar o código. Lacuna na documentação é decisão em aberto: pergunte, não presuma.

## Sem versionamento de banco
O projeto não usa migrations. Não crie Alembic, Flyway nem pasta de migrations, mesmo que uma skill sugira. Para mudar um banco já criado, entregue o `ALTER` e o inverso no chat e atualize o `schema.sql`.

## Banco de teste
O `schema.sql` cria e usa `MADEINLACE`. Nunca rode testes nele: use uma cópia com o nome trocado para `MADEINLACE_TEST` (aparece só em `CREATE DATABASE` e `USE`).
