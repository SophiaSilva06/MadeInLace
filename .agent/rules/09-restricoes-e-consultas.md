---
trigger: always_on
description: "Restrições estritas: consulta prévia para bibliotecas e proibição de suposições."
---

# Restrições e Consultas Prévias

- **Bibliotecas e Dependências:** É estritamente proibido adicionar, instalar ou incluir qualquer nova biblioteca, pacote ou dependência (seja em `requirements.txt`, `pip`, `npm`, etc.) sem perguntar e obter autorização prévia e explícita do usuário. Toda solicitação deve justificar claramente a necessidade e a versão proposta.
- **Não assumir nada:** Nunca presuma requisitos, regras de negócio, infraestrutura ou comportamentos em aberto. Em caso de dúvida, ambiguidade ou lacuna na documentação, pare e pergunte diretamente ao usuário antes de tomar qualquer decisão ou alterar código.
