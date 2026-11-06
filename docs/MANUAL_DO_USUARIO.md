# Manual do Usuário — MadeInLace

Bem-vinda(o) à **MadeInLace**, loja virtual de roupas, calçados e corsets inspirada em estilos delicados e atemporais (*Balletcore*, *Dark Coquette*, *Romantic Vintage* e *Cottagecore Princess*).

Este manual prático foi elaborado para orientar você em todas as etapas de uso do site: desde a criação da conta até a finalização de compras, rastreamento de entregas, trocas e avaliações.

---

## Sumário

1. [Acesso e Contas de Usuário](#1-acesso-e-contas-de-usuário)
   - [Criando uma nova conta](#11-criando-uma-nova-conta)
   - [Fazendo login](#12-fazendo-login)
   - [Contas de teste prontas para uso](#13-contas-de-teste-prontas-para-uso)
   - [Recuperação de senha](#14-recuperação-de-senha)
2. [Navegação e Busca de Produtos](#2-navegação-e-busca-de-produtos)
   - [Página inicial (Home)](#21-página-inicial-home)
   - [Menu Explorar e Categorias](#22-menu-explorar-e-categorias)
   - [Barra de pesquisa](#23-barra-de-pesquisa)
   - [Filtros do Catálogo](#24-filtros-do-catálogo)
3. [Detalhes do Produto e Seleção de Medidas](#3-detalhes-do-produto-e-seleção-de-medidas)
   - [Visualização de fotos e detalhes](#31-visualização-de-fotos-e-detalhes)
   - [Escolha de tamanho e cor](#32-escolha-de-tamanho-e-cor)
   - [Guia de medidas](#33-guia-de-medidas)
4. [Sacola de Compras (Carrinho)](#4-sacola-de-compras-carrinho)
   - [Drawer lateral e página do carrinho](#41-drawer-lateral-e-página-do-carrinho)
   - [Alterar quantidades e remover itens](#42-alterar-quantidades-e-remover-itens)
   - [Cálculo de frete e regra de frete grátis](#43-cálculo-de-frete-e-regra-de-frete-grátis)
5. [Finalização da Compra (Checkout)](#5-finalização-da-compra-checkout)
   - [Endereço de entrega](#51-endereço-de-entrega)
   - [Desconto de 1ª compra (10% OFF)](#52-desconto-de-1ª-compra-10-off)
   - [Meios de pagamento simulados](#53-meios-de-pagamento-simulados)
6. [Área do Cliente (Meu Perfil)](#6-área-do-cliente-meu-perfil)
   - [Meus dados e meus endereços](#61-meus-dados-e-meus-endereços)
   - [Histórico e rastreamento de pedidos](#62-histórico-e-rastreamento-de-pedidos)
   - [Solicitação de troca ou reembolso](#63-solicitação-de-troca-ou-reembolso)
   - [Como avaliar um produto comprado](#64-como-avaliar-um-produto-comprado)
7. [Guia Rápido de Configuração do Banco de Dados](#7-guia-rápido-de-configuração-do-banco-de-dados)

---

## 1. Acesso e Contas de Usuário

### 1.1 Criando uma nova conta
1. Clique no ícone de perfil no canto superior direito do cabeçalho e selecione **"Cadastre-se"** (ou acesse diretamente `/auth/registro`).
2. Preencha seus dados pessoais:
   - **Nome e Sobrenome**
   - **CPF válido** (somente dígitos)
   - **E-mail pessoal**
   - **Telefone / WhatsApp** com DDD
   - **Data de nascimento** (é necessário ter no mínimo 18 anos)
3. Cadastre sua senha seguindo as regras de segurança:
   - Mínimo de 12 caracteres;
   - Ao menos 1 letra maiúscula, 1 minúscula, 1 número e 1 símbolo especial (`@`, `!`, `#`, `$`, etc.);
   - Não pode ser igual ao seu e-mail.
4. Cadastre o **endereço principal de entrega** (CEP, Rua, Número, Bairro, Cidade e UF).
5. Se a verificação em duas etapas estiver ativada, insira o código de verificação enviado ao seu e-mail.

### 1.2 Fazendo login
1. Acesse o menu de login no ícone de usuário ou acesse `/auth/login`.
2. Informe o **e-mail** e a **senha** cadastrados.
3. Clique em **"Entrar"**.

### 1.3 Contas de teste prontas para uso
Para facilitar testes ou demonstrações sem precisar cadastrar um novo usuário do zero, o banco de dados já possui contas prontas com dados fictícios:

| Perfil | E-mail | Senha de Teste | Observação |
|---|---|---|---|
| **Cliente (Mariana)** | `mariana.costa@example.com` | `Mariana@Lace2026!` | Possui pedidos finalizados, em trânsito e avaliações |
| **Cliente (Beatriz)** | `beatriz.almeida@example.com` | `Beatriz@Lace2026!` | Cliente com histórico de compras |
| **Cliente (Camila)** | `camila.ferreira@example.com` | `Camila@Lace2026!` | Cliente com pedidos entregues |
| **Administrador** | `admin@madeinlace.example.com` | `Admin@MadeInLace2026!` | Conta de gestão administrativa |

> **Dica**: Todas as contas de demonstração também respondem à senha mestra: `MadeInLace@2026!`

### 1.4 Recuperação de senha
Caso esqueça sua senha:
1. Na tela de login, clique no link **"Esqueci minha senha"**.
2. Digite seu e-mail cadastrado.
3. Siga o link com token de segurança enviado para redefinir a nova senha.

---

## 2. Navegação e Busca de Produtos

### 2.1 Página inicial (Home)
Na página principal você encontra:
- **Banner Carrossel**: novidades, coleções e promoções em destaque.
- **Coleções por Estilo**: atalhos visuais para as linhas *Balletcore*, *Dark Coquette*, *Romantic Vintage* e *Cottagecore Princess*.
- **Mais Vendidos e Novidades**: cards de produtos com acesso rápido.
- **Avaliações Reais**: depoimentos de clientes sobre peças recebidas.

### 2.2 Menu Explorar e Categorias
No cabeçalho do site:
- Passe o mouse ou clique em **"Explorar"** para abrir o menu dropdown.
- Você pode filtrar diretamente por:
  - **Categorias**: Roupas e Vestidos, Calçados ou Corsets.
  - **Linhas Estéticas**: Balletcore, Dark Coquette, Romantic Vintage, Cottagecore Princess.

### 2.3 Barra de pesquisa
- No topo da página, digite o nome da peça ou palavra-chave (exemplo: *"corset"*, *"vestido"*, *"salto"*, *"rosa"*).
- Pressione **Enter** ou clique na lupa para ver os resultados correspondentes.

### 2.4 Filtros do Catálogo
Na página `/catalogo`, você pode refinar os resultados por:
- **Tipo de Produto**: Roupas, Calçados ou Corsets.
- **Linha**: escolha sua estética favorita.
- **Ordenação**: menor preço, maior preço ou lançamentos.

---

## 3. Detalhes do Produto e Seleção de Medidas

### 3.1 Visualização de fotos e detalhes
Ao clicar no card de qualquer produto:
- Veja fotos em alta resolução da peça.
- Consulte a descrição de materiais, detalhes de renda, laços e caimento.
- Verifique o valor à vista e as opções de parcelamento simulado.

### 3.2 Escolha de tamanho e cor
1. Selecione a **Cor** desejada.
2. Selecione o **Tamanho**:
   - Roupas e Corsets: **P**, **M**, **G**, **GG**.
   - Calçados: numerações **36**, **37**, **38**, **39**.
3. O seletor avisa automaticamente se a variação estiver com estoque baixo ou esgotada.

### 3.3 Guia de medidas
- Ao lado da seleção de tamanhos, clique em **"Guia de Medidas"** para consultar as tabelas com medidas de busto, cintura, quadril e comprimento em centímetros.

---

## 4. Sacola de Compras (Carrinho)

### 4.1 Drawer lateral e página do carrinho
- Ao clicar em **"Adicionar à Sacola"**, uma gaveta (*drawer*) se abre à direita da tela mostrando o resumo imediato do seu carrinho.
- Você pode continuar comprando ou clicar em **"Ver Sacola Completa"** para acessar `/carrinho`.

### 4.2 Alterar quantidades e remover itens
- Use os botões **`+`** e **`-`** para alterar a quantidade de cada item. O estoque é reservado temporariamente durante a navegação.
- Clique no ícone de **lixeira** caso queira remover o item da sacola.

### 4.3 Cálculo de frete e regra de frete grátis
- No campo **"Calcular Frete"**, digite seu CEP de 8 dígitos.
- **Regra de Frete Grátis**:
  - Para pedidos com subtotal de produtos a partir de **R$ 160,00**, o frete é **100% GRATUITO** para todo o Brasil.
  - Abaixo de R$ 160,00, o valor fixo é calculado de acordo com o estado de destino (ex.: SP = R$ 14,90, MG = R$ 21,90, PR = R$ 22,90).

---

## 5. Finalização da Compra (Checkout)

Ao clicar em **"Finalizar Compra"** no carrinho:

### 5.1 Endereço de entrega
- Selecione um endereço já cadastrado na sua conta ou adicione um novo endereço para esta entrega.

### 5.2 Desconto de 1ª compra (10% OFF)
- Na primeira compra de cada cliente, o sistema aplica automaticamente **10% de desconto sobre o subtotal dos produtos**!
- O resumo de valores exibe claramente: *Subtotal*, *Desconto de 1ª Compra (se aplicável)*, *Frete* e *Total Final*.

### 5.3 Meios de pagamento simulados
A MadeInLace opera com simulação de pagamentos:
1. **Pix**:
   - Gera na hora a chave / código simulado para "Copia e Cola" e QR Code.
   - Confirmação imediata do pedido.
2. **Cartão de Crédito**:
   - Permite preencher dados simulados do titular, número do cartão, validade e CVV.
   - Permite escolher o número de parcelas (até 6x sem juros).
3. **Boleto Bancário**:
   - Emite linha digitável com prazo simulado para pagamento.

Após confirmar o pagamento, seu pedido é gerado com um código exclusivo e passa para a etapa de separação.

---

## 6. Área do Cliente (Meu Perfil)

Acesse seu perfil a qualquer momento clicando no seu nome no cabeçalho ou acessando `/perfil`.

### 6.1 Meus dados e meus endereços
- **Dados Pessoais**: visualize seu nome, CPF, e-mail e telefone cadastrados.
- **Endereços Cadastrados**: cadastre múltiplos endereços (ex.: "Casa", "Trabalho") e selecione o endereço padrão.

### 6.2 Histórico e rastreamento de pedidos
Na aba **"Meus Pedidos"**, visualize todas as suas compras com:
- Data da compra, número do pedido e total pago;
- Lista de produtos adquiridos;
- Barra de rastreamento com as 5 etapas da entrega simulada:
  1. 📦 **Pedido em processamento**
  2. 🚚 **Pedido entregue à transportadora**
  3. 🛣️ **Pedido em trânsito**
  4. 🛵 **Saiu para entrega**
  5. ✅ **Pedido entregue**

### 6.3 Solicitação de troca ou reembolso
Para produtos com entrega já concluída:
- **Solicitar Troca**:
  1. Clique em **"Trocar"** no item do pedido.
  2. Escolha o novo tamanho ou cor desejada.
  3. Informe o motivo da troca.
  4. Acompanhe o status da troca diretamente no painel.
- **Solicitar Reembolso / Devolução**:
  1. Clique em **"Devolver / Reembolso"**.
  2. Digite a justificativa.
  3. O chamado é registrado para atendimento.

### 6.4 Como avaliar um produto comprado
Após a entrega de uma compra:
1. No pedido entregue, clique em **"Avaliar Produto"**.
2. Escolha a nota de **1 a 5 estrelas**.
3. Escreva seus comentários sobre a qualidade da peça, caimento e tecido.
4. Anexe fotos reais da peça (opcional).
5. Sua avaliação ficará visível publicamente na página do produto para ajudar outras clientes!

---

## 7. Guia Rápido de Configuração do Banco de Dados

Caso precise recriar o banco de dados em outro ambiente ou máquina de testes:

1. **Arquivo único completo**:
   - O arquivo `db/setup_completo_com_seed.sql` contém a criação de todas as tabelas e o seed completo com os dados fictícios prontos.
2. **Execução pelo terminal MySQL**:
   ```bash
   mysql -u root -p < db/setup_completo_com_seed.sql
   ```
3. **Execução pelo MySQL Workbench ou DBeaver**:
   - Abra o arquivo `db/setup_completo_com_seed.sql`.
   - Clique em **Execute / Run Script (Ctrl+Shift+Enter)**.
   - O banco `MADEINLACE` será criado com todas as tabelas, produtos, variações, clientes e pedidos de exemplo.

---

*MadeInLace — Elegância, delicadeza e encanto em cada detalhe.*
