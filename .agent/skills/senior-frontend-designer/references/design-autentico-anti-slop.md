# Design autêntico (anti-slop)

"Slop" é o visual genérico, previsível e sem intenção que sai quando ninguém decidiu nada: gradiente roxo-azul em tudo, cards idênticos com sombra, emojis no lugar de ícones, texto de preenchimento e fontes padrão. Seu trabalho é entregar interfaces com **ponto de vista**, reconhecíveis e fiéis à marca/imagem de referência.

Sumário: 1. Princípio · 2. Sinais de slop · 3. Como evitar · 4. Fidelidade vs. originalidade · 5. Direções estéticas · 6. Texto e conteúdo · 7. Teste anti-slop

## 1. Princípio

Toda escolha visual precisa ter um **porquê** (marca, público, função, referência). Se a resposta é "porque é o padrão", é slop. Antes de codar, formule em uma frase a direção: *"Editorial, quente, tipografia serifada grande, bordas finas, muito respiro"* ou *"Denso, técnico, mono, alto contraste, sem decoração"*.

Quando há imagem de referência, **a direção vem dela**; não "melhore" o design trocando a identidade por um template genérico. Originalidade se aplica ao que a imagem não define (estados, mobile, microinterações, detalhes).

## 2. Sinais de slop (evite)

- Gradiente roxo→azul/rosa em fundo, botão e título por padrão; "glow" e blur decorativos sem função.
- Mesma fonte genérica em tudo (system-ui sem decisão) ou Inter/Roboto/Arial por inércia quando o design pede outra personalidade.
- Grade de 3 cards idênticos com ícone em círculo, título e duas linhas; repetida em toda seção.
- Hero centralizado com título enorme + subtítulo + dois botões, sempre.
- Emojis como ícones, ilustrações de stock-genérico, mockups flutuantes sem contexto.
- Cantos 16–24px, sombra grande e borda em tudo (uniformidade sem hierarquia).
- Texto de preenchimento: "Lorem ipsum", "Revolucione seu fluxo de trabalho", "Solução all-in-one", "Potencialize resultados".
- Animações de entrada em tudo (fade-up em cada bloco); parallax sem propósito.
- Paleta sem papel: 6 cores vibrantes competindo, sem cor neutra dominante.
- Dark mode que é só `#000` + neon.

## 3. Como evitar

1. **Tipografia com personalidade**: escolha e combine famílias deliberadamente (display + texto), explore pesos, tamanhos contrastantes (escala 1.25–1.5), entrelinhas e `letter-spacing` coerentes. Fontes variáveis e `font-feature-settings` (numerais tabulares em dados).
2. **Paleta com hierarquia**: 1 neutra dominante, 1 cor de marca, 1 acento raro, e semânticas (sucesso/erro/aviso). Gere tons em `oklch()` para equilíbrio perceptual; use acento com parcimônia (≤10% da tela).
3. **Composição**: quebre a simetria quando fizer sentido (assimetria, sobreposição controlada, âncoras visuais, grids que variam o tamanho dos módulos, espaço negativo generoso).
4. **Profundidade honesta**: escolha UMA linguagem (flat com bordas, sombras suaves em camadas ou contornos fortes) e aplique com consistência.
5. **Detalhes feitos à mão**: estados vazios com personalidade, ícones de um mesmo conjunto/traço, texturas sutis (ruído SVG, grão) só quando combinam com a marca, cursores/seleção/scrollbar estilizados com contenção.
6. **Conteúdo real**: use o texto da imagem; se faltar, escreva cópia específica do domínio (nomes, números, verbos concretos), não genérica.
7. **Movimento com intenção**: poucas animações bem escolhidas (ver `microinteracoes.md`), com hierarquia de ênfase.
8. **Restrição criativa**: limite-se a 2 famílias tipográficas, 1 raio principal, 1 sistema de sombra, 1 estilo de ícone.

## 4. Fidelidade vs. originalidade

| Situação | Ação |
|---|---|
| Imagem de referência detalhada | Fidelidade máxima; criatividade só nos estados, mobile e microinterações |
| Wireframe/esboço | Defina direção visual própria e declare-a em 1 linha |
| "Faça um site de X" sem imagem | Proponha direção específica ao nicho (público, tom, referências), implemente com tokens e explique as escolhas em 2–3 linhas |
| Marca existente | Respeite cores, tipografia e tom da marca acima de gosto pessoal |

Nunca copie marca, logotipo, imagem ou texto protegido; replique **estrutura, sistema e linguagem visual**, usando assets próprios ou placeholders.

## 5. Direções estéticas (pontos de partida, não templates)

- **Editorial/revista**: serifa de display, colunas, legendas, filetes finos, preto/off-white + 1 cor.
- **Brutalista/técnico**: mono, bordas duras, grade visível, alto contraste, sem sombras.
- **Suave/orgânico**: formas arredondadas variadas, paleta terrosa, tipografia humanista, ilustração SVG própria.
- **Minimal funcional**: neutros, muito espaço, uma cor de ação, hierarquia só por tamanho/peso.
- **Retrô/artesanal**: texturas, tipografia de época, bordas e selos, paleta limitada.
- **Denso/dashboard**: tipografia pequena e nítida, tabulares, cores semânticas, densidade controlada.
Misture com critério e comprometa-se com uma; "um pouco de tudo" é slop.

## 6. Texto e conteúdo

- Títulos que dizem algo verificável ("Fature em 2 cliques, sem contador") em vez de slogans vazios.
- Botões com verbos específicos; microcopy com a voz da marca.
- Números, nomes e exemplos plausíveis e consistentes entre seções.
- Nada de lorem ipsum em entrega final; se for placeholder, marque `[placeholder]`.

## 7. Teste anti-slop (antes de entregar)

- [ ] Consigo dizer em uma frase a direção visual e por que ela serve ao conteúdo?
- [ ] Se eu trocasse o logo, ainda reconheceriam como esta marca/imagem de referência?
- [ ] Há hierarquia clara: 1 foco por seção, e o resto subordinado?
- [ ] Cada efeito (sombra, blur, gradiente, animação) tem função?
- [ ] Tipografia, cor e raios vêm de tokens e de uma escolha, não do default?
- [ ] O texto é específico do domínio?
- [ ] Os estados vazio, erro e carregando têm personalidade e utilidade?
