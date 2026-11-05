# Microinterações

Microinteração = um evento pequeno com feedback: gatilho → regras → feedback → loops/modos. Servem a **clareza, confirmação e prazer**, nunca a decoração. Cada uma deve responder "o que o usuário aprende ou sente com isso?".

Sumário: 1. Princípios · 2. Tempo e easing · 3. Catálogo com código · 4. Padrões de JS · 5. Acessibilidade e movimento · 6. Performance · 7. Checklist

## 1. Princípios

- **Feedback imediato** (< 100ms percebido) para toda ação; processos longos mostram progresso.
- **Proporcionalidade**: ação pequena → resposta pequena. Reserve o destaque para eventos importantes (sucesso de compra, erro crítico).
- **Consistência**: mesma ação, mesmo movimento, em todo o produto (um token para cada duração/easing).
- **Reversibilidade**: o que abre, fecha com o movimento inverso.
- **Nunca bloqueie**: animação não atrasa a tarefa; o usuário pode interagir durante a transição.
- **Estado final = verdade**: sem JS ou sem animação, o estado final precisa estar correto.

## 2. Tempo e easing (tokens)

```css
:root {
  --dur-instant: 80ms;   /* press, toggle */
  --dur-fast: 150ms;     /* hover, foco, cor */
  --dur-base: 250ms;     /* abrir/fechar pequeno */
  --dur-slow: 400ms;     /* painéis, modais, layout */
  --ease-out: cubic-bezier(.2, .8, .2, 1);      /* entrada: rápido → suave */
  --ease-in: cubic-bezier(.4, 0, 1, 1);         /* saída */
  --ease-in-out: cubic-bezier(.65, 0, .35, 1);  /* movimento contínuo */
  --ease-spring: linear(0, .5 8%, 1.06 20%, .98 34%, 1);  /* "mola" leve via linear() */
}
```
Regra: entradas usam ease-out, saídas ease-in e são ~20–30% mais curtas. Nada acima de 500ms em UI funcional.

## 3. Catálogo com código

**Botão (hover/press/loading)**
```css
.btn { transition: background var(--dur-fast) var(--ease-out), transform var(--dur-instant) var(--ease-out), box-shadow var(--dur-fast); }
.btn:active { transform: scale(.97); }
.btn[aria-busy="true"] { pointer-events: none; }
.btn[aria-busy="true"]::after { content:""; inline-size:1em; block-size:1em; border:2px solid currentColor; border-inline-end-color: transparent; border-radius:50%; animation: spin .7s linear infinite; }
@keyframes spin { to { rotate: 1turn; } }
```

**Link com sublinhado animado**
```css
.link { background: linear-gradient(currentColor 0 0) 0 100% / 0 2px no-repeat; transition: background-size var(--dur-base) var(--ease-out); }
.link:is(:hover, :focus-visible) { background-size: 100% 2px; }
```

**Toggle/switch**: o botão (`role="switch"`) muda `aria-checked`; o CSS desliza o thumb com `translate` e troca a cor do trilho; o estado é lido pelo CSS via `[aria-checked="true"]`.

**Campo flutuante / validação**: ícone de erro entra com `scale` + `opacity` (150ms) e o campo faz um *shake* curto (≤ 300ms, 2–3 oscilações de 4px) só com `prefers-reduced-motion: no-preference`; a mensagem é sempre texto, o movimento só reforça.

**Checkbox/curtir**: traço do SVG desenhado com `stroke-dasharray`/`stroke-dashoffset`; "pop" de 1.0→1.15→1.0 (200ms).

**Accordion/disclosure**: com `details`, anime altura via `interpolate-size: allow-keywords` + `::details-content` dentro de `@supports`; fallback abre sem animação. Chevron gira 180° com `rotate`.

**Modal/drawer/popover**
```css
dialog { opacity: 0; translate: 0 1rem; transition: opacity var(--dur-base) var(--ease-out), translate var(--dur-base) var(--ease-out), display var(--dur-base) allow-discrete, overlay var(--dur-base) allow-discrete; }
dialog[open] { opacity: 1; translate: 0; @starting-style { opacity: 0; translate: 0 1rem; } }
dialog::backdrop { background: rgb(0 0 0 / 0); transition: background var(--dur-base), display var(--dur-base) allow-discrete, overlay var(--dur-base) allow-discrete; }
dialog[open]::backdrop { background: rgb(0 0 0 / .5); @starting-style { background: rgb(0 0 0 / 0); } }
```

**Skeleton**: gradiente deslizante em `background-position` (sem animar largura), cor sutil; pausa em reduced motion (fica estático).

**Toast/snackbar**: entra por baixo (translate + opacity), barra de progresso do tempo restante, pausa em hover/foco.

**Pull-to-refresh, swipe, arrastar**: ofereça sempre alternativa por botão/teclado; use Pointer Events (`pointerdown/move/up`, `setPointerCapture`) e `touch-action` correto.

**Scroll**: barra de progresso de leitura e revelações via `animation-timeline: scroll()/view()` em `@supports`, ou `IntersectionObserver` como fallback; header que encolhe/ganha sombra via `IntersectionObserver` em sentinela (não ouvir `scroll`).

**Contadores/números**: `Intl.NumberFormat`, transição curta (≤ 800ms) com `requestAnimationFrame`; valor final presente no HTML para leitores de tela.

**Transições entre estados/páginas**: View Transitions API (`document.startViewTransition`) como melhoria progressiva, com nomes `view-transition-name` únicos.

**Cursor/hover magnético, parallax, tilt**: use raramente, desative em toque e reduced motion; nunca em elementos de leitura longa.

## 4. Padrões de JS

```js
// Estado por atributo + CSS reage
el.setAttribute('aria-busy', 'true');
try { await action(); el.dataset.state = 'success'; }
catch { el.dataset.state = 'error'; }
finally { el.removeAttribute('aria-busy'); }

// Respeitar preferência do usuário em JS
const reduce = matchMedia('(prefers-reduced-motion: reduce)');
const animate = (el, kf, opts) => reduce.matches ? el.animate(kf, { ...opts, duration: 1 }) : el.animate(kf, opts);
```
- Prefira CSS (transitions/keyframes) e **Web Animations API** (`el.animate()`) a bibliotecas; use `await anim.finished` para encadear.
- Interrompível: cancele/reverta animações em andamento ao receber novo evento (`anim.reverse()`, `anim.cancel()`).
- Não use `setTimeout` para sincronizar com animação; use `transitionend`/`animationend`/`finished`.

## 5. Acessibilidade e movimento

- `prefers-reduced-motion: reduce`: remova movimento espacial (parallax, slides, zoom, shake), mantenha mudanças de opacidade/cor curtas e informativas.
- Nada pisca mais de 3 vezes por segundo (WCAG 2.3.1). Animação que dura > 5s e começa sozinha precisa de pausar/parar (2.2.2).
- Movimento nunca é o único portador de informação; o estado também aparece em texto/ícone/atributo.
- Mudanças de estado dinâmicas anunciadas em `aria-live` quando relevantes (sucesso, erro, contagem de resultados).
- Foco: ao abrir overlay, mova o foco; ao fechar, devolva. Não roube foco em atualizações automáticas.

## 6. Performance

- Anime `transform`, `opacity`, `filter`, `clip-path`; evite layout (`width`, `height`, `top`, `margin`).
- `will-change` só durante a animação, nunca permanente em muitos elementos.
- Limite elementos animados simultâneos; use `content-visibility` e pausa quando fora da viewport.
- Medir INP: handler de clique deve responder visualmente em < 100ms mesmo se o trabalho continua depois.

## 7. Checklist

- [ ] Cada microinteração tem propósito (feedback, orientação, confirmação, prazer)?
- [ ] Durações e easings vêm de tokens; consistentes?
- [ ] Funciona com teclado, toque e mouse; estados hover só em `(hover: hover)`?
- [ ] `prefers-reduced-motion` tratado; sem flash; pausa quando necessário?
- [ ] Estado final correto sem JS/sem animação?
- [ ] Sem jank (somente propriedades de compositor), interrompível e reversível?
