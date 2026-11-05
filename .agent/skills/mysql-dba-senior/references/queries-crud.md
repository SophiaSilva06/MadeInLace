# CRUD eficiente, concorrência e segurança

## Sumário
1. Segurança: queries parametrizadas
2. Leitura (SELECT)
3. Paginação
4. Escrita: insert, upsert, update, delete
5. Transações, locks e deadlocks
6. Pool e conexões

## 1. Segurança: parametrização
Toda entrada externa vai como **parâmetro**, nunca concatenada ou interpolada em SQL. É o item de severidade crítica em qualquer auditoria. Identificadores (nome de tabela/coluna, direção de `ORDER BY`) não podem ser parâmetros: valide contra uma **lista permitida** no código.

```python
# errado
cur.execute(f"SELECT * FROM usuario WHERE email = '{email}'")
# certo
cur.execute("SELECT id, nome FROM usuario WHERE email = %s", (email,))
```
O mesmo vale para ORMs: cuidado com `text()`/`raw()`/`literal_column` com valores interpolados. A aplicação usa um usuário só com `SELECT, INSERT, UPDATE, DELETE`; DDL fica com o usuário das migrations.

## 2. Leitura
- Liste as colunas necessárias; evite `SELECT *` (quebra com mudança de schema, impede índice cobrindo, trafega dados inúteis, especialmente `TEXT`/`BLOB`).
- **N+1**: um loop que dispara uma query por item → um `JOIN` ou `WHERE id IN (...)` em lote (em ORMs: eager loading / `selectinload` / `joinedload`).
- `EXISTS` em vez de `COUNT(*) > 0`; `LIMIT 1` quando só importa a primeira linha.
- Evite `ORDER BY RAND()`; para amostragem use faixa de PK aleatória.
- `COUNT(*)` exato em tabelas grandes é caro (InnoDB conta varrendo): ofereça contagem aproximada ou materializada quando o produto aceitar.
- Predicados SARGable e tipos compatíveis (ver `indices-explain.md`). `LIKE 'termo%'` usa índice; `LIKE '%termo%'` não — use `FULLTEXT` ou um motor de busca.
- Leituras de relatório pesadas: réplica de leitura, ciente do lag; nunca na primária em horário de pico.

## 3. Paginação
`LIMIT 20 OFFSET 100000` lê e descarta 100 mil linhas. Use **keyset (seek)** com uma ordenação determinística e índice que a suporte:

```sql
-- 1ª página
SELECT id, criado_em, total FROM pedido
WHERE cliente_id = ? ORDER BY criado_em DESC, id DESC LIMIT 20;
-- próxima página: passe (criado_em, id) da última linha vista
SELECT id, criado_em, total FROM pedido
WHERE cliente_id = ? AND (criado_em, id) < (?, ?)
ORDER BY criado_em DESC, id DESC LIMIT 20;
-- índice: (cliente_id, criado_em, id)
```
Sempre inclua um desempate único (`id`) na ordenação; sem ele há linhas repetidas ou perdidas entre páginas.

**Índice e `ORDER BY` precisam ter a mesma direção em todas as colunas.** A comparação de linha `(a, b) < (?, ?)` só vira um range scan eficiente assim; com direções mistas (`a DESC, b ASC`) ela não equivale à ordenação. Nesse caso crie o índice com as mesmas direções (`INDEX (a DESC, b ASC)`, 8.0+), escreva o filtro expandido (`a < ? OR (a = ? AND b > ?)`) e confirme com `EXPLAIN ANALYZE`. Se o produto exige "ir para a página N", limite a profundidade ou use `OFFSET` só nas primeiras páginas.

## 4. Escrita

**Insert em lote** — um `INSERT` com várias linhas (centenas a poucos milhares por comando, abaixo de `max_allowed_packet`) é ordens de grandeza mais rápido que um por linha. Em carga massiva, `LOAD DATA` e transação única por lote.

**Upsert**
```sql
INSERT INTO estoque (produto_id, qtd) VALUES (?, ?) AS novo
ON DUPLICATE KEY UPDATE qtd = estoque.qtd + novo.qtd;
```
(Alias de linha: 8.0.19+; `VALUES(col)` está obsoleto. Exige `UNIQUE`/PK na chave do conflito.) Em tabelas com `AUTO_INCREMENT`, upserts consomem ids mesmo sem inserir: normal.

**Update**
- Sempre com `WHERE` por chave; cheque `affected_rows` (lembre que o MySQL conta só linhas **alteradas**, a menos que a conexão use `CLIENT_FOUND_ROWS`).
- Atualização relativa e atômica (`SET qtd = qtd - 1 WHERE id = ? AND qtd > 0`) evita ler-modificar-gravar e corrida entre requisições.
- Controle de concorrência otimista: coluna `versao`; `UPDATE ... SET versao = versao + 1 WHERE id = ? AND versao = ?`.

**Delete / update grandes** — em **lotes por faixa de PK** (1–10 mil linhas), transação curta, pausa e checagem de lag de réplica; um único `DELETE` de milhões de linhas gera lock longo, undo enorme e lag. Para expurgo recorrente, particionar por data e `DROP PARTITION` é muito mais barato.

Use `LAST_INSERT_ID()` (por conexão), nunca `MAX(id)`.

## 5. Transações, locks e deadlocks
- Nível padrão do InnoDB: `REPEATABLE READ` (com *gap locks* em leituras de travamento por faixa). `READ COMMITTED` reduz contenção e gap locks; adote conscientemente, exige binlog `ROW`.
- **Transação curta**: sem chamada de rede, espera de usuário ou processamento pesado dentro dela. Abra tarde, feche cedo.
- **Ordem consistente de acesso** às linhas/tabelas entre fluxos: a principal defesa contra deadlock.
- Trave pelo **índice**: `UPDATE`/`SELECT ... FOR UPDATE` sem índice utilizável trava muito mais do que as linhas desejadas.
- **Filas de trabalho**: `SELECT ... FOR UPDATE SKIP LOCKED LIMIT n` (8.0+) permite vários consumidores sem bloqueio mútuo.
- **Retry**: capture erro 1213 (deadlock) e, com cautela, 1205 (lock wait timeout); refaça a **transação inteira** com *backoff* e limite de tentativas. Deadlocks ocasionais são normais; frequentes indicam problema de ordem/índice. Investigue com `SHOW ENGINE INNODB STATUS` (seção `LATEST DETECTED DEADLOCK`) e `performance_schema.data_locks` (8.0).

## 6. Pool e conexões
Um pool por processo, dimensionado para `max_connections` ÷ número de instâncias, com *timeouts*, validação de conexão (`pool_pre_ping`), reciclagem antes do `wait_timeout` e TLS. Mais conexões não é mais desempenho: o excedente vira fila e contenção.
