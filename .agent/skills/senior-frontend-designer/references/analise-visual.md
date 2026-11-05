# Análise visual: de imagem a sistema de design

Sumário: 1. Inventário · 2. Medidas e espaçamento · 3. Tipografia · 4. Cores · 5. Forma e profundidade · 6. Ícones e imagens · 7. Estados implícitos · 8. Quando a imagem é só desktop

## 1. Inventário (de fora para dentro)

1. Desenhe o esqueleto: faixas horizontais (header, hero, seções, footer) e, dentro de cada uma, as colunas.
2. Identifique a **largura máxima do conteúdo** (container) e as margens laterais. Designs desktop costumam usar 1120–1280px de conteúdo útil.
3. Liste componentes únicos e suas variações (botão primário/secundário/ghost, card com/sem imagem).
4. Defina a ordem de leitura: ela vira a ordem do HTML (o CSS reposiciona só o visual, nunca o contrário).

## 2. Medidas e espaçamento

- Se a imagem tem largura conhecida (ex.: 1440px), calcule proporções: elemento com 480px de 1440 ≈ 33%. Use `fr`, `%` ou `clamp()`, não pixels fixos, para o que deve ser fluido.
- Procure o **módulo base**: a maioria dos designs usa múltiplos de 4 ou 8. Meça vários espaços; o menor divisor comum revela o módulo.
- Escala de espaçamento sugerida (tokens): 4, 8, 12, 16, 24, 32, 48, 64, 96, 128.
- Espaçamento **entre seções** costuma ser o dobro ou o triplo do espaçamento interno de cards. Preserve essa relação de ritmo, mesmo que os números mudem um pouco.
- Alinhamentos importam mais que pixels: textos e bordas que alinham na imagem devem alinhar no código (use o mesmo token, o mesmo grid).

## 3. Tipografia

**Escala**: meça a altura de maiúsculas ou a altura de linha dos textos e converta (altura de x-height ≈ 0,5 × font-size; cap-height ≈ 0,7 × font-size). Agrupe em degraus coerentes:

| Papel | Desktop típico | Mobile típico |
|---|---|---|
| Display/H1 | 48–72px | 32–40px |
| H2 | 32–44px | 24–30px |
| H3 | 20–28px | 18–22px |
| Corpo | 16–18px | 16px |
| Pequeno/legenda | 12–14px | 12–14px |

- Implemente com `clamp(min, preferido, max)`, ex.: `font-size: clamp(2rem, 1.2rem + 3vw, 4.5rem)`.
- **Line-height**: títulos 1.05–1.2; corpo 1.5–1.7. **Letter-spacing**: levemente negativo em títulos grandes (-0.01 a -0.03em); positivo em textos pequenos em caixa alta (0.05–0.1em).
- **Peso**: distinga 400/500/600/700 olhando a espessura do traço relativa ao tamanho.
- **Identificar a fonte**: observe terminais, "g" de um ou dois andares, "a", "R", "1", "t". Famílias comuns: geométricas (Poppins, Montserrat, Outfit), neo-grotescas (Inter, DM Sans, Manrope, Plus Jakarta Sans), humanistas (Source Sans 3, Nunito Sans), serifadas (Playfair Display, Lora, Fraunces, Merriweather), mono (JetBrains Mono, IBM Plex Mono). Escolha a mais próxima disponível como fonte variável e informe a suposição.
- `text-wrap: balance` em títulos e `text-wrap: pretty` em parágrafos.

## 4. Cores

1. Rode `python scripts/extract_palette.py imagem.png -n 8` para obter as cores dominantes e suas proporções.
2. Atribua **papéis**, não nomes de cor: `--color-bg`, `--color-surface`, `--color-surface-2`, `--color-text`, `--color-text-muted`, `--color-border`, `--color-primary`, `--color-primary-contrast`, `--color-accent`, e estados `--color-success/warning/danger`.
3. Cores muito próximas na imagem (por compressão JPEG) são a mesma cor: unifique.
4. Gere variações (hover, active, bordas sutis) a partir da cor base com `color-mix(in oklab, var(--color-primary) 85%, black)` em vez de inventar hexadecimais novos.
5. Valide contraste com `python scripts/contrast.py "#fff" "#3b82f6"`. Se o design original falhar no AA, ajuste a cor levemente e registre a mudança na resposta (acessibilidade vence fidelidade nesse caso).
6. Gradientes: identifique ângulo, paradas e se há ruído/sobreposição; reproduza com `linear-gradient`/`radial-gradient` e `color-mix`.

## 5. Forma e profundidade

- **Raio**: tipicamente 4, 8, 12, 16, 24px ou pill (`9999px`). Cards e inputs costumam compartilhar o mesmo raio; botões podem ser diferentes.
- **Bordas**: 1px de baixo contraste (`--color-border`) é mais comum que preto.
- **Sombras**: observe se é suave e difusa (ex.: `0 8px 24px -8px rgb(0 0 0 / .15)`) ou dura. Crie 3 níveis (`--shadow-sm/md/lg`) e reuse.
- **Glassmorphism/blur**: `backdrop-filter: blur()` com fundo semitransparente e fallback sólido.

## 6. Ícones e imagens

- Ícones: SVG inline com `currentColor`, `aria-hidden="true"` quando decorativos, ou com `<title>`/`aria-label` quando carregam significado. Mantenha traço e tamanho consistentes (24px com traço 1.5–2px é o padrão).
- Fotos e ilustrações: use `aspect-ratio` + `object-fit: cover` para reproduzir os recortes; placeholders via gradiente CSS ou SVG quando não houver o arquivo.
- Não copie marcas, logos ou fotos protegidas; use placeholders identificados.

## 7. Estados implícitos (o design estático esconde coisas)

Para cada componente interativo visível, defina: `:hover`, `:focus-visible`, `:active`, `:disabled`, `[aria-expanded]`, `[aria-current]`, loading, vazio e erro. Derive-os do sistema (ex.: hover = 8% mais escuro; foco = anel de 2–3px com offset, contraste ≥ 3:1).

## 8. Quando a imagem é só desktop (ou só mobile)

- Preserve o **sistema** (tokens, componentes, tom), não o layout literal.
- Desktop → mobile: colunas empilham, grids de 3–4 viram 1–2, navegação vira menu colapsável, CTAs ficam em largura total, imagens laterais vão acima ou abaixo do texto, tipografia reduz via `clamp()`.
- Mobile → desktop: introduza `max-width` no container, grids de múltiplas colunas e navegação horizontal; evite linhas de texto acima de ~75 caracteres.
- Teste em 320, 375, 768, 1024, 1280 e 1920px.
