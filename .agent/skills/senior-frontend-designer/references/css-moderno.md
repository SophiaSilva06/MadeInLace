# CSS moderno: técnicas e quando usar

Sumário: 1. Arquitetura · 2. Layout · 3. Responsividade · 4. Tipografia e espaço fluidos · 5. Cor e tema · 6. Seletores modernos · 7. Animação · 8. Progressive enhancement

## 1. Arquitetura

```css
@layer reset, tokens, base, components, utilities;
```
- Camadas controlam a ordem de cascata sem brigar com especificidade. Utilities sempre vencem components.
- Variáveis em `:root` (tokens globais) e variáveis locais por componente (`--btn-bg`) para variações sem duplicar regras.
- Nomeie por componente: `.card`, `.card__title`, `.card--featured`. Evite seletores aninhados com mais de 2–3 níveis.
- CSS nesting nativo é aceitável para estados e filhos diretos (`&:hover`, `& .title`), sem exagerar.
- Propriedades lógicas: `margin-inline`, `padding-block`, `inset-inline-start`, para suportar RTL e escrita vertical sem reescrever.

## 2. Layout

- **Página/grade de cards**: `display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr)); gap: var(--space-6);` (responsivo sem media query).
- **Alinhamento linear** (navbar, barra de ações): Flexbox com `gap`, `flex-wrap`, `align-items`.
- **Subgrid** para alinhar itens internos de cards irmãos (título, texto, botão na mesma linha).
- **Centralização**: `display: grid; place-items: center;`.
- **Container**: `width: min(100% - 2rem, 72rem); margin-inline: auto;`.
- **Proporção**: `aspect-ratio: 16 / 9` + `object-fit: cover`.
- **Sticky header**: `position: sticky; top: 0;` (não use JS para isso).
- **Altura de tela**: `min-height: 100dvh` (não `100vh`) para mobile.
- Evite `position: absolute` para estruturar layout; use para sobreposições pontuais (badges, ícone dentro de input).

## 3. Responsividade

- Mobile-first: estilos base para telas pequenas e `@media (min-width: 48em)` etc. Pontos de quebra típicos: 40em (640px), 48em (768px), 64em (1024px), 80em (1280px). Quebre onde o **conteúdo** exige, não por dispositivo.
- **Container queries** para componentes reutilizáveis:
```css
.card-wrap { container-type: inline-size; container-name: card; }
@container card (min-width: 32rem) { .card { grid-template-columns: 12rem 1fr; } }
```
- Preferências do usuário: `@media (prefers-reduced-motion: reduce)`, `(prefers-color-scheme: dark)`, `(prefers-contrast: more)`, `(hover: hover)` para só aplicar hover onde existe ponteiro fino.
- Imagens responsivas: `srcset`/`sizes`, `<picture>` para art direction, `max-inline-size: 100%; height: auto;`.

## 4. Tipografia e espaço fluidos

```css
:root {
  --step-0: clamp(1rem, 0.96rem + 0.2vw, 1.125rem);
  --step-3: clamp(2rem, 1.4rem + 3vw, 3.5rem);
  --space-section: clamp(3rem, 2rem + 5vw, 7rem);
}
h1, h2 { text-wrap: balance; }
p { text-wrap: pretty; max-inline-size: 70ch; }
```
- Use `rem` (respeita a configuração do usuário). Nunca trave `html { font-size }` em px.
- Fontes variáveis com `font-weight` contínuo; `font-display: swap`; `font-optical-sizing: auto`.

## 5. Cor e tema

```css
:root {
  color-scheme: light dark;
  --brand: oklch(62% 0.19 255);
  --brand-hover: color-mix(in oklab, var(--brand) 88%, black);
  --text: light-dark(#14181f, #eef1f6);
  --bg: light-dark(#ffffff, #0f1318);
}
```
- Ofereça fallback hex antes de `oklch()`/`light-dark()` se precisar suportar navegadores antigos (`@supports`).
- Alterne tema manual com `data-theme="dark"` no `<html>` e persista a escolha em `localStorage` (veja receitas JS). Respeite a preferência do sistema como padrão.
- Estados de foco: `:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }`. Nunca `outline: none` sem substituto.

## 6. Seletores modernos

- `:is()`, `:where()` (especificidade zero, ótimo para base/reset), `:not()`.
- `:has()` para estilizar o pai pelo estado do filho (`.field:has(:user-invalid)`, `.card:has(img)`).
- `:user-invalid` / `:user-valid` para validação só após interação do usuário.
- `:focus-within` para destacar grupos.
- `::marker`, `::backdrop` (dialog/popover), `accent-color` em controles nativos.

## 7. Animação

Anime só `transform`/`opacity`, com tokens de duração e easing e `prefers-reduced-motion`. Catálogo completo, código e regras em `microinteracoes.md`.

## 8. Progressive enhancement

- Verifique suporte em MDN/caniuse/Baseline antes de depender de recurso novo (anchor positioning, `@scope`, `interpolate-size`, scroll-driven animations).
- Estruture: `@supports (propriedade: valor) { ... }` com estilo funcional fora do bloco.
- Evite hacks de prefixo manual; o navegador-alvo moderno dispensa a maioria dos `-webkit-`, exceto `-webkit-backdrop-filter` (Safari antigo) e `-webkit-line-clamp`.
