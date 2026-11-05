---
trigger: always_on
description: "Mínimo de segurança em toda mudança: segredos, entrada hostil, autorização, sessão, dependências."
---

# Segurança: mínimo em toda mudança

- **Segredos:** nunca em código, testes, logs, commits, exemplos ou no chat. Use `.env` fora do git e um `.env.example` sem valores reais. Se encontrar um, mascare (`sk-…abcd`) e recomende revogar antes de qualquer outra coisa.
- **Toda entrada é hostil:** SQL só parametrizado ou via ORM (identificador dinâmico só por allowlist). Nunca monte comando de shell, caminho de arquivo, URL de saída ou template Jinja2 com dado do usuário.
- **Saída escapada:** sem `|safe` nem `innerHTML` com dado externo.
- **Autorização no servidor, por objeto,** em toda rota (dono ou papel). Validação no cliente não conta.
- **Sessão:** cookie `HttpOnly`, `Secure`, `SameSite`; CSRF em formulário que altera estado; senha com Argon2id ou bcrypt; erros sem detalhes internos.
- **Dependência nova:** justifique, fixe a versão e desconfie de nome parecido com pacote conhecido.
- Código sensível (login, recuperação de senha, pagamento, upload, permissões) ou pedido de merge/PR: use a skill `secops-guardian`.
