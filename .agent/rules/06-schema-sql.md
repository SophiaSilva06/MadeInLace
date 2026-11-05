---
trigger: glob
description: "Convenções do script do banco MySQL (db/schema.sql), sem migrations."
globs: "db/**/*.sql, **/schema.sql"
---

# Script do banco (MySQL 8.0.16+)

- `db/schema.sql` é a única definição do banco. Alterou algo? Atualize também o dicionário de dados (seção 17 da documentação) no mesmo trabalho.
- **Convenções:** nomes em MAIÚSCULAS sem acento, PK `ID`, FK `FK_<ALVO>`, `DECIMAL(10,2)` para dinheiro, `TINYINT(1)` para booleano, `DATETIME` para datas (nascimento é `DATE`), InnoDB e utf8mb4. CPF, CNPJ, CEP e telefone só com dígitos.
- Integridade no banco, não só no app: `UNIQUE`, `FOREIGN KEY` e `CHECK` onde a regra for do dado. Chave estrangeira com o mesmo tipo e sinal da coluna referenciada.
- Exclusão é lógica (`ATIVO = 0`); não crie `ON DELETE CASCADE` em tabela de histórico, pedido ou item vendido.
- Índice novo só com evidência (`EXPLAIN ANALYZE`); consulta frequente em `FK_*` e em colunas de filtro merece índice.
- Alteração em banco já criado: entregue o `ALTER` e o inverso no chat. `DROP`, `TRUNCATE` e mudança de tipo exigem aprovação (regra 02).

Aprofundamento: skill `mysql-dba-senior` (ignore nela o que pede migrations, regra 07).
