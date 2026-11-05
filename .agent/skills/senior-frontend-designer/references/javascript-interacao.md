# JavaScript de interação: padrões e receitas

Sumário: 1. Princípios · 2. Estrutura de módulo · 3. Menu mobile · 4. Modal (dialog) · 5. Accordion · 6. Tabs · 7. Carrossel · 8. Formulário com validação · 9. Tema claro/escuro · 10. Revelar ao rolar · 11. Filtro/busca · 12. Toast

## 1. Princípios

- JS vanilla moderno (ES2022+), sem globais. Em projeto servido por http(s) use `type="module"`; se o usuário vai **abrir o `index.html` direto do disco (file://)**, módulos são bloqueados por CORS: use `<script defer src>` clássico com IIFE (como o starter) ou um único arquivo. Um módulo por componente, inicializado por `data-component`.
- O **estado vive no DOM** (`aria-expanded`, `hidden`, `data-state`) e o CSS reage a ele. Isso mantém JS pequeno e estilo previsível.
- **Delegação de eventos** quando há muitos itens; `{ passive: true }` em scroll/touch.
- Nunca `innerHTML` com texto de usuário. Use `textContent`, `createElement` ou `<template>`.
- Persistência (`localStorage`) sempre em `try/catch`.
- Desfaça o que criou (`AbortController` para remover listeners) em componentes que podem ser destruídos.
- Debounce em busca/resize; `IntersectionObserver`/`ResizeObserver` em vez de ouvir scroll/resize manualmente.

## 2. Estrutura de módulo

```js
// main.js
const registry = {
  nav: () => import('./components/nav.js'),
};
document.querySelectorAll('[data-component]').forEach(async (el) => {
  const loader = registry[el.dataset.component];
  if (loader) (await loader()).default(el);
});
```
Para projetos pequenos, um único `main.js` com funções `initNav()`, `initTabs()` etc. chamadas em `DOMContentLoaded` é suficiente.

## 3. Menu mobile

HTML: `<button class="nav-toggle" aria-expanded="false" aria-controls="menu">Menu</button><nav id="menu" data-open="false">…</nav>`
```js
export function initNav(root = document) {
  const btn = root.querySelector('.nav-toggle');
  const menu = root.querySelector('#menu');
  const set = (open) => { btn.setAttribute('aria-expanded', open); menu.dataset.open = open; };
  btn.addEventListener('click', () => set(btn.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') { set(false); btn.focus(); } });
  matchMedia('(min-width: 48em)').addEventListener('change', (e) => e.matches && set(false));
}
```
CSS: no mobile `#menu[data-open="false"] { display: none; }`; no desktop sempre visível.

## 4. Modal com `<dialog>`

```html
<button data-open-dialog="signup">Cadastrar</button>
<dialog id="signup" aria-labelledby="signup-title"><h2 id="signup-title">…</h2><form method="dialog">…<button value="cancel">Fechar</button></form></dialog>
```
```js
document.addEventListener('click', (e) => {
  const opener = e.target.closest('[data-open-dialog]');
  if (opener) document.getElementById(opener.dataset.openDialog)?.showModal();
  const dlg = e.target.closest('dialog');
  if (dlg && e.target === dlg) dlg.close(); // clique no backdrop
});
```
`showModal()` já cuida de foco, Esc e inerte do fundo. Estilize `dialog::backdrop`. Devolva o foco ao gatilho no evento `close` se o navegador não fizer.

## 5. Accordion

Prefira `<details><summary>` nativo (com `name="grupo"` para abrir um por vez). Só use JS se precisar de animação suave de altura.

## 6. Tabs (padrão ARIA)

```js
export function initTabs(root) {
  const tabs = [...root.querySelectorAll('[role="tab"]')];
  const select = (tab) => tabs.forEach((t) => {
    const on = t === tab;
    t.setAttribute('aria-selected', on);
    t.tabIndex = on ? 0 : -1;
    document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
  });
  root.addEventListener('click', (e) => { const t = e.target.closest('[role="tab"]'); if (t) select(t); });
  root.addEventListener('keydown', (e) => {
    const i = tabs.indexOf(document.activeElement);
    if (i < 0) return;
    const next = { ArrowRight: i + 1, ArrowLeft: i - 1, Home: 0, End: tabs.length - 1 }[e.key];
    if (next === undefined) return;
    e.preventDefault();
    const t = tabs[(next + tabs.length) % tabs.length];
    t.focus(); select(t);
  });
}
```

## 7. Carrossel

Base em CSS: `scroll-snap-type: x mandatory; overflow-x: auto; display: flex; gap` + filhos `scroll-snap-align: start`. JS só adiciona botões anterior/próximo (`el.scrollBy({ left: el.clientWidth, behavior: 'smooth' })`) e indicadores via `IntersectionObserver`. Autoplay só se pedido, com botão de pausa e parado em `prefers-reduced-motion`. Região com `role="region" aria-roledescription="carrossel" aria-label="…"`.

## 8. Formulário com validação

```js
export function initForm(form) {
  form.noValidate = true; // controlamos a mensagem, mas usamos a API nativa
  const show = (field) => {
    const msg = form.querySelector(`#${field.id}-error`);
    field.setAttribute('aria-invalid', !field.validity.valid);
    if (msg) msg.textContent = field.validity.valid ? '' : field.validationMessage;
  };
  form.addEventListener('blur', (e) => e.target.matches('input, select, textarea') && show(e.target), true);
  form.addEventListener('input', (e) => e.target.getAttribute('aria-invalid') === 'true' && show(e.target));
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const invalid = [...form.elements].filter((f) => f.willValidate && !f.validity.valid);
    invalid.forEach(show);
    if (invalid.length) return invalid[0].focus();
    form.setAttribute('aria-busy', 'true');
    try { /* await fetch(form.action, { method: 'POST', body: new FormData(form) }); */ form.reset(); }
    finally { form.removeAttribute('aria-busy'); }
  });
}
```
Mensagens em português: use `field.setCustomValidity()` ou um mapa por `validity.valueMissing/typeMismatch/tooShort`.
Máscaras (CPF, telefone, CEP): `inputmode="numeric"`, formate no evento `input` sem mover o cursor de forma errada; valide o formato final.

## 9. Tema claro/escuro

```js
const root = document.documentElement;
const saved = (() => { try { return localStorage.getItem('theme'); } catch { return null; } })();
const prefersDark = matchMedia('(prefers-color-scheme: dark)').matches;
root.dataset.theme = saved ?? (prefersDark ? 'dark' : 'light');
document.querySelector('[data-theme-toggle]')?.addEventListener('click', () => {
  const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
  root.dataset.theme = next;
  try { localStorage.setItem('theme', next); } catch {}
});
```
Rode o trecho de leitura inline no `<head>` para evitar flash de tema errado.

## 10. Revelar ao rolar

```js
const io = new IntersectionObserver((entries) => entries.forEach((en) => {
  if (en.isIntersecting) { en.target.classList.add('is-visible'); io.unobserve(en.target); }
}), { threshold: 0.15 });
document.querySelectorAll('[data-reveal]').forEach((el) => io.observe(el));
```
CSS: `[data-reveal] { opacity: 0; translate: 0 1rem; } [data-reveal].is-visible { opacity: 1; translate: 0; transition: ... }` dentro de `@media (prefers-reduced-motion: no-preference)`, e sem ocultar o conteúdo se não houver JS (`.js [data-reveal]`).

## 11. Filtro/busca

```js
const input = document.querySelector('#search');
const items = [...document.querySelectorAll('[data-item]')];
const live = document.querySelector('#results-count');
const norm = (s) => s.normalize('NFD').replace(/\p{Diacritic}/gu, '').toLowerCase();
input.addEventListener('input', debounce(() => {
  const q = norm(input.value);
  let n = 0;
  items.forEach((el) => { const hit = norm(el.textContent).includes(q); el.hidden = !hit; n += hit; });
  live.textContent = `${n} resultado(s)`; // região aria-live="polite"
}, 150));
function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
```

## 12. Toast

Contêiner `<div role="status" aria-live="polite" class="toasts">`; ao disparar, crie o elemento com `textContent`, remova após 4–6s (pausa no hover/foco) e ofereça botão de fechar. Para erros críticos use `role="alert"`.
