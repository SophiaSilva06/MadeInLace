# Migrations idempotentes, retrocompatíveis e zero-downtime

## Sumário
1. Regras de uma migration segura
2. Idempotência em MySQL
3. Online DDL: escolher ALGORITHM e LOCK
4. Padrão expand → migrate → contract
5. Receitas por tipo de mudança
6. Tabelas grandes: gh-ost / pt-online-schema-change
7. Checklist pré-deploy

## 1. Regras de uma migration segura
- **Uma intenção por migration**, pequena e revisável. DDL no MySQL faz commit implícito e não é revertido por `ROLLBACK`: uma migration que falha no meio deixa o schema pela metade. Por isso cada migration deve poder ser **reexecutada** sem erro.
- **Nunca edite migration já aplicada.** Crie outra.
- **Todo `up` tem `down`** (ou uma nota explícita de "irreversível" com o motivo e o plano de restauração).
- **Separe DDL de backfill de dados.** Backfill em lotes, fora de transação longa.
- **Limite a espera por metadata lock**: `SET SESSION lock_wait_timeout = 5;` e rode fora de picos. Uma transação longa aberta bloqueia o DDL, e o DDL bloqueado enfileira todas as queries seguintes na tabela.
- **Sempre declare `ALGORITHM=` e `LOCK=` explicitamente** (seção 3). Sem isso o MySQL pode fazer uma cópia com lock sem avisar; com isso ele falha com erro claro.

## 2. Idempotência em MySQL

Suporte nativo é parcial. Combine:

```sql
-- Tabelas
CREATE TABLE IF NOT EXISTS pedido ( ... ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Remoções
DROP TABLE IF EXISTS tabela_antiga;
```

Colunas, índices e constraints **não têm `IF NOT EXISTS` no MySQL** (têm no MariaDB). Use checagem em `information_schema` com SQL dinâmico:

```sql
-- Adicionar coluna somente se não existir
SET @sql = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE pedido ADD COLUMN canal VARCHAR(20) NULL, ALGORITHM=INSTANT',
    'SELECT 1')
  FROM information_schema.columns
  WHERE table_schema = DATABASE() AND table_name = 'pedido' AND column_name = 'canal');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Criar índice somente se não existir
SET @sql = (
  SELECT IF(COUNT(*) = 0,
    'ALTER TABLE pedido ADD INDEX idx_pedido_cliente_criado (cliente_id, criado_em), ALGORITHM=INPLACE, LOCK=NONE',
    'SELECT 1')
  FROM information_schema.statistics
  WHERE table_schema = DATABASE() AND table_name = 'pedido' AND index_name = 'idx_pedido_cliente_criado');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
```

Para constraints use `information_schema.table_constraints`. Em Alembic, Flyway ou Liquibase, use as pré-condições da ferramenta (`sa.inspect(bind)`, `preConditions`) ou um helper com esse padrão: o controle de versão evita reexecução, mas só a idempotência protege contra execução parcial e ambientes divergentes.

Dados: use `INSERT ... ON DUPLICATE KEY UPDATE` ou `INSERT IGNORE` (com cuidado: `IGNORE` também engole outros erros) e `UPDATE ... WHERE <ainda não migrado>`.

## 3. Online DDL: escolher ALGORITHM e LOCK

Ordem de preferência: `INSTANT` > `INPLACE` com `LOCK=NONE` > ferramenta externa (seção 6) > `COPY` (bloqueia escritas; só com janela de manutenção).

| Operação (InnoDB, 8.0) | Em geral | Observação |
|---|---|---|
| Adicionar coluna | `INSTANT` | No fim da tabela desde 8.0.12; em qualquer posição desde 8.0.29. Limite de ~64 versões instantâneas por tabela |
| Remover coluna | `INSTANT` (8.0.29+) | Antes disso `INPLACE` com rebuild |
| Adicionar índice secundário | `INPLACE, LOCK=NONE` | Lê a tabela; custo de I/O proporcional ao tamanho |
| Adicionar FK | `INPLACE` só com `foreign_key_checks=0` na sessão | Valide os dados antes; com checks ligados vira `COPY` |
| Mudar tipo da coluna | `COPY` (quase sempre) | Use ferramenta externa ou expand/contract |
| Aumentar `VARCHAR` | `INPLACE` se não cruzar o limite de 255→256 bytes de prefixo de tamanho | Cruzar o limite força rebuild |
| `NULL` → `NOT NULL` | `INPLACE` com rebuild | Exige backfill antes; bloqueia se houver nulos |
| Mudar PK / charset / collation | `COPY` | Tratar como migração de tabela |

A tabela é um guia: confirme na documentação da versão. Peça o algoritmo explicitamente e deixe o servidor recusar:

```sql
ALTER TABLE pedido ADD COLUMN canal VARCHAR(20) NULL, ALGORITHM=INSTANT;
ALTER TABLE pedido ADD INDEX idx_x (a, b), ALGORITHM=INPLACE, LOCK=NONE;
```
Erro `ER_ALTER_OPERATION_NOT_SUPPORTED_REASON` significa "esse ALTER não é online": mude de estratégia, não remova o `ALGORITHM`.

## 4. Padrão expand → migrate → contract

Garante que a versão N-1 e a N do código funcionem contra o mesmo schema durante o rollout (e permite rollback do código).

1. **Expand** — só adições compatíveis: coluna `NULL` ou com `DEFAULT`, tabela nova, índice novo. Nada é removido ou renomeado. Deploy do schema **antes** do código.
2. **Migrate** — o código novo passa a **escrever nos dois lugares** (dual-write) e a ler do novo com fallback para o antigo. Faça o **backfill em lotes** dos dados históricos:
   ```sql
   -- repita até 0 linhas afetadas; pause entre lotes; monitore lag de réplica
   UPDATE pedido SET canal = 'web' WHERE canal IS NULL AND id BETWEEN ? AND ? ;
   ```
   Itere por faixa de PK (não `LIMIT` sem `ORDER BY`), lotes de 1–10 mil linhas conforme o custo, com `sleep` curto.
3. **Verify** — compare contagens/checksums entre origem e destino; deixe rodar um ciclo completo de negócio.
4. **Contract** — só depois que nenhuma versão do código usa o formato antigo: aplique `NOT NULL`/constraint nova, remova coluna/tabela/índice antigos. Faça isso em **deploy separado**, dias depois, e mantenha o backup/`down`.

Para remover coluna: primeiro pare de ler e escrever nela no código (deploy 1), depois `DROP COLUMN` (deploy 2). Para remover índice, ensaie com índice invisível (`indices-explain.md`, seção 4).

## 5. Receitas

**Renomear coluna** — não use `RENAME COLUMN` direto. Adicione coluna nova → dual-write → backfill → troque leitura → pare de escrever na antiga → remova a antiga.

**Mudar tipo** (ex.: `INT` → `BIGINT`, `VARCHAR` → `DECIMAL`) — mesma receita de coluna nova; ou gh-ost em tabela grande.

**Adicionar `NOT NULL`** — adicione como `NULL` com default na aplicação, backfill, verifique `SELECT COUNT(*) WHERE col IS NULL` = 0, só então `MODIFY ... NOT NULL` (ou `CHECK` primeiro, validado fora de pico).

**Adicionar FK em tabela com dados** — procure órfãos antes (`LEFT JOIN ... WHERE pai.id IS NULL`), corrija, crie o índice do lado filho em passo anterior, depois a FK.

## 6. Tabelas grandes (dezenas de milhões de linhas ou ALTER que cai em `COPY`)

- **gh-ost** (sem triggers, lê o binlog) ou **pt-online-schema-change** (usa triggers): criam cópia sombra, replicam mudanças, fazem `RENAME` atômico no fim. Exigem binlog em `ROW` (gh-ost), espaço em disco ≈ tamanho da tabela e atenção ao lag de réplicas; FKs complicam ambos.
- Faça um **dry-run** primeiro, defina throttle por lag de réplica e carga (`--max-lag-millis`, `--max-load`), e deixe o cut-over para horário de baixo tráfego.

## 7. Checklist pré-deploy
- [ ] Idempotente, com `down`/rollback, e `ALGORITHM`/`LOCK` explícitos
- [ ] Código N-1 funciona com o schema novo (e N com o antigo, se houver rollback)
- [ ] Backfill em lotes, retomável, com monitoramento de lag e locks
- [ ] Testado com volume parecido com produção (tempo e disco estimados)
- [ ] Janela fora de pico, sem transação longa aberta (`information_schema.innodb_trx`)
- [ ] Verificação pós-deploy definida (contagens, `EXPLAIN` das queries afetadas)
