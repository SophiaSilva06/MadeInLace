// Script clássico (defer) para funcionar também ao abrir o index.html direto do disco (file://).
// Em projeto servido por http(s), pode virar módulo ES (type="module") e dividir em arquivos.
(() => {
'use strict';
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function initNav() {
  const btn = $('.nav-toggle');
  const menu = $('#menu');
  if (!btn || !menu) return;
  const set = (open) => { btn.setAttribute('aria-expanded', String(open)); menu.dataset.open = String(open); };
  btn.addEventListener('click', () => set(btn.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && btn.getAttribute('aria-expanded') === 'true') { set(false); btn.focus(); } });
  matchMedia('(min-width: 48em)').addEventListener('change', (e) => e.matches && set(false));
}

function initTheme() {
  const root = document.documentElement;
  $('[data-theme-toggle]')?.addEventListener('click', () => {
    const next = root.dataset.theme === 'dark' ? 'light' : 'dark';
    root.dataset.theme = next;
    try { localStorage.setItem('theme', next); } catch { /* storage indisponível */ }
  });
}

function initReveal() {
  const items = $$('[data-reveal]');
  if (!items.length || !('IntersectionObserver' in window)) { items.forEach((el) => el.classList.add('is-visible')); return; }
  const io = new IntersectionObserver((entries) => entries.forEach((en) => {
    if (en.isIntersecting) { en.target.classList.add('is-visible'); io.unobserve(en.target); }
  }), { threshold: 0.15 });
  items.forEach((el) => io.observe(el));
}

function toast(message) {
  const host = $('.toasts');
  if (!host) return;
  const el = document.createElement('p');
  el.className = 'toast';
  el.textContent = message;
  host.append(el);
  setTimeout(() => el.remove(), 5000);
}

function initForms() {
  $$('form.form').forEach((form) => {
    const show = (field) => {
      const msg = $(`#${field.id}-error`, form);
      field.setAttribute('aria-invalid', String(!field.validity.valid));
      if (msg) msg.textContent = field.validity.valid ? '' : field.validationMessage;
    };
    form.addEventListener('blur', (e) => e.target.matches('input, select, textarea') && show(e.target), true);
    form.addEventListener('input', (e) => e.target.getAttribute?.('aria-invalid') === 'true' && show(e.target));
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const invalid = [...form.elements].filter((f) => f.willValidate && !f.validity.valid);
      invalid.forEach(show);
      if (invalid.length) return invalid[0].focus();
      form.reset();
      toast('Mensagem enviada com sucesso.');
    });
  });
}

initNav();
initTheme();
initReveal();
initForms();
})();
