---
trigger: always_on
description: "Contratos de API e banco só mudam por pedido explícito; proteção contra operações destrutivas no banco."
---

# Contratos e dados

- Contratos (schema do banco, payloads, endpoints, status codes) só mudam por pedido explícito. Se for necessário mudar, descreva a proposta (campo, motivo, impacto, compatibilidade) e aguarde aprovação. Não presuma que a mudança existe.
- Frontend adapta dados no cliente; backend não quebra o frontend existente sem versionar.
- O schema só muda por alteração explícita e revisável do script do banco (`db/schema.sql`); o projeto não usa versionamento de banco. Nada de `create_all` fora de teste.
- Nunca execute `DROP`, `TRUNCATE`, `ALTER` destrutivo ou `UPDATE`/`DELETE` em massa fora de banco local ou de teste sem autorização explícita. Em dúvida sobre qual banco está conectado, pare e confirme.
- Os models do ORM permanecem idênticos ao banco (tipos, tamanhos, nulabilidade, nomes).
