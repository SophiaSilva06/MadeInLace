# Índices e planos de execução (EXPLAIN ANALYZE)

## Sumário
1. Como coletar queries candidatas
2. Ler EXPLAIN ANALYZE
3. Projetar índices
4. Validar, medir custo e limpar
5. Problemas comuns e correções

## 1. Coletar queries candidatas
Priorize por **tempo total** (frequência × duração), não só pela query mais lenta isolada.

```sql
-- Top queries por tempo total (performance_schema, MySQL 5.7+/8.0)
SELECT digest_text, count_star, ROUND(sum_timer_wait/1e12,2) AS total_s,
       ROUND(avg_timer_wait/1e9,2) AS avg_ms, sum_rows_examined, sum_rows_sent,
       sum_no_index_used, sum_created_tmp_disk_tables
FROM performance_schema.events_statements_summary_by_digest
WHERE schema_name = DATABASE() ORDER BY sum_timer_wait DESC LIMIT 20;

-- Atalhos do schema sys
SELECT * FROM sys.statements_with_full_table_scans LIMIT 20;
SELECT * FROM sys.schema_unused_indexes;        -- candidatos a remoção
SELECT * FROM sys.schema_redundant_indexes;     -- prefixos duplicados
```
Também vale o slow query log e as queries lidas direto do código. Os contadores do `performance_schema` zeram no restart: avise se o uptime for curto.

## 2. Ler EXPLAIN ANALYZE

`EXPLAIN ANALYZE` (MySQL ≥ 8.0.18) **executa** a query e mostra o plano em árvore com estimativa e medição reais. Em consultas com efeito colateral (UPDATE/DELETE, conforme o suporte da versão) rode dentro de transação com `ROLLBACK` em ambiente seguro, ou prefira `EXPLAIN` simples. Em MariaDB use `ANALYZE FORMAT=JSON <query>`.

```sql
EXPLAIN ANALYZE
SELECT p.id, p.total FROM pedido p
WHERE p.cliente_id = 42 AND p.status = 'PAGO' ORDER BY p.criado_em DESC LIMIT 20;
```

O que olhar em cada nó (`cost=... rows=...` estimado; `actual time=primeira..total rows=N loops=L` medido):
- **rows estimado ≫ ou ≪ rows real** → estatísticas defasadas ou distribuição enviesada: `ANALYZE TABLE t;` e, se persistir, histograma (`ANALYZE TABLE t UPDATE HISTOGRAM ON col;`) para colunas sem índice usadas em filtro.
- **`actual time` total ≈ `loops` × tempo por loop** → o custo real de um nested loop é multiplicado pelas iterações; muitas iterações num lado interno sem índice é o clássico gargalo.
- **`Table scan`** com muitas linhas e filtro depois (`Filter:`) → falta índice ou o predicado não é SARGable.
- **`Sort` / `Sort: ... external`** sobre muitas linhas, ou `Temporary table` → índice que entregue a ordem (ou o agrupamento) elimina o passo.
- **`Index lookup` / `Index range scan` / `Covering index`** → bom sinal, desde que as linhas lidas sejam próximas das retornadas.
- **Linhas lidas ≫ linhas retornadas** é a medida central de ineficiência.

Compare **antes/depois** com os mesmos parâmetros e dados quentes (rode 2×: a primeira aquece o buffer pool). Informe `actual time` e linhas lidas, não só "ficou mais rápido".

`EXPLAIN` tabular/`FORMAT=JSON` mostram o `key_len` (quantas colunas do índice composto foram usadas) e são o que existe no 5.7.

## 3. Projetar índices

**Ordem das colunas num índice composto:**
1. Colunas com **igualdade** (`=`, `IN` curto) primeiro, das mais seletivas/consistentes para as menos;
2. depois a coluna de **ordenação** (`ORDER BY`) se a query tiver `LIMIT` — assim o índice entrega ordenado e a leitura para cedo;
3. a coluna com **faixa** (`>`, `<`, `BETWEEN`, `LIKE 'x%'`) por último, porque colunas depois dela não filtram por índice.

Para o exemplo acima: `INDEX (cliente_id, status, criado_em)`.

**Regras práticas**
- Vale a **regra do prefixo mais à esquerda**: `(a,b,c)` atende `a`, `a,b`, `a,b,c`, não `b` sozinho. Um índice `(a,b)` torna `(a)` redundante.
- **Cobertura** (`covering index`): se a query só usa colunas do índice, o InnoDB nem toca a tabela (`Using index`). Inclua colunas extras só para queries muito quentes; cada coluna aumenta o índice. Todo índice secundário já carrega a PK.
- **Seletividade**: índice em coluna de poucos valores (flag, status) sozinho raramente ajuda; como **prefixo de composto** com outro filtro, sim.
- **Predicados SARGable**: `WHERE criado_em >= '2026-01-01' AND criado_em < '2026-02-01'` em vez de `WHERE DATE(criado_em) = ...`; compare tipos iguais (string vs. número gera conversão e perde o índice); evite `OR` entre colunas diferentes (reescreva com `UNION ALL`).
- **Funcional / coluna gerada** (8.0.13+): `INDEX ((LOWER(email)))` ou coluna virtual indexada, quando a função é inevitável.
- **Descendente** (8.0): `INDEX (a ASC, b DESC)` quando o `ORDER BY` mistura direções.
- **Prefixo em texto longo**: `INDEX (descricao(32))` só serve para igualdade/prefixo, não para ordenar; prefira `FULLTEXT` para busca de palavras.
- **PK e FKs**: toda FK com índice no filho; PK curta (o tamanho da PK é copiado para todos os índices secundários).
- **Evite** índices duplicados e índice em toda coluna "por garantia": cada `INSERT`/`UPDATE` mantém todos eles.

## 4. Validar, medir custo e limpar
1. Crie o índice com Online DDL (`ALGORITHM=INPLACE, LOCK=NONE`) — ver `migrations-zero-downtime.md`.
2. Rode `EXPLAIN ANALYZE` de novo e confirme que o otimizador **escolheu** o índice (`USE INDEX` só para diagnóstico, não em produção, salvo exceção documentada).
3. Verifique o **custo de escrita**: tempo de `INSERT`/`UPDATE` representativo e tamanho do índice (`information_schema.tables.index_length`, `mysql.innodb_index_stats`).
4. Para **remover** índice: torne-o invisível (`ALTER TABLE t ALTER INDEX i INVISIBLE;`), observe por um ciclo de negócio, depois `DROP INDEX`. Reversão imediata com `VISIBLE`. (MariaDB 10.6+: `IGNORED` / `NOT IGNORED`.)

## 5. Problemas comuns

| Sintoma no plano | Causa provável | Correção |
|---|---|---|
| JOIN com muitos `loops` sem índice no lado interno | FK/chave de junção sem índice, collation ou tipo divergentes | Indexar chave de junção; alinhar collation/tipo |
| Estimativa muito diferente do real | Estatísticas velhas, dados enviesados | `ANALYZE TABLE`, histograma |
| `OFFSET` grande lento | Descarta linhas lidas | Paginação keyset, com índice e `ORDER BY` na mesma direção (`queries-crud.md`) |
| `COUNT(*)` lento em tabela grande | Varredura do menor índice | Contador materializado/aproximação, ou filtro indexado |
| `SELECT DISTINCT`/`GROUP BY` com tabela temporária | Falta índice para agrupar | Índice nas colunas de agrupamento |
| Subquery correlata repetida | Executa por linha externa | `JOIN`/`EXISTS` ou CTE; confira o plano |
| Funciona em dev, lento em produção | Pouco volume em dev / estatísticas diferentes | Testar com cópia de volume realista |
