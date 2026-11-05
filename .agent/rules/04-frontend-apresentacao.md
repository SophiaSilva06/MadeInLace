---
trigger: glob
description: "Convenções de HTML, CSS, JS e templates: semântica, tokens, estados, acessibilidade."
globs: "**/*.html, **/*.css, **/*.js, **/templates/**"
---

# Frontend (HTML, CSS, JS, templates)

- **Só apresentação:** não altere contratos de API ou banco (regra 02).
- **HTML semântico:** um `h1`, landmarks, `<button>` para ação e `<a href>` para navegação, `<label>` em todo campo, `alt` nas imagens, `lang` no `<html>`.
- **CSS:** valores vindos de variáveis (tokens), mobile-first, sem `!important` nem estilo inline, sem rolagem horizontal de 320px a 1920px.
- **Estados:** todo elemento interativo tem hover, `:focus-visible`, disabled, loading e erro. Respeite `prefers-reduced-motion`.
- **Acessibilidade mínima (WCAG 2.2 AA):** contraste 4,5:1 em texto normal, uso completo por teclado, alvo de toque de pelo menos 24px (ideal 44px).
- **JS:** vanilla, sem dependência nova sem pedido; `textContent` em vez de `innerHTML`; conteúdo essencial legível sem JS; console sem erros.

Aprofundamento e fidelidade a imagem de referência: skill `senior-frontend-designer`.
