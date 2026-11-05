# Segurança em frontend web (HTML/CSS/JS puro + templates Jinja2)

Conteúdo: Modelo mental · XSS e sinks perigosos · CSP · Autenticação e armazenamento de token · CSRF · CORS · Headers · Terceiros e SRI · Redirects, links e postMessage · Prototype pollution · Dependências e build opcionais · Checklist de revisão

---

## Modelo mental

O frontend roda no dispositivo do atacante: **tudo nele é público e alterável** (lógica, regras de negócio, flags de admin, "campos ocultos"). Segurança real vive no servidor; o frontend reduz superfície (escape correto, CSP, armazenamento seguro) e nunca é a única barreira. Nada que seja segredo pode ir para o bundle.

## XSS e sinks perigosos

O Jinja2 escapa por padrão no servidor e o DOM só escapa se você usar `textContent`/atributos; o XSS aparece quando se **contorna** o escape (no template ou no JS).

| Sink | Risco | Alternativa |
|---|---|---|
| `element.innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` | HTML arbitrário | `textContent`, `createElement`, ou sanitizar com **DOMPurify** |
| `\|safe`/`Markup()`/`autoescape false` no Jinja2 | HTML arbitrário vindo do servidor | remover; ou sanitizar no servidor (`nh3`/`bleach`) antes de marcar como seguro |
| `href`/`src`/`action` com dado do usuário | `javascript:` e `data:` URIs | validar esquema (`https:`/`http:`/`mailto:`) com `new URL()` |
| `eval`, `new Function`, `setTimeout("texto")`, `script.src = userInput` | execução de código | nunca; usar funções e dados |
| `location = userInput`, `window.open(userInput)` | open redirect / `javascript:` | allowlist de destinos |
| Template literals montando HTML (`` `<li>${nome}</li>` `` + `innerHTML`) | XSS | `createElement` + `textContent`, ou `<template>` clonado |
| Markdown renderizado | HTML embutido | renderizador com sanitização e sem HTML cru |

```js
// VULNERÁVEL: dado do usuário/API vira HTML
lista.innerHTML = `<li>${produto.nome}</li>`;
// SEGURO: texto não é interpretado como HTML
const li = document.createElement("li");
li.textContent = produto.nome;
lista.appendChild(li);
// se HTML rico for requisito real: DOMPurify.sanitize(html) antes de atribuir a innerHTML
```
```js
// validar URL antes de usar em href
function urlSegura(u) { try { const p = new URL(u, location.origin); return ["https:", "http:", "mailto:"].includes(p.protocol) ? p.href : "#"; } catch { return "#"; } }
```
DOM XSS: rastreie fontes (`location.hash/search`, `document.referrer`, `postMessage`, `localStorage`, respostas de API, dados devolvidos por APIs de terceiros) até sinks. Ao enviar dados do servidor para JS, use `{{ dados | tojson }}` em `<script type="application/json">` e leia com `JSON.parse`; nunca `var x = "{{ valor }}"`. Dados vindos de APIs externas são **não confiáveis**: renderize como texto.

## Content Security Policy (CSP)

A CSP é a rede de segurança contra XSS. Prefira **nonce/hash** a `unsafe-inline`; evite `unsafe-eval`.
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-{aleatório-por-resposta}'; style-src 'self'; img-src 'self' data:; connect-src 'self' https://api.exemplo.com; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests
```
Comece em `Content-Security-Policy-Report-Only` com `report-to` para medir antes de impor. Habilite **Trusted Types** (`require-trusted-types-for 'script'`) em apps que podem adotá-lo.

## Autenticação e armazenamento de token

- **Preferir cookie de sessão/JWT em cookie `HttpOnly; Secure; SameSite=Lax|Strict`** (JS não consegue ler, então um XSS não exfiltra o token). Com cookies, **proteja contra CSRF** (abaixo).
- `localStorage`/`sessionStorage` são legíveis por qualquer script da página: um único XSS ou dependência comprometida rouba o token. Se um token precisar existir no navegador, mantenha-o **apenas em memória** e o refresh em cookie `HttpOnly`.
- Nunca guarde senhas, chaves ou dados pessoais sensíveis no storage do navegador.
- Logout deve invalidar no servidor, não só apagar o token local.

## CSRF

Necessário sempre que a autenticação é automática (cookies), o que é o caso de um site com formulários Jinja2 e sessão. O FastAPI não traz CSRF pronto: implemente token anti-CSRF por sessão em campo oculto de cada formulário que altera estado (detalhes e código em `python-backend.md`), `SameSite=Lax/Strict`, validação de `Origin`/`Referer`, e **métodos seguros sem efeito colateral** (GET nunca altera estado: logout e exclusões são `POST`/`DELETE`). Requisições `fetch` com cookie também enviam o token (header `X-CSRF-Token`). APIs que usam só `Authorization: Bearer` não sofrem CSRF clássico.

## CORS

CORS **não é** controle de acesso; apenas instrui o navegador. Configure origens explícitas (`https://app.exemplo.com`), nunca reflita o header `Origin` sem validar, nunca combine `*` com credenciais, restrinja métodos e headers, e não habilite `null` como origem. Revise `Access-Control-Allow-Credentials: true`.

## Headers de segurança (servidor/CDN/proxy)

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Content-Security-Policy: ... (acima; frame-ancestors substitui X-Frame-Options)
Cross-Origin-Opener-Policy: same-origin
Cache-Control: no-store     # em respostas autenticadas/sensíveis
```
Cookies: `Secure; HttpOnly; SameSite`, prefixo `__Host-` quando possível. Remova headers que revelam versão (`Server`, `X-Powered-By`). Verifique com securityheaders.com / Mozilla Observatory.

## Terceiros e SRI

Todo script de terceiros executa com os poderes da sua página. Minimize, hospede localmente quando possível, fixe a versão e use **Subresource Integrity**:
```html
<script src="https://cdn.exemplo.com/lib@1.2.3/lib.min.js" integrity="sha384-..." crossorigin="anonymous"></script>
```
Tags de analytics/chat/anúncios em páginas de login/pagamento são risco de skimming (Magecart); isole em iframe sandbox ou remova dessas páginas. `<iframe>` de terceiros: use `sandbox` e `allow` mínimos.

## Redirects, links e postMessage

- **Open redirect:** `?next=` / `returnUrl` deve ser validado no servidor contra allowlist ou aceitar apenas caminhos relativos (`/painel`), rejeitando `//evil.com` e `\evil.com`.
- `target="_blank"` com `rel="noopener noreferrer"` (navegadores modernos já tratam `noopener`, mas mantenha).
- `window.postMessage`: ao **enviar**, informe `targetOrigin` exato (não `'*'` com dado sensível); ao **receber**, verifique `event.origin` contra allowlist e valide a estrutura da mensagem.

## Prototype pollution e parsing

Cuidado ao fazer merge profundo de objetos vindos do usuário (`_.merge`, `Object.assign` recursivo, `JSON.parse` + merge): bloqueie chaves `__proto__`, `constructor`, `prototype`; use `Object.create(null)`/`Map` para dicionários; mantenha lodash e similares atualizados. Evite regex com backtracking catastrófico (ReDoS) em validação de entrada.

## Dependências e build opcionais

O projeto serve HTML/CSS/JS direto pelo servidor; se algum dia entrar um bundler (Vite, webpack, etc.), qualquer variável embutida no build vira pública (prefixos como `VITE_*`, `PUBLIC_*`): **nunca** coloque chaves secretas, tokens de admin, credenciais de banco ou chaves privadas nelas. Chaves "públicas" (ex.: publishable key de pagamento, chave de mapas) devem ter restrição de domínio/escopo no provedor. Não exponha source maps nem arquivos de configuração em `StaticFiles`, e não faça commit de `.env`.

## Se houver npm (bibliotecas JS de terceiros)

- Commite o **lockfile** e use `npm ci` (ou `pnpm install --frozen-lockfile`, `yarn --immutable`) no CI.
- `npm audit --audit-level=high` e/ou `osv-scanner` no PR; Dependabot/Renovate com revisão.
- Desconfie de pacotes novos: confira nome (typosquatting), mantenedor, histórico, downloads. Considere `ignore-scripts=true` (`npm config`) e habilite scripts só onde necessário.
- Fixe versões; evite `*`/`latest`; revise `postinstall`.
- Habilite 2FA e *provenance* ao publicar pacotes.

## Checklist de revisão de um PR de frontend

1. Algum dado do usuário/API chega a um sink HTML/URL/JS sem escape ou sanitização?
2. Há token/segredo em `localStorage`, no JS/HTML servido, no template, em comentário ou em arquivo de exemplo?
3. Formulários e requisições mutáveis têm proteção CSRF? Métodos corretos?
4. Novos scripts/estilos/iframes externos: necessários, fixados, com SRI e dentro da CSP?
5. Redirects e links dinâmicos validados? `postMessage` com origin verificada?
6. Autorização ou regra de negócio aplicada só no cliente? (se sim, reportar: deve existir no servidor)
7. Novas bibliotecas JS (CDN ou npm) auditadas, fixadas e com SRI/lockfile?
8. Mensagens de erro expõem detalhes internos?
