-- =====================================================================
--  MADEINLACE - Dados de exemplo para a demonstração (MySQL 8.0.16+)
--  Rode DEPOIS do script de criação do banco (script_sql.md), num banco recém-criado.
--  Conteúdo: 2 fornecedores, 4 linhas, 10 produtos (vestidos, sapatos e corsets) com
--  variações e imagens, 6 clientes + 1 admin, 10 vendas e 10 avaliações com 1 imagem cada.
--
--  ATENÇÃO:
--   * Todos os dados são FICTÍCIOS (e-mails @example.com, CPFs/CNPJs só passam na
--     validação de dígitos, endereços inventados).
--   * Usa IDs explícitos: pensado para tabelas vazias (exceto as de domínio da seção 10
--     do script de criação, que precisam estar preenchidas).
--   * Tudo roda dentro de UMA transação: se algum INSERT falhar, use ROLLBACK;
--     (no cliente de linha de comando, rode com --abort-on-error).
--   * Execute o script inteiro na mesma sessão, porque ele usa variáveis (@...).
-- =====================================================================

USE MADEINLACE;

-- Hash de senha dos usuários de demonstração gerados com Argon2id (RFC 9106, biblioteca cryptography)
-- Regras de negócio MadeInLace (Seção 2.3): mín. 12 caracteres, maiúscula, minúscula, número e símbolo, != e-mail.
-- Senhas originais em texto claro:
--   Admin (ID 1):     Admin@MadeInLace2026!
--   Mariana (ID 2):   Mariana@Lace2026!
--   Beatriz (ID 3):   Beatriz@Lace2026!
--   Camila (ID 4):    Camila@Lace2026!
--   Juliana (ID 5):   Juliana@Lace2026!
--   Larissa (ID 6):   Larissa@Lace2026!
--   Fernanda (ID 7):  Fernanda@Lace2026!
--   Mestra/Demo:      MadeInLace@2026!
SET @SENHA_ADMIN    = '$argon2id$v=19$m=65536,t=3,p=4$9g4YM5lI3bG4VUx3FTt7pg$XMlHB3sBRctJ8AYsz4dgUi+WFvWpbouFZKbElucYV2I';
SET @SENHA_MARIANA  = '$argon2id$v=19$m=65536,t=3,p=4$pRBORo4P2dTDPQcyka71bQ$r/zQy1yPq0jFdkPHaKkxYAAua0FxW1u9/FECXK8Dyyk';
SET @SENHA_BEATRIZ  = '$argon2id$v=19$m=65536,t=3,p=4$4jzvv8DWSN79aNkGc/qXQQ$0R1KXaMNuNjrlaBsM1EP0euyOsa/LtrUZYAPjiInpZg';
SET @SENHA_CAMILA   = '$argon2id$v=19$m=65536,t=3,p=4$nAtsZhK7m5OZiL+emZYN+A$d26cgzN6WQ27JuOot5LQXQMnM78B31Vjj9B5Dt/aJVE';
SET @SENHA_JULIANA  = '$argon2id$v=19$m=65536,t=3,p=4$5LyxPv/OpSfcX1eXKSv+mw$93zqiZzmuh51Xq0qZmZvB3NOmJSFzoe9zqTF7xKRMlk';
SET @SENHA_LARISSA  = '$argon2id$v=19$m=65536,t=3,p=4$OnEr5/zZGbdjfUskcm6IKQ$o2JJ6uthltQqBa71dz1DUX3IUIW9TWZpfB1QNl7Ojy0';
SET @SENHA_FERNANDA = '$argon2id$v=19$m=65536,t=3,p=4$gsTFMvFbOfgsD8UJaQkBUA$WskTGXiTvsKN3ZYaxZF3NMiVtZuCN5QVTz+W98U4TmM';
SET @SENHA_DEMO     = '$argon2id$v=19$m=65536,t=3,p=4$PZUKPjZnTgnCbU/l/tCMyQ$7mTeJiI8GzMeZwGfjsj3AXSNbghd5vSc8jsxmFqsi6U';

-- IDs das tabelas de domínio, buscados pelo nome (não dependem da ordem de inserção).
SET @PAG_PIX     = (SELECT ID FROM METODO_PAGAMENTO WHERE METODO = 'Pix');
SET @PAG_CREDITO = (SELECT ID FROM METODO_PAGAMENTO WHERE METODO = 'Cartão de crédito' OR METODO LIKE '%cr%dito%');
SET @PAG_DEBITO  = (SELECT ID FROM METODO_PAGAMENTO WHERE METODO = 'Cartão de débito' OR METODO LIKE '%d%bito%');
SET @ST_PROCESSAMENTO   = (SELECT ID FROM STATUS_VENDA WHERE ESTADO_ANDAMENTO = 'EM_PROCESSAMENTO');
SET @ST_TRANSPORTADORA  = (SELECT ID FROM STATUS_VENDA WHERE ESTADO_ANDAMENTO = 'NA_TRANSPORTADORA');
SET @ST_TRANSITO        = (SELECT ID FROM STATUS_VENDA WHERE ESTADO_ANDAMENTO = 'EM_TRANSITO');
SET @ST_ENTREGANDO      = (SELECT ID FROM STATUS_VENDA WHERE ESTADO_ANDAMENTO = 'ENTREGANDO');
SET @ST_ENTREGUE        = (SELECT ID FROM STATUS_VENDA WHERE ESTADO_ANDAMENTO = 'ENTREGUE');

START TRANSACTION;

-- ---------------------------------------------------------------------
--  1. LINHAS
-- ---------------------------------------------------------------------
INSERT INTO LINHA (ID, NOME) VALUES
    (1, 'Balletcore'),
    (2, 'Dark Coquette'),
    (3, 'Romantic Vintage'),
    (4, 'Cottagecore Princess');

-- ---------------------------------------------------------------------
--  2. FORNECEDORES (com e-mail, telefone e endereço)
-- ---------------------------------------------------------------------
INSERT INTO FORNECEDORES (ID, NOME, CNPJ, RAZAO_SOCIAL, ATIVO) VALUES
    (1, 'Atelier Rosa Velha', '11222333000181', 'Atelier Rosa Velha Confecções Ltda', 1),
    (2, 'Casa Sapateira Lume', '44555666000181', 'Lume Calçados e Acessórios Ltda', 1);

INSERT INTO EMAILS_FORNECEDOR (FK_FORNECEDOR, EMAIL, ATIVO) VALUES
    (1, 'contato@rosavelha.example.com', 1),
    (2, 'vendas@casalume.example.com', 1);

INSERT INTO TELEFONE_FORNECEDOR (FK_FORNECEDOR, DDD, TELEFONE, ATIVO) VALUES
    (1, '11', '32100001', 1),
    (2, '19', '34500002', 1);

INSERT INTO ENDERECO_FORNECEDOR (FK_FORNECEDOR, CEP, LOGRADOURO, NUMERO, COMPLEMENTO, BAIRRO, CIDADE, ESTADO, ATIVO) VALUES
    (1, '01001000', 'Rua das Camélias', '120', 'Sala 3', 'Centro', 'São Paulo', 'SP', 1),
    (2, '13010000', 'Avenida dos Ipês', '845', NULL, 'Vila Industrial', 'Campinas', 'SP', 1);

-- ---------------------------------------------------------------------
--  3. PRODUTOS
-- ---------------------------------------------------------------------
INSERT INTO PRODUTOS (ID, FK_FORNECEDOR, FK_LINHA, NOME, DESCRICAO, TIPO, ATIVO, DATA_CRIACAO) VALUES
    (1, 2, 1, 'Balletcore Heels', 'Sapato de salto com acabamento em cetim rosa claro, laços delicados e tiras no tornozelo. Inspirado no universo balletcore, combina com looks românticos e vestidos fluidos.', 'calcado', 1, '2026-08-25 10:00:00'),
    (2, 2, 2, 'Dark Coquette Shoes', 'Sapato preto estilo boneca com bordado em fio claro e laço no peito do pé. Fica lindo com meias brancas e saias rodadas.', 'calcado', 1, '2026-08-25 10:00:00'),
    (3, 1, 2, 'Flower & Mirror Corset', 'Corset em jacquard floral em tons escuros, com decote coração e fechamento frontal. Peça de destaque para compor com saias longas e mangas bufantes.', 'corset', 1, '2026-08-25 10:00:00'),
    (4, 1, 2, 'Midday Phantom Dress', 'Vestido midi preto de inspiração corset, com detalhe em renda no busto, alças finas e fenda frontal na saia. Elegante e versátil para eventos.', 'roupa', 1, '2026-08-25 10:00:00'),
    (5, 1, 3, 'Morning Dew Corset', 'Corset branco com babados nos ombros, laço frontal e acabamento em renda. Pode ser usado ombro a ombro, com cardigan ou com saias de tule.', 'corset', 1, '2026-08-25 10:00:00'),
    (6, 1, 3, 'Pink Butterfly Dress', 'Vestido midi em cetim rosa com bustiê de renda e alças finas. Caimento fluido e brilho suave, ideal para festas e ensaios fotográficos.', 'roupa', 1, '2026-08-25 10:00:00'),
    (7, 1, 4, 'Princess Ashley Corset', 'Corset verde sálvia com bordas de renda, laços delicados e fechamento por cordões nas costas, que permite ajustar a cintura. Combina com saias de cetim ou tule.', 'corset', 1, '2026-08-25 10:00:00'),
    (8, 2, 3, 'Satin Mary Jane Heels', 'Sapato Mary Jane de cetim branco com salto bloco, laços volumosos, fios de pérolas e detalhes em renda. Perfeito para noivas, madrinhas e looks de gala.', 'calcado', 1, '2026-08-25 10:00:00'),
    (9, 1, 2, 'Shaking the Wine Dress', 'Vestido longo preto com bustiê em vinho e preto e decote coração, modelagem ajustada ao corpo. Sofisticado e marcante.', 'roupa', 1, '2026-08-25 10:00:00'),
    (10, 1, 4, 'Summer Wind Corset', 'Conjunto em azul claro com mangas bufantes, bustiê em renda creme e laço frontal. Leve e romântico, perfeito para o verão.', 'corset', 1, '2026-08-25 10:00:00');

-- Imagens dos produtos: só o CAMINHO relativo (pasta img/produtos/ dentro de static/).
-- A primeira imagem de cada produto (menor ID) é a principal.
INSERT INTO IMGS_PRODUTOS (FK_PRODUTO, URL_IMAGEM, ATIVO) VALUES
    (1, 'img/produtos/balletcore-heels-1.png', 1),
    (2, 'img/produtos/dark-coquette-shoes-1.png', 1),
    (3, 'img/produtos/flower-mirror-corset-1.png', 1),
    (4, 'img/produtos/midday-phantom-dress-1.png', 1),
    (5, 'img/produtos/morning-dew-corset-1.png', 1),
    (5, 'img/produtos/morning-dew-corset-2.png', 1),
    (6, 'img/produtos/pink-butterfly-dress-1.png', 1),
    (7, 'img/produtos/princess-ashley-corset-1.png', 1),
    (7, 'img/produtos/princess-ashley-corset-2.png', 1),
    (8, 'img/produtos/satin-mary-jane-heels-1.png', 1),
    (9, 'img/produtos/shaking-the-wine-dress-1.png', 1),
    (10, 'img/produtos/summer-wind-corset-1.png', 1);

-- ---------------------------------------------------------------------
--  4. VARIAÇÕES (tamanho/cor/estoque/preço). Pink Butterfly G está esgotado de propósito.
--  Dark Coquette Shoes (R$ 174,90 com 10% de promoção = R$ 157,41) e Flower & Mirror Corset
--  (R$ 149,90) ficam abaixo de R$ 160,00 para demonstrar a cobrança de frete.
-- ---------------------------------------------------------------------
INSERT INTO VARIACAO (ID, FK_PRODUTO, TAMANHO, COR, ESTOQUE, CUSTO, PRECO, PORCENTAGEM_PROMOCAO, ATIVO) VALUES
    (1, 1, '36', 'Rosa claro', 5, 148.00, 329.90, 0.00, 1),
    (2, 1, '37', 'Rosa claro', 9, 148.00, 329.90, 0.00, 1),
    (3, 1, '38', 'Rosa claro', 9, 148.00, 329.90, 0.00, 1),
    (4, 1, '39', 'Rosa claro', 4, 148.00, 329.90, 0.00, 1),
    (5, 2, '36', 'Preto', 5, 80.00, 174.90, 10.00, 1),
    (6, 2, '37', 'Preto', 9, 80.00, 174.90, 10.00, 1),
    (7, 2, '38', 'Preto', 9, 80.00, 174.90, 10.00, 1),
    (8, 2, '39', 'Preto', 4, 80.00, 174.90, 10.00, 1),
    (9, 3, 'P', 'Floral escuro', 8, 65.00, 149.90, 0.00, 1),
    (10, 3, 'M', 'Floral escuro', 12, 65.00, 149.90, 0.00, 1),
    (11, 3, 'G', 'Floral escuro', 6, 65.00, 149.90, 0.00, 1),
    (12, 4, 'P', 'Preto', 8, 165.00, 389.90, 15.00, 1),
    (13, 4, 'M', 'Preto', 12, 165.00, 389.90, 15.00, 1),
    (14, 4, 'G', 'Preto', 6, 165.00, 389.90, 15.00, 1),
    (15, 5, 'P', 'Branco', 8, 128.00, 299.90, 0.00, 1),
    (16, 5, 'M', 'Branco', 12, 128.00, 299.90, 0.00, 1),
    (17, 5, 'G', 'Branco', 6, 128.00, 299.90, 0.00, 1),
    (18, 6, 'P', 'Rosa', 8, 180.00, 419.90, 20.00, 1),
    (19, 6, 'M', 'Rosa', 12, 180.00, 419.90, 20.00, 1),
    (20, 6, 'G', 'Rosa', 0, 180.00, 419.90, 20.00, 1),
    (21, 7, 'P', 'Verde sálvia', 8, 150.00, 349.90, 0.00, 1),
    (22, 7, 'M', 'Verde sálvia', 12, 150.00, 349.90, 0.00, 1),
    (23, 7, 'G', 'Verde sálvia', 6, 150.00, 349.90, 0.00, 1),
    (24, 8, '36', 'Branco', 5, 160.00, 369.90, 0.00, 1),
    (25, 8, '37', 'Branco', 9, 160.00, 369.90, 0.00, 1),
    (26, 8, '38', 'Branco', 9, 160.00, 369.90, 0.00, 1),
    (27, 8, '39', 'Branco', 4, 160.00, 369.90, 0.00, 1),
    (28, 9, 'P', 'Preto e vinho', 8, 195.00, 459.90, 10.00, 1),
    (29, 9, 'M', 'Preto e vinho', 12, 195.00, 459.90, 10.00, 1),
    (30, 9, 'G', 'Preto e vinho', 6, 195.00, 459.90, 10.00, 1),
    (31, 10, 'P', 'Azul claro', 8, 135.00, 319.90, 0.00, 1),
    (32, 10, 'M', 'Azul claro', 12, 135.00, 319.90, 0.00, 1),
    (33, 10, 'G', 'Azul claro', 6, 135.00, 319.90, 0.00, 1);

-- ---------------------------------------------------------------------
--  5. USUÁRIOS (1 admin + 6 clientes) e endereços
-- ---------------------------------------------------------------------
INSERT INTO USUARIOS (ID, NOME, SOBRENOME, EMAIL, SENHA_HASH, NASCIMENTO, CPF, TELEFONE, ATIVO, IS_ADM, DATA_CRIACAO) VALUES
    (1, 'Admin', 'Loja', 'admin@madeinlace.example.com', @SENHA_ADMIN, NULL, NULL, NULL, 1, 1, '2026-08-20 09:00:00'),
    (2, 'Mariana', 'Costa', 'mariana.costa@example.com', @SENHA_MARIANA, '1992-03-14', '12345678909', '11999990002', 1, 0, '2026-09-01 14:20:00'),
    (3, 'Beatriz', 'Almeida', 'beatriz.almeida@example.com', @SENHA_BEATRIZ, '1998-07-02', '23456789173', '19999990003', 1, 0, '2026-09-03 10:05:00'),
    (4, 'Camila', 'Ferreira', 'camila.ferreira@example.com', @SENHA_CAMILA, '1995-11-23', '34567891228', '15999990004', 1, 0, '2026-09-05 18:40:00'),
    (5, 'Juliana', 'Souza', 'juliana.souza@example.com', @SENHA_JULIANA, '2000-01-30', '45678912364', '13999990005', 1, 0, '2026-09-08 21:15:00'),
    (6, 'Larissa', 'Martins', 'larissa.martins@example.com', @SENHA_LARISSA, '1990-09-09', '56789123482', '14999990006', 1, 0, '2026-09-10 08:50:00'),
    (7, 'Fernanda', 'Lima', 'fernanda.lima@example.com', @SENHA_FERNANDA, '1996-05-18', '52998224725', '19999990007', 1, 0, '2026-10-10 12:00:00');

INSERT INTO ENDERECO_USUARIO (FK_USUARIO, NOME, CEP, LOGRADOURO, NUMERO, COMPLEMENTO, BAIRRO, CIDADE, ESTADO, ATIVO) VALUES
    (2, 'Casa', '01311000', 'Rua das Acácias', '45', 'Apto 12', 'Bela Vista', 'São Paulo', 'SP', 1),
    (3, 'Casa', '30130000', 'Rua das Hortênsias', '300', NULL, 'Centro', 'Belo Horizonte', 'MG', 1),
    (4, 'Casa', '18035000', 'Avenida das Palmeiras', '1020', 'Bloco B', 'Jardim Europa', 'Sorocaba', 'SP', 1),
    (5, 'Trabalho', '40020000', 'Rua dos Girassóis', '77', 'Sala 5', 'Comércio', 'Salvador', 'BA', 1),
    (6, 'Casa', '17010000', 'Rua das Orquídeas', '560', NULL, 'Vila Cardia', 'Bauru', 'SP', 1),
    (7, 'Casa', '80010000', 'Rua das Violetas', '210', 'Apto 4', 'Centro', 'Curitiba', 'PR', 1);

-- ---------------------------------------------------------------------
--  6. COMPRAS: carrinho -> venda -> histórico de status -> itens
--  Regras usadas nos exemplos:
--   * 10% de desconto SÓ na 1ª compra de cada cliente (venda mais antiga do usuário,
--     DESCONTO = 1); da 2ª compra em diante DESCONTO = 0 (usuários 2, 3 e 4 têm mais de uma venda);
--   * frete grátis a partir de R$ 160,00 de subtotal (soma dos itens já com promoção, antes do
--     desconto de 10%); abaixo disso, o frete é o valor fixo da UF do endereço usado na compra
--     (tabela-frete-madeinlace.md). Vendas com frete: 6 (SP, R$ 14,90), 8 (PR, R$ 22,90) e
--     9 (MG, R$ 21,90), todas com subtotal entre R$ 149,90 e R$ 157,41.
--  Carrinhos já convertidos em venda ficam como CONVERTIDO (sem ITEM_CARRINHO).
-- ---------------------------------------------------------------------
INSERT INTO CARRINHO (ID, FK_USUARIO, STATUS, TOTAL, FRETE_GRATIS, DATA_CRIACAO) VALUES
    (1, 2, 'CONVERTIDO', 669.80, 1, '2026-09-14 10:07:00'),
    (2, 3, 'CONVERTIDO', 685.82, 1, '2026-09-18 14:45:00'),
    (3, 4, 'CONVERTIDO', 457.31, 1, '2026-09-21 20:20:00'),
    (4, 5, 'CONVERTIDO', 667.34, 1, '2026-09-25 08:40:00'),
    (5, 6, 'CONVERTIDO', 999.70, 1, '2026-09-28 19:05:00'),
    (6, 2, 'CONVERTIDO', 149.90, 0, '2026-11-01 10:35:00'),
    (7, 4, 'CONVERTIDO', 413.91, 1, '2026-11-05 08:50:00'),
    (8, 7, 'CONVERTIDO', 157.41, 0, '2026-10-12 13:55:00'),
    (9, 3, 'CONVERTIDO', 149.90, 0, '2026-10-20 16:15:00'),
    (10, 2, 'CONVERTIDO', 307.31, 1, '2026-11-04 17:55:00');

INSERT INTO VENDA (ID, FK_CARRINHO, FK_USUARIO, FK_ENDERECO_USUARIO, FK_METODO_PAGAMENTO, FK_STATUS, SUBTOTAL, FRETE, DESCONTO, TOTAL, FRETE_GRATIS, `DATA`) VALUES
    (1, 1, 2, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 2 AND ATIVO = 1 LIMIT 1), @PAG_PIX, @ST_ENTREGUE, 669.80, 0.00, 1, 602.82, 1, '2026-09-14 10:32:00'),
    (2, 2, 3, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 3 AND ATIVO = 1 LIMIT 1), @PAG_CREDITO, @ST_ENTREGUE, 685.82, 0.00, 1, 617.24, 1, '2026-09-18 15:10:00'),
    (3, 3, 4, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 4 AND ATIVO = 1 LIMIT 1), @PAG_PIX, @ST_ENTREGUE, 457.31, 0.00, 1, 411.58, 1, '2026-09-21 20:45:00'),
    (4, 4, 5, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 5 AND ATIVO = 1 LIMIT 1), @PAG_CREDITO, @ST_ENTREGUE, 667.34, 0.00, 1, 600.61, 1, '2026-09-25 09:05:00'),
    (5, 5, 6, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 6 AND ATIVO = 1 LIMIT 1), @PAG_CREDITO, @ST_ENTREGUE, 999.70, 0.00, 1, 899.73, 1, '2026-09-28 19:30:00'),
    (6, 6, 2, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 2 AND ATIVO = 1 LIMIT 1), @PAG_PIX, @ST_TRANSITO, 149.90, 14.90, 0, 164.80, 0, '2026-11-01 11:00:00'),
    (7, 7, 4, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 4 AND ATIVO = 1 LIMIT 1), @PAG_DEBITO, @ST_PROCESSAMENTO, 413.91, 0.00, 0, 413.91, 1, '2026-11-05 09:15:00'),
    (8, 8, 7, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 7 AND ATIVO = 1 LIMIT 1), @PAG_PIX, @ST_ENTREGUE, 157.41, 22.90, 1, 164.57, 0, '2026-10-12 14:20:00'),
    (9, 9, 3, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 3 AND ATIVO = 1 LIMIT 1), @PAG_DEBITO, @ST_ENTREGUE, 149.90, 21.90, 0, 171.80, 0, '2026-10-20 16:40:00'),
    (10, 10, 2, (SELECT ID FROM ENDERECO_USUARIO WHERE FK_USUARIO = 2 AND ATIVO = 1 LIMIT 1), @PAG_CREDITO, @ST_TRANSPORTADORA, 307.31, 0.00, 0, 307.31, 1, '2026-11-04 18:20:00');

INSERT INTO HISTORICO_STATUS_VENDA (FK_VENDA, FK_STATUS_VENDA, DATA_EVENTO) VALUES
    (1, @ST_PROCESSAMENTO, '2026-09-14 10:32:00'),
    (1, @ST_TRANSPORTADORA, '2026-09-15 13:32:00'),
    (1, @ST_TRANSITO, '2026-09-16 16:32:00'),
    (1, @ST_ENTREGANDO, '2026-09-19 12:32:00'),
    (1, @ST_ENTREGUE, '2026-09-20 14:32:00'),
    (2, @ST_PROCESSAMENTO, '2026-09-18 15:10:00'),
    (2, @ST_TRANSPORTADORA, '2026-09-19 18:10:00'),
    (2, @ST_TRANSITO, '2026-09-20 21:10:00'),
    (2, @ST_ENTREGANDO, '2026-09-23 17:10:00'),
    (2, @ST_ENTREGUE, '2026-09-24 19:10:00'),
    (3, @ST_PROCESSAMENTO, '2026-09-21 20:45:00'),
    (3, @ST_TRANSPORTADORA, '2026-09-22 23:45:00'),
    (3, @ST_TRANSITO, '2026-09-24 02:45:00'),
    (3, @ST_ENTREGANDO, '2026-09-26 22:45:00'),
    (3, @ST_ENTREGUE, '2026-09-28 00:45:00'),
    (4, @ST_PROCESSAMENTO, '2026-09-25 09:05:00'),
    (4, @ST_TRANSPORTADORA, '2026-09-26 12:05:00'),
    (4, @ST_TRANSITO, '2026-09-27 15:05:00'),
    (4, @ST_ENTREGANDO, '2026-09-30 11:05:00'),
    (4, @ST_ENTREGUE, '2026-10-01 13:05:00'),
    (5, @ST_PROCESSAMENTO, '2026-09-28 19:30:00'),
    (5, @ST_TRANSPORTADORA, '2026-09-29 22:30:00'),
    (5, @ST_TRANSITO, '2026-10-01 01:30:00'),
    (5, @ST_ENTREGANDO, '2026-10-03 21:30:00'),
    (5, @ST_ENTREGUE, '2026-10-04 23:30:00'),
    (6, @ST_PROCESSAMENTO, '2026-11-01 11:00:00'),
    (6, @ST_TRANSPORTADORA, '2026-11-02 14:00:00'),
    (6, @ST_TRANSITO, '2026-11-03 17:00:00'),
    (7, @ST_PROCESSAMENTO, '2026-11-05 09:15:00'),
    (8, @ST_PROCESSAMENTO, '2026-10-12 14:20:00'),
    (8, @ST_TRANSPORTADORA, '2026-10-13 17:20:00'),
    (8, @ST_TRANSITO, '2026-10-14 20:20:00'),
    (8, @ST_ENTREGANDO, '2026-10-17 16:20:00'),
    (8, @ST_ENTREGUE, '2026-10-18 18:20:00'),
    (9, @ST_PROCESSAMENTO, '2026-10-20 16:40:00'),
    (9, @ST_TRANSPORTADORA, '2026-10-21 19:40:00'),
    (9, @ST_TRANSITO, '2026-10-22 22:40:00'),
    (9, @ST_ENTREGANDO, '2026-10-25 18:40:00'),
    (9, @ST_ENTREGUE, '2026-10-26 20:40:00'),
    (10, @ST_PROCESSAMENTO, '2026-11-04 18:20:00'),
    (10, @ST_TRANSPORTADORA, '2026-11-05 08:20:00');

-- PRECO_UNITARIO já com a promoção, congelado no momento da compra.
INSERT INTO ITEM_VENDA (ID, FK_VENDA, FK_VARIACAO, QNT, PRECO_UNITARIO) VALUES
    (1, 1, 16, 1, 299.90),
    (2, 1, 25, 1, 369.90),
    (3, 2, 21, 1, 349.90),
    (4, 2, 19, 1, 335.92),
    (5, 3, 15, 1, 299.90),
    (6, 3, 5, 1, 157.41),
    (7, 4, 18, 1, 335.92),
    (8, 4, 13, 1, 331.42),
    (9, 5, 22, 1, 349.90),
    (10, 5, 32, 1, 319.90),
    (11, 5, 2, 1, 329.90),
    (12, 6, 10, 1, 149.90),
    (13, 7, 28, 1, 413.91),
    (14, 8, 6, 1, 157.41),
    (15, 9, 9, 1, 149.90),
    (16, 10, 7, 1, 157.41),
    (17, 10, 11, 1, 149.90);

-- ---------------------------------------------------------------------
--  7. AVALIAÇÕES (só de itens de vendas ENTREGUE) e imagem de cada avaliação
--  As imagens de avaliação são PLACEHOLDERS (cópias de fotos de produto) em img/avaliacoes/.
-- ---------------------------------------------------------------------
INSERT INTO AVALIACAO (ID, FK_ITEM_VENDA, NOTA, COMENTARIO, DATA_CRIACAO) VALUES
    (1, 1, 5, 'Lindo demais! O corset é ainda mais delicado pessoalmente: a renda e o laço são muito bem acabados. Fechou certinho no tamanho M e o tecido não é áspero. Chegou antes do prazo.', '2026-09-23 16:32:00'),
    (2, 2, 5, 'Parece sapato de conto de fadas. As pérolas e os laços são firmes e o salto bloco é confortável para ficar horas em pé. Usei em um casamento e recebi muitos elogios.', '2026-09-23 17:32:00'),
    (3, 3, 5, 'A cor verde sálvia é perfeita e o caimento valoriza muito a cintura. Os cordões das costas ajustam bem. Super recomendo!', '2026-09-28 23:10:00'),
    (4, 4, 4, 'O cetim é lindo e tem um brilho elegante, mas amassa com facilidade. Vale passar a vapor antes de usar. O comprimento ficou perfeito em mim.', '2026-09-29 00:10:00'),
    (5, 5, 4, 'Muito bonito e delicado. Fiquei em dúvida entre P e M e o P ficou justo no busto; se estiver entre dois tamanhos, vá de M. Fora isso, acabamento impecável.', '2026-09-30 01:45:00'),
    (6, 6, 4, 'Combina demais com meia branca e o bordado é lindo. O bico é um pouco estreito e apertou no começo, mas amaciou depois de alguns usos.', '2026-09-30 02:45:00'),
    (7, 7, 5, 'Amei! Usei no aniversário de uma amiga e todo mundo perguntou onde comprei. O tecido é pesado e cai muito bem.', '2026-10-06 16:05:00'),
    (8, 9, 4, 'Peça linda, os detalhes em renda são caprichados. Demorou um pouquinho para chegar, mas o atendimento avisou o tempo todo. Compraria de novo.', '2026-10-08 03:30:00'),
    (9, 10, 5, 'Perfeito para fotos de verão! O azul é suave, as mangas bufantes são fofas e o tecido é leve.', '2026-10-08 04:30:00'),
    (10, 11, 3, 'O sapato é lindíssimo e os laços são caprichados, mas o salto é mais alto do que imaginei pela foto e a numeração veio um pouco pequena. Recomendo pedir um número acima.', '2026-10-09 00:30:00');

INSERT INTO IMGS_AVALIACAO (FK_AVALIACAO, URL_IMAGEM, ATIVO) VALUES
    (1, 'img/avaliacoes/avaliacao_01.png', 1),
    (2, 'img/avaliacoes/avaliacao_02.png', 1),
    (3, 'img/avaliacoes/avaliacao_03.png', 1),
    (4, 'img/avaliacoes/avaliacao_04.png', 1),
    (5, 'img/avaliacoes/avaliacao_05.png', 1),
    (6, 'img/avaliacoes/avaliacao_06.png', 1),
    (7, 'img/avaliacoes/avaliacao_07.png', 1),
    (8, 'img/avaliacoes/avaliacao_08.png', 1),
    (9, 'img/avaliacoes/avaliacao_09.png', 1),
    (10, 'img/avaliacoes/avaliacao_10.png', 1);

COMMIT;
