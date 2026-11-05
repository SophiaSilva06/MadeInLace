# Performance e SEO

Sumário: 1. Core Web Vitals · 2. Carregamento · 3. SEO e metadados

## 1. Core Web Vitals (metas)

- **LCP** ≤ 2,5s: otimize a imagem/título principal (dimensões, formato AVIF/WebP, `fetchpriority="high"` na imagem hero, sem lazy nela).
- **INP** ≤ 200ms: handlers curtos, sem trabalho pesado na thread principal, `requestAnimationFrame`/`scheduler.yield()` ou Web Worker se necessário, listeners `passive` em scroll/touch.
- **CLS** ≤ 0,1: `width`/`height` ou `aspect-ratio` em mídia, reserve espaço para embeds, evite injetar conteúdo acima do existente, `font-display: swap` + fallback com métricas parecidas (`size-adjust`).

## 2. Carregamento

- CSS crítico pequeno no `<head>`; JS com `type="module"` (adiado por padrão) ou `defer`.
- Fontes: no máximo 2 famílias, subset latino, `preload` apenas da fonte crítica, `preconnect` se vier de CDN.
- Imagens: `loading="lazy"` e `decoding="async"` abaixo da dobra; `srcset`/`sizes`; formatos modernos.
- Sem bibliotecas para o que o navegador faz sozinho. Evite jQuery/lodash/moment em projeto novo.
- Reduza reflows: leia o DOM em lote, escreva em lote; use `content-visibility: auto` em seções longas.

## 3. SEO e metadados

```html
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Título claro | Marca</title>
  <meta name="description" content="Resumo de 140–160 caracteres.">
  <meta name="theme-color" content="#0f1318">
  <meta property="og:title" content="..."><meta property="og:description" content="..."><meta property="og:image" content="...">
  <link rel="icon" href="data:image/svg+xml,...">
</head>
```
- Nunca use `user-scalable=no` nem `maximum-scale=1` (bloqueia zoom).
- Um `h1`; URLs âncora legíveis; `<a>` com texto descritivo ("Ver planos", não "clique aqui").
