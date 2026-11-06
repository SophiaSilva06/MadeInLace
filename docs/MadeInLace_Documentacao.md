# MadeInLace — Documentação do Projeto

Loja virtual de roupas e calçados femininos inspirada na loja real **LaceMade**. Projeto estudantil: o pagamento é apenas simulado e o rastreamento de entrega não usa API de transportadora.

---

## Sumário

1. [Visão geral](#1-visão-geral)
2. [Cadastro e conta do usuário](#2-cadastro-e-conta-do-usuário)
3. [Autenticação e segurança](#3-autenticação-e-segurança)
4. [Recuperação de senha e de e-mail](#4-recuperação-de-senha-e-de-e-mail)
5. [Endereços](#5-endereços)
6. [Catálogo de produtos](#6-catálogo-de-produtos)
7. [Navegação e busca](#7-navegação-e-busca)
8. [Estoque e reservas](#8-estoque-e-reservas)
9. [Carrinho](#9-carrinho)
10. [Checkout e pagamento](#10-checkout-e-pagamento)
11. [Pedido: desconto, frete e cálculo](#11-pedido-desconto-frete-e-cálculo)
12. [Status, entrega e histórico](#12-status-entrega-e-histórico)
13. [Trocas e reembolsos](#13-trocas-e-reembolsos)
14. [Avaliações](#14-avaliações)
15. [Exclusão de dados e LGPD](#15-exclusão-de-dados-e-lgpd)
16. [Requisitos não funcionais](#16-requisitos-não-funcionais)
17. [Dicionário de tipos de dados](#17-dicionário-de-tipos-de-dados)

Anexo A. [Tabela de frete](#anexo-a--tabela-de-frete)

---

## 1. Visão geral

| Item | Descrição |
|---|---|
| Nome da loja | MadeInLace |
| Segmento | Roupas e calçados femininos |
| Inspiração | Loja real LaceMade |
| Natureza | Projeto estudantil |
| Banco de dados | MySQL 8.0.16+ (InnoDB, utf8mb4) |
| Pagamento | Simulado (apenas registro no banco) |
| Rastreamento de entrega | Simulado (sem API de transportadora) |

---

## 2. Cadastro e conta do usuário

### 2.1 Dados exigidos no cadastro
- O cadastro exige as informações essenciais: nome, sobrenome, CPF (válido e único), e-mail, telefone, data de nascimento, senha e ao menos um endereço de entrega.
- Ao se registrar, é necessário adicionar pelo menos um endereço.
- Usuário e endereço são gravados na mesma transação.
- Cada e-mail pode ter um único cadastro.
- Idade mínima de 18 anos para cadastro (capacidade civil para contratar).

### 2.2 Validação no cadastro
- Caso algo esteja inválido, não é possível se cadastrar.
- A senha é verificada pelos fatores mínimos e recebe uma marcação positiva caso esteja válida e uma negativa caso esteja inválida.

### 2.3 Regras da senha
- Mínimo de 12 caracteres, com pelo menos 1 letra maiúscula, 1 minúscula, 1 número e 1 símbolo.
- Não pode ser igual ao e-mail.
- É armazenada em hash argon2.
- Nunca aparece em log, e-mail ou resposta.

### 2.4 Alteração de dados pelo cliente
- O cliente pode alterar nome, sobrenome, telefone, senha e e-mail.
- Alterar a senha exige a senha atual.
- Alterar o e-mail exige a senha atual e nova confirmação por link.
- CPF e data de nascimento só mudam via suporte.

---

## 3. Autenticação e segurança

- O acesso é feito por e-mail e senha.
- Após 5 tentativas de login falhas em 15 minutos (por IP + e-mail), o acesso é bloqueado temporariamente.
- A mensagem de erro é sempre genérica: "e-mail ou senha inválidos".
- Após redefinir a senha, as sessões ativas são encerradas e o cliente recebe um aviso por e-mail.

---

## 4. Recuperação de senha e de e-mail

### 4.1 Recuperação de senha
- É possível recuperar a conta (alteração da senha) usando um token aleatório de verificação, de no mínimo 32 bytes, enviado ao e-mail da conta a ser recuperada.
- Grava-se apenas o hash do token.
- O token tem validade de 1 hora e é de uso único.
- Um novo pedido marca os antigos como expirados, invalidando-os.
- A resposta é sempre genérica ("se o e-mail estiver cadastrado, enviaremos as instruções"), para não revelar quais e-mails existem.

### 4.2 Recuperação de e-mail esquecido
- O e-mail esquecido pode ser recuperado informando CPF e data de nascimento.
- O sistema exibe apenas o e-mail mascarado (ex.: `j***@g***.com`).
- Há limite de tentativas.

---

## 5. Endereços

### 5.1 Gerenciamento
- Na página do perfil, o cliente adiciona, edita e remove endereços.
- O usuário deve ter pelo menos um endereço ativo em qualquer momento; o último endereço não pode ser removido.
- Limite de 10 endereços ativos por usuário.
- Um endereço pode ser marcado como principal (pré-selecionado no checkout).

### 5.2 Campos
- CEP (8 dígitos), logradouro, número, complemento (opcional), bairro, cidade e estado (UF).
- Há consulta automática à API de CEP, que retorna bairro, cidade e UF, autocompletando as caixas da aba de edição de endereços no perfil.
- Os dados são gravados como texto no endereço.
- Apenas endereços do Brasil.

### 5.3 Imutabilidade
- Endereço usado em uma venda é imutável: a edição cria um novo registro e inativa o anterior, preservando o histórico do pedido.

### 5.4 Entrega
- A entrega é feita para todo o Brasil; não há entrega para o exterior (endereços fora do país não são aceitos).
- O endereço de entrega é escolhido no checkout entre os endereços ativos do cliente.

---

## 6. Catálogo de produtos

### 6.1 Estrutura do produto
- Todo produto tem fornecedor, linha, tipo, imagens e variações (tamanho × cor).
- Produtos nunca são excluídos fisicamente (soft delete).

### 6.2 Visibilidade
- Só aparecem no site produtos ativos com ao menos uma variação ativa.
- Variação sem estoque disponível aparece desabilitada.
- Produto sem nenhuma variação disponível exibe "Esgotado" e não pode ser adicionado ao carrinho.

### 6.3 Promoções
- Promoção é um percentual (0 a 90) no produto.
- Preço final = preço × (1 − % / 100), arredondado a 2 casas.
- Com promoção ativa, o card mostra o preço original riscado e o preço final.

### 6.4 Best Sellers
- São os produtos mais vendidos (soma de unidades em pedidos pagos nos últimos 30 dias).
- Limitados a 12 e recalculados diariamente.

### 6.5 Selos
- "Promoção" quando % > 0.
- "Best Seller" quando está no ranking.

### 6.6 Nota exibida
- A nota exibida é a média das avaliações ativas, com 1 casa decimal.
- Sem avaliações, a nota não é exibida.

---

## 7. Navegação e busca

### 7.1 Menu Explorar
- Exibe as 4 linhas ativas mais recentes (por data de lançamento).

### 7.2 Seções do nav
| Seção | Critério |
|---|---|
| Saltos | Por tipo |
| Corsets | Por tipo |
| Vestidos | Por tipo |
| Plus Size | Por tamanho |
| Promoção | Produtos com % > 0 |
| Produtos | Todos |

### 7.3 Busca
- A busca pode ser feita pelo nome dos produtos ou pelas linhas deles, alternando o tipo de pesquisa em um espaço de seleção.
- A busca pesquisa pelos caracteres escritos, procurando um match em um nome ou linha.
- Os resultados são demonstrados ao apertar Enter, o que leva para a página que lista os produtos encontrados relacionados.

---

## 8. Estoque e reservas

### 8.1 Controle de estoque
- O estoque é controlado por variação.
- O total do produto é a soma das variações e é mantido pelo sistema.
- Estoque disponível = estoque físico − reservas ativas de outros carrinhos.

### 8.2 Reserva por item
- Cada produto do carrinho tem um timer de 10 minutos, no qual é descontado do estoque, ficando reservado.
- Ao adicionar um produto, 1 unidade fica reservada para o usuário por 10 minutos.
- A reserva cobre 1 unidade por item do carrinho. Quantidades adicionais dependem da disponibilidade na hora do checkout.
- Após os 10 minutos, o item volta ao estoque e não está mais reservado. Se o estoque acabar depois disso, o produto fica indisponível para a compra.

### 8.3 Fim da reserva
- Terminada a reserva, o item permanece no carrinho, mas sem garantia.
- Se ainda houver unidade disponível, o cliente pode comprar (a reserva é renovada por 10 minutos ao iniciar o checkout).
- Se as unidades acabarem, o item aparece como "Indisponível" e não permite concluir a compra até ser removido.

### 8.4 Timer
- O timer de cada item (carrinho lateral e página de carrinho) é calculado a partir do horário de expiração gravado no servidor; o cliente apenas exibe a contagem regressiva.

### 8.5 Concorrência
- A validação final de estoque no checkout ocorre dentro de transação com bloqueio de linha (`SELECT ... FOR UPDATE`), impedindo venda acima do estoque.

---

## 9. Carrinho

- Cada usuário tem um carrinho.
- O carrinho exige login. Visitante que tenta adicionar um item é enviado ao login e retorna ao produto depois.
- O carrinho é persistido no banco e acompanha o usuário entre sessões e dispositivos.
- Máximo de 10 unidades por variação em um mesmo carrinho.
- Preços do carrinho são sempre recalculados a partir do catálogo; se mudaram desde a inclusão, o cliente é avisado.
- Ao concluir a compra, as reservas são consumidas e o carrinho é esvaziado.

---

## 10. Checkout e pagamento

### 10.1 Etapas
- O checkout verifica o endereço, seleciona o método de pagamento e conclui a compra.

### 10.2 Condições para concluir
- Estar logado.
- Ter ao menos um item e todos os itens disponíveis.
- Ter endereço ativo selecionado.

### 10.3 Métodos de pagamento
- Métodos previstos: Pix, cartão de crédito, cartão de débito e boleto (cadastrados em tabela de métodos).
- O pagamento não é realmente realizado, apenas registrado no banco (simulando a conclusão de um pagamento, por ser um projeto estudantil).
- O método de pagamento é apenas selecionado; não há inserção de dados como número de cartão, pois é uma simulação.

### 10.4 Idempotência e snapshot
- O envio do checkout é idempotente: duplo clique ou reenvio não gera dois pedidos.
- Preços e totais do pedido são um retrato do momento da compra (preço unitário gravado no item) e não mudam depois.

---

## 11. Pedido: desconto, frete e cálculo

### 11.1 Desconto de primeira compra
- Os 10% de desconto são válidos apenas para a primeira compra do usuário.
- "Primeira compra" significa que o usuário (e o CPF) não possui pedido anterior em status diferente de cancelado. Pedidos cancelados ou expirados sem pagamento não consomem o benefício.
- O desconto é aplicado automaticamente no checkout sobre o subtotal dos produtos (já com promoções) e não incide sobre o frete.

### 11.2 Frete
- Frete é grátis para compras a partir de R$ 160,00 (medido pela base do frete, seção 11.3), em qualquer UF.
- Abaixo disso, o frete é um valor fixo por UF do endereço de entrega, conforme a tabela do Anexo A (simulação, sem API de transportadora).

### 11.3 Fórmulas do pedido
| Item | Fórmula |
|---|---|
| Subtotal | soma de (preço final × quantidade) |
| Desconto | subtotal × 10% quando elegível |
| Base do frete | subtotal − desconto |
| Total | subtotal − desconto + frete |

---

## 12. Status, entrega e histórico

- A data de entrega é registrada quando o pedido muda para ENTREGUE e marca o início dos 30 dias de troca.
- Toda mudança de status, tanto da troca quanto da venda, gera um registro no histórico (apenas inserção, nunca alteração).
- O cliente só enxerga os próprios pedidos.

---

## 13. Trocas e reembolsos

### 13.1 Prazo e elegibilidade
- Reembolsos e trocas podem ser feitos com a devolução do produto em boa qualidade durante os primeiros 30 dias após a chegada do produto.
- Estando fora do prazo de 30 dias, itens de venda perdem os botões para troca e reembolso.
- Só itens de pedidos com status ENTREGUE podem ser solicitados.
- A quantidade solicitada não pode exceder a quantidade comprada menos a já solicitada.

### 13.2 Por produto
- As trocas e reembolsos são feitos por cada produto; não há uma opção para trocar ou reembolsar tudo de uma vez.

### 13.3 Troca
- A troca depende de estoque da variação desejada; sem estoque, o cliente opta por outra variação ou por reembolso.

### 13.4 Reembolso
- É feito pelo mesmo meio de pagamento, pelo valor efetivamente pago pelo item (considerando desconto proporcional).
- O frete é reembolsado em defeito e em arrependimento total.

### 13.5 Destino do item devolvido
- Item devolvido com defeito não volta ao estoque.
- Item em perfeito estado volta após conferência.

---

## 14. Avaliações

- Só avalia quem comprou e recebeu o produto (pedido ENTREGUE).
- Uma avaliação por produto por usuário.
- Nota inteira de 1 a 5.
- Comentário opcional de até 1000 caracteres.

---

## 15. Exclusão de dados e LGPD

- A exclusão de conta é lógica (ativo = 0).
- Dados pessoais são anonimizados após o prazo legal, preservando vendas e dados fiscais (LGPD).
- A exclusão dos dados das colunas das tabelas do banco é lógica (ativo = 0), sendo apenas realmente deletados pelo database admin, caso necessário.

---

## 16. Requisitos não funcionais

| Categoria | Requisito |
|---|---|
| SEO | URLs amigáveis, títulos e meta descrições por página, sitemap |
| Desempenho | Páginas principais com LCP abaixo de 2,5 s; respostas de API no percentil 95 abaixo de 500 ms |
| Acessibilidade | Meta WCAG 2.1 nível AA (contraste, foco visível) |
| Localização | Idioma pt-BR e moeda BRL (valores monetários sempre em DECIMAL, nunca em ponto flutuante) |

---

## 17. Dicionário de tipos de dados

### 17.1 Convenções do banco
- Nomes em MAIÚSCULAS, sem acento; chave primária = `ID`; chaves estrangeiras = `FK_<ALVO>`.
- Dinheiro: `DECIMAL(10,2)`. Booleanos: `TINYINT(1)`. Datas: `DATETIME` (exceto nascimento, que é `DATE`).
- Máscaras (CPF, CNPJ, CEP, telefone) não são gravadas: apenas dígitos.
- Imagens: é guardado apenas o caminho relativo na pasta do servidor.

### 17.2 Tipos utilizados

| Tipo | Descrição | Faixa / tamanho | Uso no banco |
|---|---|---|---|
| `TINYINT UNSIGNED` | Inteiro muito pequeno, sem sinal | 0 a 255 | IDs de tabelas de domínio pequenas (método de pagamento, status), `NOTA` |
| `SMALLINT UNSIGNED` | Inteiro pequeno, sem sinal | 0 a 65.535 | IDs de linha e fornecedor, `QNT` |
| `INT UNSIGNED` | Inteiro, sem sinal | 0 a 4.294.967.295 | IDs das demais tabelas, chaves estrangeiras, `ESTOQUE` |
| `TINYINT(1)` | Booleano (0 ou 1) | 1 byte | `ATIVO`, `IS_ADM`, `EXPIRADO`, `DESCONTO`, `FRETE_GRATIS`, `CONCLUSAO` |
| `DECIMAL(10,2)` | Decimal exato, até 10 dígitos com 2 casas | até 99.999.999,99 | Valores monetários |
| `DECIMAL(5,2)` | Decimal exato, até 5 dígitos com 2 casas | até 999,99 | `PORCENTAGEM_PROMOCAO` |
| `CHAR(n)` | Texto de tamanho fixo | n caracteres | CNPJ (14), CPF (11), CEP (8), UF (2), DDD (2), token (64) |
| `VARCHAR(n)` | Texto de tamanho variável | até n caracteres | Nomes, e-mails, endereços, motivos, comentários, caminhos de imagem |
| `TEXT` | Texto longo | até 65.535 bytes | `DESCRICAO` de produtos |
| `ENUM(...)` | Lista fixa de valores | 1 valor da lista | Tipo do produto, status do carrinho, estados de venda e de troca |
| `DATE` | Data | AAAA-MM-DD | `NASCIMENTO` |
| `DATETIME` | Data e hora | AAAA-MM-DD hh:mm:ss | Criação, expiração, eventos, reservas, conclusões |

### 17.3 Tipos por tabela

#### Tabelas de domínio

**LINHA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `SMALLINT UNSIGNED` | Não | PK, auto incremento |
| NOME | `VARCHAR(100)` | Não | Único |

**METODO_PAGAMENTO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `TINYINT UNSIGNED` | Não | PK, auto incremento |
| METODO | `VARCHAR(30)` | Não | Único. Valores iniciais: Pix, Cartão de crédito, Cartão de débito, Boleto |

**STATUS_VENDA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `TINYINT UNSIGNED` | Não | PK, auto incremento |
| ESTADO_ANDAMENTO | `ENUM` | Não | EM_PROCESSAMENTO, NA_TRANSPORTADORA, EM_TRANSITO, ENTREGANDO, ENTREGUE, TENTATIVA_FALHA, CANCELADO |
| DESCRICAO | `VARCHAR(80)` | Não | Texto exibido ao cliente |

**STATUS_TROCA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `TINYINT UNSIGNED` | Não | PK, auto incremento |
| ESTADO_ANDAMENTO | `ENUM` | Não | SOLICITADA, APROVADA, DEVOLUCAO_RECEBIDA, EM_PROCESSAMENTO, NA_TRANSPORTADORA, ENTREGANDO, ENTREGUE, RECUSADA |
| DESCRICAO | `VARCHAR(80)` | Não | Texto exibido ao cliente |

#### Fornecedores

**FORNECEDORES**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `SMALLINT UNSIGNED` | Não | PK, auto incremento |
| NOME | `VARCHAR(100)` | Não | |
| CNPJ | `CHAR(14)` | Não | Único, só dígitos |
| RAZAO_SOCIAL | `VARCHAR(150)` | Não | |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

**EMAILS_FORNECEDOR**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_FORNECEDOR | `SMALLINT UNSIGNED` | Não | FK para FORNECEDORES |
| EMAIL | `VARCHAR(254)` | Não | |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

**TELEFONE_FORNECEDOR**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_FORNECEDOR | `SMALLINT UNSIGNED` | Não | FK para FORNECEDORES |
| DDD | `CHAR(2)` | Não | |
| TELEFONE | `VARCHAR(9)` | Não | |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

**ENDERECO_FORNECEDOR**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_FORNECEDOR | `SMALLINT UNSIGNED` | Não | FK para FORNECEDORES |
| CEP | `CHAR(8)` | Não | Só dígitos |
| LOGRADOURO | `VARCHAR(120)` | Não | |
| NUMERO | `VARCHAR(10)` | Não | |
| COMPLEMENTO | `VARCHAR(80)` | Sim | |
| BAIRRO | `VARCHAR(80)` | Não | |
| CIDADE | `VARCHAR(60)` | Não | |
| ESTADO | `CHAR(2)` | Não | UF |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

#### Produtos

**PRODUTOS**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_FORNECEDOR | `SMALLINT UNSIGNED` | Não | FK para FORNECEDORES |
| FK_LINHA | `SMALLINT UNSIGNED` | Não | FK para LINHA |
| NOME | `VARCHAR(150)` | Não | |
| DESCRICAO | `TEXT` | Sim | |
| TIPO | `ENUM` | Não | roupa, calcado, corset |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |

**IMGS_PRODUTOS**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_PRODUTO | `INT UNSIGNED` | Não | FK para PRODUTOS |
| URL_IMAGEM | `VARCHAR(255)` | Não | Caminho relativo na pasta do servidor |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

**VARIACAO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_PRODUTO | `INT UNSIGNED` | Não | FK para PRODUTOS |
| TAMANHO | `VARCHAR(10)` | Não | |
| COR | `VARCHAR(30)` | Não | |
| ESTOQUE | `INT UNSIGNED` | Não | Padrão 0 |
| CUSTO | `DECIMAL(10,2)` | Não | |
| PRECO | `DECIMAL(10,2)` | Não | |
| PORCENTAGEM_PROMOCAO | `DECIMAL(5,2)` | Não | Padrão 0,00 |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

#### Usuários

**USUARIOS**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| NOME | `VARCHAR(50)` | Não | |
| SOBRENOME | `VARCHAR(100)` | Não | |
| EMAIL | `VARCHAR(254)` | Não | Único |
| SENHA_HASH | `VARCHAR(255)` | Não | Hash da senha |
| NASCIMENTO | `DATE` | Sim | |
| CPF | `CHAR(11)` | Sim | Único, só dígitos |
| TELEFONE | `VARCHAR(11)` | Sim | DDD + número, só dígitos |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |
| IS_ADM | `TINYINT(1)` | Não | Padrão 0 |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |

**ENDERECO_USUARIO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_USUARIO | `INT UNSIGNED` | Não | FK para USUARIOS |
| NOME | `VARCHAR(50)` | Não | Apelido (ex.: "Casa", "Trabalho") |
| CEP | `CHAR(8)` | Não | Só dígitos |
| LOGRADOURO | `VARCHAR(120)` | Não | |
| NUMERO | `VARCHAR(10)` | Não | |
| COMPLEMENTO | `VARCHAR(80)` | Sim | |
| BAIRRO | `VARCHAR(80)` | Não | |
| CIDADE | `VARCHAR(60)` | Não | |
| ESTADO | `CHAR(2)` | Não | UF |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

**RECUPERACAO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_USUARIO | `INT UNSIGNED` | Não | FK para USUARIOS |
| TOKEN | `CHAR(64)` | Não | Único. Hash do token enviado por e-mail |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |
| DATA_EXPIRA | `DATETIME` | Não | |
| EXPIRADO | `TINYINT(1)` | Não | Padrão 0. 1 quando usado ou invalidado |

**VERIFICACAO_EMAIL**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| EMAIL | `VARCHAR(254)` | Não | E-mail destinatário da verificação |
| TOKEN | `CHAR(64)` | Não | Único. Hash SHA-256 do código de verificação |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |
| DATA_EXPIRA | `DATETIME` | Não | Data/hora de expiração do código |
| EXPIRADO | `TINYINT(1)` | Não | Padrão 0. 1 quando verificado ou expirado |
| TENTATIVAS | `TINYINT UNSIGNED` | Não | Padrão 0. Tentativas de validação |

#### Carrinho

**CARRINHO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_USUARIO | `INT UNSIGNED` | Não | FK para USUARIOS |
| STATUS | `ENUM` | Não | ATIVO, CONVERTIDO, ABANDONADO. Padrão ATIVO |
| TOTAL | `DECIMAL(10,2)` | Não | Padrão 0,00 |
| FRETE_GRATIS | `TINYINT(1)` | Não | Padrão 0 |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |
| FK_USUARIO_ATIVO | `INT UNSIGNED` | Sim | Coluna gerada (virtual) |

**ITEM_CARRINHO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_CARRINHO | `INT UNSIGNED` | Não | FK para CARRINHO |
| FK_VARIACAO | `INT UNSIGNED` | Não | FK para VARIACAO |
| QNT | `SMALLINT UNSIGNED` | Não | Padrão 1 |
| PRECO_UNITARIO | `DECIMAL(10,2)` | Não | |
| RESERVADO_ATE | `DATETIME` | Não | Horário em que a reserva expira |

#### Vendas

**VENDA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_CARRINHO | `INT UNSIGNED` | Não | FK para CARRINHO |
| FK_USUARIO | `INT UNSIGNED` | Não | FK para USUARIOS |
| FK_ENDERECO_USUARIO | `INT UNSIGNED` | Não | FK para ENDERECO_USUARIO |
| FK_METODO_PAGAMENTO | `TINYINT UNSIGNED` | Não | FK para METODO_PAGAMENTO |
| FK_STATUS | `TINYINT UNSIGNED` | Não | FK para STATUS_VENDA (status atual) |
| SUBTOTAL | `DECIMAL(10,2)` | Não | |
| FRETE | `DECIMAL(10,2)` | Não | Padrão 0,00 |
| DESCONTO | `TINYINT(1)` | Não | Padrão 0. 1 = 10% na primeira compra |
| TOTAL | `DECIMAL(10,2)` | Não | |
| FRETE_GRATIS | `TINYINT(1)` | Não | Padrão 0 |
| DATA | `DATETIME` | Não | Padrão: data/hora atual |

**HISTORICO_STATUS_VENDA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_VENDA | `INT UNSIGNED` | Não | FK para VENDA |
| FK_STATUS_VENDA | `TINYINT UNSIGNED` | Não | FK para STATUS_VENDA |
| DATA_EVENTO | `DATETIME` | Não | Padrão: data/hora atual |

**ITEM_VENDA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_VENDA | `INT UNSIGNED` | Não | FK para VENDA |
| FK_VARIACAO | `INT UNSIGNED` | Não | FK para VARIACAO |
| QNT | `SMALLINT UNSIGNED` | Não | |
| PRECO_UNITARIO | `DECIMAL(10,2)` | Não | Preço com promoção, congelado na compra |

#### Trocas e reembolsos

**TROCA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_ITEM_VENDA | `INT UNSIGNED` | Não | FK para ITEM_VENDA |
| FK_STATUS_TROCA | `TINYINT UNSIGNED` | Não | FK para STATUS_TROCA (status atual) |
| FK_VARIACAO_NOVA | `INT UNSIGNED` | Não | FK para VARIACAO (variação que o cliente receberá) |
| QNT | `SMALLINT UNSIGNED` | Não | Padrão 1 |
| MOTIVO | `VARCHAR(500)` | Sim | |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |
| CONCLUSAO | `TINYINT(1)` | Não | Padrão 0 |
| DATA_CONCLUSAO | `DATETIME` | Sim | |

**HISTORICO_STATUS_TROCA**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_TROCA | `INT UNSIGNED` | Não | FK para TROCA |
| FK_STATUS_TROCA | `TINYINT UNSIGNED` | Não | FK para STATUS_TROCA |
| DATA_EVENTO | `DATETIME` | Não | Padrão: data/hora atual |

**REEMBOLSO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_ITEM_VENDA | `INT UNSIGNED` | Não | FK para ITEM_VENDA |
| QNT | `SMALLINT UNSIGNED` | Não | Padrão 1 |
| MOTIVO | `VARCHAR(500)` | Não | |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |
| CONCLUSAO | `TINYINT(1)` | Não | Padrão 0 |
| DATA_CONCLUSAO | `DATETIME` | Sim | |

#### Avaliações

**AVALIACAO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_ITEM_VENDA | `INT UNSIGNED` | Não | FK para ITEM_VENDA (único) |
| NOTA | `TINYINT UNSIGNED` | Não | De 1 a 5 |
| COMENTARIO | `VARCHAR(1000)` | Sim | |
| DATA_CRIACAO | `DATETIME` | Não | Padrão: data/hora atual |

**IMGS_AVALIACAO**

| Coluna | Tipo | Nulo | Observação |
|---|---|---|---|
| ID | `INT UNSIGNED` | Não | PK, auto incremento |
| FK_AVALIACAO | `INT UNSIGNED` | Não | FK para AVALIACAO |
| URL_IMAGEM | `VARCHAR(255)` | Não | Caminho relativo na pasta do servidor |
| ATIVO | `TINYINT(1)` | Não | Padrão 1 |

---

## Anexo A — Tabela de frete

> Os valores abaixo são fictícios e servem apenas para a simulação da loja. Em produção, seriam substituídos pela API dos Correios ou de uma transportadora.

- **Origem da simulação:** São Paulo (SP). **Destino:** todo o Brasil (não há entrega para o exterior).
- A UF considerada é a do endereço de entrega escolhido no checkout (`ENDERECO_USUARIO.ESTADO`).
- A regra do frete grátis está na seção 11.2; esta tabela vale quando o frete não é grátis.
- O prazo (dias úteis) é informativo, exibido ao cliente; o banco não possui coluna de prazo.

| Região           | UF  | Frete (R$) | Prazo (dias úteis) |
| ---------------- | --- | ---------- | ------------------ |
| **Sudeste**      | SP  | 14,90      | 1–3                |
|                  | RJ  | 19,90      | 3–5                |
|                  | MG  | 21,90      | 3–5                |
|                  | ES  | 24,90      | 4–6                |
| **Sul**          | PR  | 22,90      | 3–5                |
|                  | SC  | 24,90      | 4–6                |
|                  | RS  | 27,90      | 4–7                |
| **Centro-Oeste** | DF  | 29,90      | 4–7                |
|                  | GO  | 29,90      | 4–7                |
|                  | MS  | 31,90      | 5–8                |
|                  | MT  | 34,90      | 5–9                |
| **Nordeste**     | BA  | 34,90      | 5–9                |
|                  | SE  | 36,90      | 6–10               |
|                  | AL  | 37,90      | 6–10               |
|                  | PE  | 37,90      | 6–10               |
|                  | PB  | 38,90      | 7–11               |
|                  | RN  | 39,90      | 7–11               |
|                  | CE  | 39,90      | 7–11               |
|                  | PI  | 41,90      | 8–12               |
|                  | MA  | 42,90      | 8–12               |
| **Norte**        | TO  | 38,90      | 6–10               |
|                  | PA  | 44,90      | 8–13               |
|                  | RO  | 47,90      | 9–14               |
|                  | AC  | 52,90      | 10–15              |
|                  | AM  | 54,90      | 10–15              |
|                  | AP  | 56,90      | 10–16              |
|                  | RR  | 59,90      | 11–17              |
